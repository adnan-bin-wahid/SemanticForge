from fastapi import APIRouter
from ...services.embedding_indexer import EmbeddingIndexer
from ...services.vector_search import search_by_query
from ...models.search import VectorSearchQuery, VectorSearchResponse, SearchResult
from app.services.keyword_search import keyword_search_instance
from app.models.search import KeywordSearchQuery, KeywordSearchResponse
from app.services.hybrid_search import hybrid_search_instance
from app.models.search import HybridSearchResponse
from app.services.graph_expansion import GraphExpansion
from app.models.search import GraphExpansionRequest, GraphExpansionResponse
from app.models.search import ContextRetrievalRequest, ContextRetrievalResponse
from app.models.search import GeneratePatchRequest, GeneratePatchResponse, DiffStats, ValidationReport
from app.services.code_generation import CodeGenerator
from app.services.diff_generator import DiffGenerator
from app.services.constraint_checker_integration import validate_patch_completely, validate_patch_completely_from_content, generate_validation_report
from app.services.test_runner_integration import run_tests_on_patch, generate_test_report
from app.services.test_mapper_integration import get_test_to_code_mapping
from app.services.coverage_analyzer_integration import get_coverage_analysis
from fastapi import Request
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/index-embeddings")
async def index_embeddings():
    """
    Trigger indexing of all code symbols from Neo4j into Qdrant.
    Generates embeddings and stores them for vector search.
    
    Returns:
        Indexing statistics and status
    """
    indexer = EmbeddingIndexer()
    result = await indexer.index_repository()
    return result

@router.post("/vector-search", response_model=VectorSearchResponse)
async def vector_search(request: VectorSearchQuery):
    """
    Search for code symbols using semantic similarity.
    
    Args:
        request: Contains the natural language query and optional limit
        
    Returns:
        List of semantically similar code symbols with scores
    """
    results = await search_by_query(request.query, request.limit)
    
    # Convert to SearchResult objects
    search_results = [
        SearchResult(
            name=r["name"],
            type=r["type"],
            score=r["score"],
            start_line=r["start_line"],
        )
        for r in results
    ]
    
    return VectorSearchResponse(
        query=request.query,
        results=search_results,
        total_results=len(search_results),
    )

@router.post("/keyword-search", response_model=KeywordSearchResponse)
async def keyword_search(request: KeywordSearchQuery):
    """
    Search for code symbols using keyword matching.
    
    Args:
        request: Contains the query and optional limit
        
    Returns:
        List of relevant code symbols with scores
    """
    # Ensure the index is built before searching
    if not keyword_search_instance.bm25:
        await keyword_search_instance.index_documents()
        
    results = keyword_search_instance.search(request.query, request.limit)
    
    return KeywordSearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
    )

@router.post("/hybrid-search", response_model=HybridSearchResponse)
async def hybrid_search(request: VectorSearchQuery):
    """
    Perform a hybrid search combining vector and keyword search.
    """
    results = await hybrid_search_instance.search(request.query, request.limit)
    return results

@router.post("/expand-context", response_model=GraphExpansionResponse)
async def expand_context(fastapi_req: Request, request: GraphExpansionRequest):
    """
    Expand the context of a list of symbols by querying the graph for neighbors.
    """
    graph_expansion_service = fastapi_req.app.state.graph_expansion_service
    expanded_context = await graph_expansion_service.expand_context(request.symbols)
    return GraphExpansionResponse(expanded_context=expanded_context)

@router.post("/retrieve-context", response_model=ContextRetrievalResponse)
async def retrieve_context(fastapi_req: Request, request: ContextRetrievalRequest):
    """
    Orchestrates the full context retrieval pipeline.
    """
    context_retriever = fastapi_req.app.state.context_retriever
    response_data = await context_retriever.retrieve_context(request.query, request.limit)
    return ContextRetrievalResponse(**response_data)

@router.post("/generate-code")
async def generate_code(fastapi_req: Request, request: ContextRetrievalRequest):
    """
    Generate code based on a user instruction.
    """
    code_generator = fastapi_req.app.state.code_generator
    result = await code_generator.generate_code(request.query, request.limit)
    return result


@router.post("/generate-patch", response_model=GeneratePatchResponse)
async def generate_patch(fastapi_req: Request, request: GeneratePatchRequest):
    """
    Generate a patch/diff by comparing original code with LLM-generated code.
    Optionally validates the patch through static analysis and tests.
    
    Args:
        fastapi_req: FastAPI request context (contains app state)
        request: GeneratePatchRequest containing:
            - query: User instruction for code generation
            - original_content: Original file content to compare against
            - file_path: Path for the diff header (default: "generated.py")
            - limit: Number of context results to use (default: 10)
            - repo_path: (Optional) Path to repository root for validation
            - file_relative_path: (Optional) File path relative to repo
            - run_tests: (Optional) Whether to run tests (default: False)
            - test_directory: (Optional) Path to tests (default: "tests")
            - strict: (Optional) Strict type checking (default: False)
            - test_timeout: (Optional) Test timeout in seconds (default: 60)
    
    Returns:
        GeneratePatchResponse containing:
            - unified_diff: Standard unified diff format (git-compatible)
            - stats: Diff statistics (lines added/removed/modified, similarity ratio)
            - generated_code: The LLM-generated code
            - file_path: The file path used in the diff
            - validation: (Optional) Validation report if repo_path was provided
    """
    logger.info(f"========== PHASE 5.6 START: /generate-patch Endpoint Called ==========")
    logger.info(f"[PHASE 5.6] User instruction: {request.query[:100]}...")
    logger.info(f"[PHASE 5.6] File: {request.file_path}")
    logger.info(f"[PHASE 5.6] Context limit: {request.limit}")
    logger.info(f"[PHASE 5.6] Validation enabled: {bool(request.repo_path)}")
    
    code_generator = fastapi_req.app.state.code_generator
    diff_generator = DiffGenerator()
    
    # Step 1: Generate code based on user instruction
    logger.info(f"[PHASE 5.4] Calling LLM CodeGenerator service...")
    generation_result = await code_generator.generate_code(request.query, request.limit)
    generated_code = generation_result.get("generated_code", "")
    logger.info(f"[PHASE 5.4] ✓ Code generated successfully ({len(generated_code)} bytes)")
    
    # Step 2: Create diff between original and generated
    logger.info(f"[PHASE 5.5] Generating unified diff...")
    unified_diff = diff_generator.generate_unified_diff(
        original_content=request.original_content,
        generated_content=generated_code,
        file_path=request.file_path
    )
    logger.info(f"[PHASE 5.5] ✓ Diff generated successfully")
    
    # Step 3: Calculate statistics
    logger.info(f"[PHASE 5.5] Calculating diff statistics...")
    stats_dict = diff_generator.get_diff_stats(request.original_content, generated_code)
    stats = DiffStats(**stats_dict)
    logger.info(f"[PHASE 5.5] ✓ Stats: +{stats.lines_added} -{stats.lines_removed} ({stats.similarity_ratio*100:.1f}% similar)")
    
    # Step 4: Optional validation
    validation_report = None
    if request.repo_path or request.original_content:
        logger.info(f"========== PHASE 6 START: Validation Pipeline ==========")
        try:
            # Determine file relative path
            file_relative_path = request.file_relative_path or request.file_path
            logger.info(f"[PHASE 6] File relative path: {file_relative_path}")
            
            # Use content-based validation (no file system access needed)
            logger.info(f"[PHASE 6] Using content-based validation pipeline")
            logger.info(f"[PHASE 6] Original content size: {len(request.original_content)} bytes")
            logger.info(f"[PHASE 6] Generated content size: {len(generated_code)} bytes")
            
            # Run constraint checking (Phases 6.1-6.5)
            logger.info(f"[PHASE 6.5] Starting constraint checker service (orchestrator)...")
            constraint_report, temp_dir = validate_patch_completely_from_content(
                file_relative_path,
                request.original_content,
                generated_code,
                mypy_strict=request.strict,
                continue_on_errors=True  # Run all checks even if some fail
            )
            logger.info(f"[PHASE 6.5] ✓ Constraint checker completed")
            logger.info(f"[PHASE 6.5] Overall result: {'PASSED' if constraint_report.passed else 'FAILED'}")
            logger.info(f"[PHASE 6.5] Errors: {constraint_report.total_errors}, Warnings: {constraint_report.total_warnings}")
            
            constraint_api_report = generate_validation_report(constraint_report)
            
            # Run tests if requested (Phase 6.6)
            test_api_report = None
            if request.run_tests and request.repo_path:
                logger.info(f"[PHASE 6.6] Starting test execution runner (Pytest)...")
                try:
                    file_relative_path = request.file_relative_path or request.file_path
                    test_report, _ = run_tests_on_patch(
                        request.repo_path,
                        {file_relative_path: generated_code},
                        request.test_directory,
                        timeout=request.test_timeout
                    )
                    test_api_report = generate_test_report(test_report)
                    logger.info(f"[PHASE 6.6] ✓ Test execution completed")
                    logger.info(f"[PHASE 6.6] Result: {test_api_report.get('status', 'unknown')}")
                except Exception as e:
                    logger.warning(f"[PHASE 6.6] Test execution failed: {str(e)}")
            else:
                logger.info(f"[PHASE 6.6] Test execution skipped (run_tests=false)")
            
            # Build validation stages (Phase 6.9 Frontend will display these)
            logger.info(f"[PHASE 6.8] Building validation stages for frontend display...")
            validation_stages = {}
            
            if constraint_report.basic_rules_result:
                validation_stages["syntax"] = {
                    "stage_name": "basic_rules",
                    "passed": constraint_report.basic_rules_result.passed,
                    "error_count": constraint_report.basic_rules_result.error_count,
                    "warning_count": constraint_report.basic_rules_result.warning_count,
                    "summary": constraint_report.basic_rules_result.summary
                }
            
            if constraint_report.ruff_result:
                validation_stages["linting"] = {
                    "stage_name": "ruff",
                    "passed": constraint_report.ruff_result.passed,
                    "error_count": constraint_report.ruff_result.error_count,
                    "warning_count": constraint_report.ruff_result.warning_count,
                    "summary": constraint_report.ruff_result.summary
                }
            
            if constraint_report.mypy_result:
                validation_stages["type_checking"] = {
                    "stage_name": "mypy",
                    "passed": constraint_report.mypy_result.passed,
                    "error_count": constraint_report.mypy_result.error_count,
                    "warning_count": constraint_report.mypy_result.warning_count,
                    "summary": constraint_report.mypy_result.summary
                }
            
            if test_api_report:
                validation_stages["tests"] = {
                    "stage_name": "test_execution",
                    "passed": test_api_report["status"] == "passed",
                    "error_count": test_api_report["statistics"]["errors"],
                    "warning_count": 0,
                    "summary": test_api_report["summary"]
                }
            
            # Calculate overall statistics
            total_errors = constraint_report.total_errors
            total_warnings = constraint_report.total_warnings
            
            if test_api_report:
                total_errors += test_api_report["statistics"]["errors"]
                total_errors += test_api_report["statistics"]["failed"]
            
            # Determine overall status
            overall_passed = (constraint_report.passed and 
                             (not request.run_tests or (test_api_report is None or test_api_report["status"] == "passed")))
            
            # Build summary
            if overall_passed:
                overall_summary = "✓ All validation checks passed"
                logger.info(f"[PHASE 6.8] ✓ VALIDATION PASSED - All checks successful")
            else:
                issues = []
                if constraint_report.total_errors > 0:
                    issues.append(f"{constraint_report.total_errors} static analysis error(s)")
                if constraint_report.total_warnings > 0:
                    issues.append(f"{constraint_report.total_warnings} warning(s)")
                if test_api_report and test_api_report["status"] == "failed":
                    issues.append(f"{test_api_report['statistics']['failed']} test failure(s)")
                    if test_api_report['statistics']['errors'] > 0:
                        issues.append(f"{test_api_report['statistics']['errors']} test error(s)")
                
                issue_str = ", ".join(issues) if issues else "unknown issues"
                overall_summary = f"✗ Validation failed: {issue_str}"
                logger.warning(f"[PHASE 6.8] ✗ VALIDATION FAILED - {issue_str}")
            
            validation_report = ValidationReport(
                overall_status="passed" if overall_passed else "failed",
                overall_summary=overall_summary,
                constraint_check=constraint_api_report,
                test_results=test_api_report,
                total_issues=total_errors + total_warnings,
                total_errors=total_errors,
                total_warnings=total_warnings,
                validation_stages=validation_stages
            )
            logger.info(f"========== PHASE 6 END: Validation Complete ==========")
        except Exception as e:
            logger.error(f"[PHASE 6] Validation pipeline error: {str(e)}", exc_info=True)
            # If validation fails, just skip it but continue
    else:
        logger.info(f"[PHASE 6] Validation skipped (validation disabled)")
    
    # Step 5: Return complete response
    logger.info(f"[PHASE 5.6] ✓ /generate-patch endpoint returning response")
    logger.info(f"========== PHASE 5.6 END: Response Ready ==========")
    
    return GeneratePatchResponse(
        query=request.query,
        unified_diff=unified_diff,
        stats=stats,
        generated_code=generated_code,
        file_path=request.file_path,
        validation=validation_report
    )


@router.post("/analyze-test-mapping")
async def analyze_test_mapping(repo_path: str = "/app/test-project"):
    """
    Analyze test-to-code mapping (Phase 7.1).
    
    Determines which test files cover which source code files by analyzing imports
    and file structure.
    
    Args:
        repo_path: Path to the repository (default: /app/test-project for Docker)
    
    Returns:
        Mapping report containing:
        - statistics: Coverage statistics
        - test_to_source_mapping: Which tests cover which source files
        - source_to_test_mapping: Which tests cover each source file
        - uncovered_sources: Source files not covered by any tests
        - details: Lists of all test and source files discovered
    """
    logger.info(f"========== PHASE 7.1 START: Test-to-Code Mapping Analysis ==========")
    logger.info(f"[PHASE 7.1] Repository path: {repo_path}")
    
    try:
        # Analyze repository
        logger.info(f"[PHASE 7.1] Starting test-to-code mapping analysis...")
        report = get_test_to_code_mapping(repo_path)
        
        logger.info(f"[PHASE 7.1] ✓ Analysis complete")
        logger.info(f"[PHASE 7.1] Statistics:")
        stats = report.get("statistics", {})
        logger.info(f"  - Total test files: {stats.get('total_test_files', 0)}")
        logger.info(f"  - Total source files: {stats.get('total_source_files', 0)}")
        logger.info(f"  - Covered source files: {stats.get('covered_source_files', 0)}")
        logger.info(f"  - Coverage: {stats.get('coverage_percentage', 0):.1f}%")
        
        logger.info(f"========== PHASE 7.1 END: Mapping Complete ==========")
        
        return report
        
    except Exception as e:
        logger.error(f"[PHASE 7.1] Error during test-to-code mapping: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "phase": "7.1",
            "status": "failed"
        }


@router.post("/analyze-coverage")
async def analyze_coverage(repo_path: str = "/app/test-project"):
    """
    Analyze test coverage using pytest and coverage.py (Phase 7.2).
    
    Runs the test suite with coverage.py to collect line-by-line execution data,
    showing which lines of code are covered by tests.
    
    Args:
        repo_path: Path to the repository (default: /app/test-project for Docker)
    
    Returns:
        Coverage report containing:
        - test_summary: Test execution results (passed, failed, errors)
        - statistics: Overall coverage metrics
        - coverage_by_file: Per-file coverage details with executed/missing lines
    """
    logger.info(f"========== PHASE 7.2 START: Coverage Analysis ==========")
    logger.info(f"[PHASE 7.2] Repository path: {repo_path}")
    
    try:
        # Run coverage analysis
        logger.info(f"[PHASE 7.2] Running pytest with coverage.py...")
        report = get_coverage_analysis(repo_path)
        
        # Log statistics
        stats = report.get("statistics", {})
        test_summary = report.get("test_summary", {})
        
        logger.info(f"[PHASE 7.2] ✓ Analysis complete")
        logger.info(f"[PHASE 7.2] Test Results:")
        logger.info(f"  - Passed: {test_summary.get('passed', 0)}/{test_summary.get('total', 0)}")
        logger.info(f"  - Failed: {test_summary.get('failed', 0)}")
        logger.info(f"  - Errors: {test_summary.get('errors', 0)}")
        
        logger.info(f"[PHASE 7.2] Coverage Statistics:")
        logger.info(f"  - Files analyzed: {stats.get('total_files', 0)}")
        logger.info(f"  - Lines covered: {stats.get('covered_lines', 0)}/{stats.get('total_lines', 0)}")
        logger.info(f"  - Overall coverage: {stats.get('overall_coverage', 0):.1f}%")
        
        logger.info(f"========== PHASE 7.2 END: Coverage Analysis Complete ==========")
        
        return report
        
    except Exception as e:
        logger.error(f"[PHASE 7.2] Error during coverage analysis: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "phase": "7.2",
            "status": "failed"
        }
