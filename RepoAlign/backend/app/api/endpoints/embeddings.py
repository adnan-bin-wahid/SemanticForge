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
from app.services.coverage_graph_enricher_integration import get_coverage_graph_enrichment
from app.services.test_node_creator import create_test_nodes
from app.services.dynamic_profiler_integration import get_dynamic_profiling
from app.services.call_trace_processor_integration import get_processed_trace
from app.services.dynamic_call_graph_enricher_integration import enrich_dynamic_call_graph
from app.services.runtime_type_collector_integration import collect_runtime_types
from app.services.runtime_type_graph_enricher_integration import enrich_function_types
from app.services.dynamic_analysis_service_integration import run_dynamic_analysis
from app.services.file_watcher_integration import (
    start_file_watcher, stop_file_watcher, get_watcher_status, 
    get_pending_changes, consume_changes, clear_changes
)
from app.services.git_diff_integration import (
    start_git_diff_poller, stop_git_diff_poller, get_git_poller_status,
    get_pending_git_changes, consume_git_changes, clear_git_changes
)
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


@router.post("/create-test-nodes")
async def create_test_nodes_endpoint(repo_path: str = "/app/test-project"):
    """
    Create Test nodes in Neo4j from discovered test files (Phase 7.3 prep).
    
    Discovers all test files in the repository and creates Test nodes
    in the Neo4j graph for linking with functions via COVERED_BY edges.
    
    Args:
        repo_path: Path to the repository (default: /app/test-project for Docker)
    
    Returns:
        Report containing number of Test nodes created
    """
    logger.info(f"[PHASE 7.3] Creating Test nodes from discovered test files")
    logger.info(f"[PHASE 7.3] Repository path: {repo_path}")
    
    try:
        count = create_test_nodes(repo_path)
        
        logger.info(f"[PHASE 7.3] ✓ Test node creation complete")
        logger.info(f"[PHASE 7.3] Created {count} Test nodes")
        
        return {
            "phase": "7.3",
            "title": "Test Node Creation",
            "status": "success",
            "nodes_created": count
        }
        
    except Exception as e:
        logger.error(f"[PHASE 7.3] Error creating test nodes: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "phase": "7.3",
            "status": "failed"
        }


@router.post("/enrich-coverage-graph")
async def enrich_coverage_graph(repo_path: str = "/app/test-project"):
    """
    Enrich the knowledge graph with COVERED_BY edges (Phase 7.3).
    
    Processes the coverage report and creates edges between Function nodes
    and Test nodes, linking functions to the tests that execute them.
    
    Args:
        repo_path: Path to the repository (default: /app/test-project for Docker)
    
    Returns:
        Enrichment report containing:
        - functions_processed: Number of functions analyzed
        - edges_created: Number of COVERED_BY edges created
        - coverage_data: Coverage statistics
    """
    logger.info(f"========== PHASE 7.3 START: Coverage Graph Enrichment ==========")
    logger.info(f"[PHASE 7.3] Repository path: {repo_path}")
    
    try:
        # Enrich the coverage graph
        logger.info(f"[PHASE 7.3] Processing coverage data and creating graph edges...")
        result = get_coverage_graph_enrichment(repo_path)
        
        # Log enrichment results
        logger.info(f"[PHASE 7.3] ✓ Graph enrichment complete")
        logger.info(f"[PHASE 7.3] Enrichment Statistics:")
        logger.info(f"  - Functions processed: {result.get('functions_processed', 0)}")
        logger.info(f"  - COVERED_BY edges created: {result.get('edges_created', 0)}")
        
        logger.info(f"========== PHASE 7.3 END: Coverage Graph Enrichment Complete ==========")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 7.3] Error during graph enrichment: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "phase": "7.3",
            "status": "failed"
        }


@router.post("/run-dynamic-profiling")
async def run_dynamic_profiling(repo_path: str = "/app/test-project"):
    """
    Run dynamic profiling on test execution (Phase 7.4).
    
    Captures function call events during test execution using sys.setprofile.
    Produces a raw log of the dynamic call stack.
    
    Args:
        repo_path: Path to the repository (default: /app/test-project for Docker)
    
    Returns:
        Report containing call traces and call graph
    """
    logger.info(f"[PHASE 7.4] Starting dynamic profiling for {repo_path}")
    
    try:
        result = get_dynamic_profiling(repo_path)
        
        logger.info(f"[PHASE 7.4] ✓ Dynamic profiling complete")
        logger.info(f"[PHASE 7.4] Captured {result['summary']['total_events']} events")
        logger.info(f"[PHASE 7.4] Unique function pairs: {result['summary']['unique_call_pairs']}")
        logger.info(f"[PHASE 7.4] Max call depth: {result['summary']['max_call_depth']}")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 7.4] Error during dynamic profiling: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "phase": "7.4",
            "status": "failed"
        }


@router.post("/process-call-trace")
async def process_call_trace(repo_path: str = "/app/test-project"):
    """
    Process dynamic call traces into structured function call lists (Phase 7.5).
    
    Runs dynamic profiling (Phase 7.4) and processes the raw trace data into:
    - Unique function-to-function call pairs
    - Call frequency statistics
    - Dynamic call graph
    - Functions most called and most called by
    
    Args:
        repo_path: Path to the repository (default: /app/test-project for Docker)
    
    Returns:
        Processed trace with call pairs, call graph, and statistics
    """
    logger.info(f"[PHASE 7.5] Processing call traces for {repo_path}")
    
    try:
        result = get_processed_trace(repo_path)
        
        logger.info(f"[PHASE 7.5] ✓ Trace processing complete")
        logger.info(f"[PHASE 7.5] Unique call pairs: {result['summary']['total_unique_pairs']}")
        logger.info(f"[PHASE 7.5] Unique functions: {result['summary']['total_unique_functions']}")
        logger.info(f"[PHASE 7.5] Total invocations: {result['summary']['total_call_invocations']}")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 7.5] Error during trace processing: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "phase": "7.5",
            "status": "failed"
        }


@router.post("/enrich-dynamic-call-graph")
async def enrich_dynamic_call_graph_endpoint(repo_path: str = "/app/test-project"):
    """
    Create DYNAMICALLY_CALLS edges in Neo4j based on processed trace data (Phase 7.6).
    
    Orchestrates the full dynamic analysis pipeline:
    1. Phase 7.4: Dynamic profiling with sys.setprofile
    2. Phase 7.5: Process trace data into call pairs
    3. Phase 7.6: Create DYNAMICALLY_CALLS edges in Neo4j
    
    The result enriches the knowledge graph with actual runtime function call relationships.
    
    Args:
        repo_path: Path to the repository (default: /app/test-project for Docker)
    
    Returns:
        Summary of edges created, statistics, and enrichment details
    """
    logger.info(f"[PHASE 7.6] Enriching dynamic call graph for {repo_path}")
    
    try:
        result = enrich_dynamic_call_graph(repo_path)
        
        if result.get("status") == "success":
            summary = result.get("summary", {})
            logger.info(f"[PHASE 7.6] ✓ Enrichment complete")
            logger.info(f"[PHASE 7.6] Edges created: {summary.get('edges_created', 0)}")
            logger.info(f"[PHASE 7.6] Edges updated: {summary.get('edges_updated', 0)}")
            logger.info(f"[PHASE 7.6] Failed edges: {summary.get('failed_edges', 0)}")
            logger.info(f"[PHASE 7.6] Missing nodes: {summary.get('missing_nodes', 0)}")
            
            stats = result.get("statistics", {})
            logger.info(f"[PHASE 7.6] Total DYNAMICALLY_CALLS edges in graph: {stats.get('total_dynamically_calls_edges', 0)}")
            logger.info(f"[PHASE 7.6] Total call invocations: {stats.get('total_call_count', 0)}")
        else:
            logger.error(f"[PHASE 7.6] Enrichment failed: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 7.6] Error during graph enrichment: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "phase": "7.6",
            "status": "failed"
        }


@router.post("/collect-runtime-types")
async def collect_runtime_types_endpoint(repo_path: str = "/app/test-project"):
    """
    Collect and analyze runtime type information (Phase 7.7).
    
    Runs the full dynamic analysis pipeline with enhanced type collection:
    1. Phase 7.4: Dynamic profiling with argument type capture
    2. Phase 7.7: Type analysis and aggregation
    
    The result includes observed types for each function's arguments,
    type signatures, and polymorphism analysis.
    
    Args:
        repo_path: Path to the repository (default: /app/test-project for Docker)
    
    Returns:
        Summary of collected types, function signatures, and statistics
    """
    logger.info(f"[PHASE 7.7] Collecting runtime types for {repo_path}")
    
    try:
        result = collect_runtime_types(repo_path)
        
        if result.get("status") == "success":
            summary = result.get("summary", {})
            logger.info(f"[PHASE 7.7] ✓ Type collection complete")
            logger.info(f"[PHASE 7.7] Functions with types: {summary.get('functions_with_types', 0)}")
            logger.info(f"[PHASE 7.7] Total call events: {summary.get('total_call_events_processed', 0)}")
            logger.info(f"[PHASE 7.7] Unique types observed: {summary.get('unique_types_observed', 0)}")
            
            stats = result.get("type_statistics", {})
            logger.info(f"[PHASE 7.7] Functions with polymorphic types: {stats.get('functions_with_polymorphic_types', 0)}")
            logger.info(f"[PHASE 7.7] Functions with consistent types: {stats.get('functions_with_consistent_types', 0)}")
        else:
            logger.error(f"[PHASE 7.7] Type collection failed: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 7.7] Error during type collection: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "phase": "7.7",
            "status": "failed"
        }


@router.post("/enrich-function-types")
async def enrich_function_types_endpoint(repo_path: str = "/app/test-project"):
    """
    Enrich Function nodes in Neo4j with runtime type properties (Phase 7.8).
    
    Runs the full dynamic analysis pipeline with type enrichment:
    1. Phase 7.4: Dynamic profiling with argument type capture
    2. Phase 7.7: Runtime type collection and analysis
    3. Phase 7.8: Add type properties to Function nodes in Neo4j
    
    The result enriches the Function nodes with properties:
    - observed_types: List of types observed for function arguments
    - type_signatures: List of observed type signatures
    - is_polymorphic: Boolean indicating if function has multiple signatures
    - signature_variants: Count of distinct type signatures observed
    
    Args:
        repo_path: Path to the repository (default: /app/test-project for Docker)
    
    Returns:
        Summary of functions updated, type properties added, and polymorphism analysis
    """
    logger.info(f"[PHASE 7.8] Enriching function types in Neo4j for {repo_path}")
    
    try:
        result = enrich_function_types(repo_path)
        
        if result.get("status") == "success":
            summary = result.get("summary", {})
            logger.info(f"[PHASE 7.8] ✓ Type enrichment complete")
            logger.info(f"[PHASE 7.8] Functions updated: {summary.get('functions_updated', 0)}")
            logger.info(f"[PHASE 7.8] Properties added: {summary.get('properties_added', 0)}")
            logger.info(f"[PHASE 7.8] Polymorphic functions identified: {summary.get('polymorphic_functions_identified', 0)}")
            
            enriched_stats = result.get("enriched_functions_statistics", {})
            logger.info(f"[PHASE 7.8] Functions in graph with types: {enriched_stats.get('functions_with_types', 0)}")
            logger.info(f"[PHASE 7.8] Polymorphic functions in graph: {enriched_stats.get('functions_with_polymorphic_types', 0)}")
        else:
            logger.error(f"[PHASE 7.8] Enrichment failed: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 7.8] Error during function type enrichment: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "phase": "7.8",
            "status": "failed"
        }


@router.post("/run-dynamic-analysis")
async def run_dynamic_analysis_endpoint(repo_path: str = "/app/test-project"):
    """
    Run the complete dynamic analysis pipeline (Phase 7.9).
    
    Orchestrates all dynamic analysis phases to enrich the knowledge graph:
    1. Phase 7.4: Dynamic profiling with argument type capture via sys.setprofile
    2. Phase 7.5: Process raw trace data into structured call pairs
    3. Phase 7.6: Create DYNAMICALLY_CALLS edges in Neo4j graph
    4. Phase 7.7: Collect and analyze runtime type information
    5. Phase 7.8: Add type properties to Function nodes in Neo4j
    
    This single endpoint provides end-to-end dynamic analysis enrichment.
    
    The result includes:
    - Dynamic call relationships with invocation counts
    - Runtime type signatures for each function
    - Polymorphism analysis (functions with multiple signatures)
    - Complete type coverage statistics
    - Neo4j graph enrichment summary
    
    Args:
        repo_path: Path to the repository (default: /app/test-project for Docker)
    
    Returns:
        Comprehensive summary of all pipeline phases with execution times,
        statistics, and detailed results from each phase
    """
    logger.info(f"[PHASE 7.9] Running complete dynamic analysis pipeline for {repo_path}")
    
    try:
        result = run_dynamic_analysis(repo_path)
        
        if result.get("status") == "success":
            summary = result.get("execution_summary", {})
            logger.info(f"[PHASE 7.9] ✓ Dynamic analysis pipeline completed successfully")
            
            # Log execution times
            for phase_name, phase_info in summary.items():
                exec_time = phase_info.get("execution_time_seconds", 0)
                status = phase_info.get("status", "unknown")
                logger.info(f"[PHASE 7.9] {phase_name}: {status} ({exec_time}s)")
            
            # Log pipeline metrics
            metrics = result.get("pipeline_metrics", {})
            logger.info(f"[PHASE 7.9] Total execution time: {result.get('total_execution_time_seconds', 0)}s")
            logger.info(f"[PHASE 7.9] Successful phases: {metrics.get('successful_phases', 0)}/{metrics.get('total_phases', 5)}")
            logger.info(f"[PHASE 7.9] Total call events captured: {metrics.get('total_call_events_captured', 0)}")
            logger.info(f"[PHASE 7.9] Unique call pairs: {metrics.get('unique_call_pairs', 0)}")
            logger.info(f"[PHASE 7.9] DYNAMICALLY_CALLS edges: {metrics.get('dynamically_calls_edges_created', 0)}")
            logger.info(f"[PHASE 7.9] Functions with runtime types: {metrics.get('functions_with_runtime_types', 0)}")
            logger.info(f"[PHASE 7.9] Unique types observed: {metrics.get('unique_types_observed', 0)}")
            logger.info(f"[PHASE 7.9] Function nodes updated: {metrics.get('function_nodes_updated_with_types', 0)}")
            logger.info(f"[PHASE 7.9] Polymorphic functions: {metrics.get('polymorphic_functions_identified', 0)}")
        else:
            failed_phase = result.get("failed_at_phase", "unknown")
            logger.error(f"[PHASE 7.9] Pipeline failed at Phase {failed_phase}")
            logger.error(f"[PHASE 7.9] Error: {result.get('failure_details', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 7.9] Error running dynamic analysis pipeline: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "phase": "7.9",
            "status": "failed"
        }


@router.post("/start-file-watcher")
async def start_file_watcher_endpoint(repo_path: str = "/app/test-project"):
    """
    Start the background file system watcher (Phase 8.1).
    
    Initializes a watchdog observer to monitor the repository directory for
    file system events (create, delete, modify). The watcher runs in the background
    and queues detected changes for processing by subsequent phases.
    
    Only monitors Python files (.py, .pyi) and ignores common directories
    like __pycache__, .git, .venv, node_modules, etc.
    
    Args:
        repo_path: Path to the repository to monitor (default: /app/test-project for Docker)
    
    Returns:
        Status dictionary containing:
        - status: "started", "already_running", or "failed"
        - message: Human-readable status message
        - repo_path: Repository path being monitored
        - start_time: ISO format timestamp when watcher started
        - error: Error message if status is "failed"
    """
    logger.info(f"========== PHASE 8.1 START: File Watcher ==========")
    logger.info(f"[PHASE 8.1] Starting file system watcher for {repo_path}")
    
    try:
        result = start_file_watcher(repo_path)
        
        if result.get("status") == "started":
            logger.info(f"[PHASE 8.1] ✓ File watcher started successfully")
            logger.info(f"[PHASE 8.1] Repository path: {repo_path}")
            logger.info(f"[PHASE 8.1] Start time: {result.get('start_time')}")
        elif result.get("status") == "already_running":
            logger.info(f"[PHASE 8.1] File watcher already running since {result.get('start_time')}")
        else:
            logger.error(f"[PHASE 8.1] Failed to start file watcher: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.1] Error starting file watcher: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "phase": "8.1"
        }


@router.post("/stop-file-watcher")
async def stop_file_watcher_endpoint():
    """
    Stop the background file system watcher (Phase 8.1).
    
    Gracefully shuts down the watchdog observer and returns statistics about
    detected changes before stopping.
    
    Returns:
        Status dictionary containing:
        - status: "stopped", "not_running", or "failed"
        - message: Human-readable status message
        - events_detected: Total file system events detected since start
        - events_by_type: Breakdown by event type (created, deleted, modified)
        - error: Error message if status is "failed"
    """
    logger.info(f"[PHASE 8.1] Stopping file system watcher")
    
    try:
        result = stop_file_watcher()
        
        if result.get("status") == "stopped":
            logger.info(f"[PHASE 8.1] ✓ File watcher stopped successfully")
            logger.info(f"[PHASE 8.1] Events detected: {result.get('events_detected', 0)}")
            events_by_type = result.get('events_by_type', {})
            logger.info(f"[PHASE 8.1] Created: {events_by_type.get('created', 0)}, "
                       f"Deleted: {events_by_type.get('deleted', 0)}, "
                       f"Modified: {events_by_type.get('modified', 0)}")
        elif result.get("status") == "not_running":
            logger.info(f"[PHASE 8.1] File watcher is not running")
        else:
            logger.error(f"[PHASE 8.1] Failed to stop file watcher: {result.get('error', 'Unknown error')}")
        
        logger.info(f"========== PHASE 8.1 END ==========")
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.1] Error stopping file watcher: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "phase": "8.1"
        }


@router.get("/watcher-status")
async def get_watcher_status_endpoint():
    """
    Get the current status of the file system watcher (Phase 8.1).
    
    Returns detailed status information about the running watcher,
    including uptime, event counts, and queue status.
    
    Returns:
        Status dictionary containing:
        - is_running: Boolean indicating if watcher is active
        - repo_path: Repository path being monitored
        - start_time: ISO format timestamp when watcher started
        - uptime_seconds: How long the watcher has been running
        - events_detected: Total file system events detected
        - events_by_type: Breakdown by event type (created, deleted, modified)
        - queue_size: Number of unprocessed changes in queue
    """
    try:
        result = get_watcher_status()
        
        if result.get("is_running"):
            logger.debug(f"[PHASE 8.1] Watcher status: running, queue size: {result.get('queue_size', 0)}")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.1] Error getting watcher status: {str(e)}", exc_info=True)
        return {
            "is_running": False,
            "error": str(e)
        }


@router.get("/pending-changes")
async def get_pending_changes_endpoint(max_changes: int = 100):
    """
    Get pending file system changes without consuming them (Phase 8.1).
    
    Retrieves up to max_changes detected file changes from the queue
    without removing them. Use this to preview changes before consuming.
    
    Args:
        max_changes: Maximum number of changes to retrieve (default: 100)
    
    Returns:
        Dictionary containing:
        - status: "success", "watcher_not_running", or "failed"
        - pending_changes: Number of changes in the queue
        - changes: List of change events with structure:
            - event_type: "created", "deleted", or "modified"
            - file_path: Absolute path to the changed file
            - timestamp: ISO format timestamp of the event
    """
    try:
        result = get_pending_changes(max_changes)
        
        changes = result.get("changes", [])
        if changes:
            logger.debug(f"[PHASE 8.1] Retrieved {len(changes)} pending changes")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.1] Error getting pending changes: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


@router.post("/consume-changes")
async def consume_changes_endpoint(max_changes: int = 100):
    """
    Consume (remove from queue) pending file system changes (Phase 8.1).
    
    Retrieves up to max_changes detected file changes from the queue
    and removes them from the queue. These changes are then passed to
    subsequent phases (8.2 Git Diff, 8.3 Queue, etc.) for processing.
    
    Args:
        max_changes: Maximum number of changes to consume (default: 100)
    
    Returns:
        Dictionary containing:
        - status: "success", "watcher_not_running", or "failed"
        - consumed_changes: Number of changes consumed
        - changes: List of consumed change events with structure:
            - event_type: "created", "deleted", or "modified"
            - file_path: Absolute path to the changed file
            - timestamp: ISO format timestamp of the event
    """
    try:
        result = consume_changes(max_changes)
        
        consumed = result.get("consumed_changes", 0)
        if consumed > 0:
            logger.info(f"[PHASE 8.1] Consumed {consumed} changes from queue")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.1] Error consuming changes: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


@router.post("/clear-changes")
async def clear_changes_endpoint():
    """
    Clear all pending file system changes from the queue (Phase 8.1).
    
    Removes all detected file changes from the queue without processing them.
    Use this to reset the watcher state or skip accumulated changes.
    
    Returns:
        Dictionary containing:
        - status: "success", "watcher_not_running", or "failed"
        - changes_cleared: Number of changes that were removed from the queue
    """
    try:
        result = clear_changes()
        
        cleared = result.get("changes_cleared", 0)
        if cleared > 0:
            logger.info(f"[PHASE 8.1] Cleared {cleared} changes from queue")
        else:
            logger.debug(f"[PHASE 8.1] No changes to clear")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.1] Error clearing changes: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


# ============================================================
# PHASE 8.2: Git Diff Polling (Alternative)
# ============================================================

@router.post("/start-git-diff-poller")
async def start_git_diff_poller_endpoint(repo_path: str = "/app/test-project", 
                                        poll_interval: int = 2):
    """
    Start the Git Diff Poller for change detection (Phase 8.2).
    
    Initializes a Git-based alternative change detection mechanism that periodically
    runs `git diff` and `git status` to detect modified, added, and deleted files.
    This provides a robust, Git-aware strategy for tracking repository changes.
    
    The poller runs in the background and queues detected changes for processing.
    Only monitors Python files (.py, .pyi) and ignores common directories
    like __pycache__, .git, .venv, node_modules, etc.
    
    Args:
        repo_path: Path to the Git repository to monitor (default: /app/test-project for Docker)
        poll_interval: Seconds between git diff polls (default: 2 seconds)
    
    Returns:
        Status dictionary containing:
        - status: "started", "already_running", or "failed"
        - message: Human-readable status message
        - repo_path: Repository path being monitored
        - start_time: ISO format timestamp when poller started
        - error: Error message if status is "failed"
    """
    logger.info(f"========== PHASE 8.2 START: Git Diff Poller ==========")
    logger.info(f"[PHASE 8.2] Starting Git diff poller for {repo_path} (poll interval: {poll_interval}s)")
    
    try:
        result = start_git_diff_poller(repo_path, poll_interval)
        
        if result.get("status") == "started":
            logger.info(f"[PHASE 8.2] ✓ Git diff poller started successfully")
            logger.info(f"[PHASE 8.2] Repository path: {repo_path}")
            logger.info(f"[PHASE 8.2] Start time: {result.get('start_time')}")
            logger.info(f"[PHASE 8.2] Poll interval: {poll_interval} seconds")
        elif result.get("status") == "already_running":
            logger.info(f"[PHASE 8.2] Git diff poller already running since {result.get('start_time')}")
        else:
            logger.error(f"[PHASE 8.2] Failed to start git diff poller: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.2] Error starting git diff poller: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "phase": "8.2"
        }


@router.post("/stop-git-diff-poller")
async def stop_git_diff_poller_endpoint():
    """
    Stop the Git Diff Poller (Phase 8.2).
    
    Gracefully shuts down the Git diff poller and returns statistics about
    detected changes before stopping.
    
    Returns:
        Status dictionary containing:
        - status: "stopped", "not_running", or "failed"
        - message: Human-readable status message
        - events_detected: Total file changes detected since start
        - events_by_type: Breakdown by event type (modified, added, deleted, renamed)
        - error: Error message if status is "failed"
    """
    logger.info(f"[PHASE 8.2] Stopping Git diff poller")
    
    try:
        result = stop_git_diff_poller()
        
        if result.get("status") == "stopped":
            logger.info(f"[PHASE 8.2] ✓ Git diff poller stopped successfully")
            logger.info(f"[PHASE 8.2] Events detected: {result.get('events_detected', 0)}")
            events_by_type = result.get('events_by_type', {})
            logger.info(f"[PHASE 8.2] Modified: {events_by_type.get('modified', 0)}, "
                       f"Added: {events_by_type.get('added', 0)}, "
                       f"Deleted: {events_by_type.get('deleted', 0)}, "
                       f"Renamed: {events_by_type.get('renamed', 0)}")
        elif result.get("status") == "not_running":
            logger.info(f"[PHASE 8.2] Git diff poller is not running")
        else:
            logger.error(f"[PHASE 8.2] Failed to stop git diff poller: {result.get('error', 'Unknown error')}")
        
        logger.info(f"========== PHASE 8.2 END ==========")
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.2] Error stopping git diff poller: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "phase": "8.2"
        }


@router.get("/git-poller-status")
async def get_git_poller_status_endpoint():
    """
    Get the current status of the Git Diff Poller (Phase 8.2).
    
    Returns detailed status information about the running poller,
    including uptime, event counts, queue status, and current commit hash.
    
    Returns:
        Status dictionary containing:
        - is_running: Boolean indicating if poller is active
        - repo_path: Repository path being monitored
        - start_time: ISO format timestamp when poller started
        - uptime_seconds: How long the poller has been running
        - poll_interval_seconds: Seconds between polls
        - events_detected: Total file changes detected
        - events_by_type: Breakdown by event type (modified, added, deleted, renamed)
        - queue_size: Number of unprocessed changes in queue
        - current_commit: First 8 chars of current commit hash
    """
    try:
        result = get_git_poller_status()
        
        if result.get("is_running"):
            logger.debug(f"[PHASE 8.2] Poller status: running, queue size: {result.get('queue_size', 0)}")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.2] Error getting poller status: {str(e)}", exc_info=True)
        return {
            "is_running": False,
            "error": str(e)
        }


@router.get("/pending-git-changes")
async def get_pending_git_changes_endpoint(max_changes: int = 100):
    """
    Get pending Git changes without consuming them (Phase 8.2).
    
    Retrieves up to max_changes detected file changes from the queue
    without removing them. Use this to preview changes before consuming.
    
    Args:
        max_changes: Maximum number of changes to retrieve (default: 100)
    
    Returns:
        Dictionary containing:
        - status: "success", "poller_not_running", or "failed"
        - changes: List of change events with structure:
            - event_type: "modified", "added", "deleted", or "renamed"
            - file_path: Path to the changed file (relative to repo root)
            - timestamp: ISO format timestamp of the event
            - git_status: Git status code (M, A, D, R, etc.)
    """
    try:
        result = get_pending_git_changes(max_changes)
        
        changes = result.get("changes", [])
        if changes:
            logger.debug(f"[PHASE 8.2] Retrieved {len(changes)} pending git changes")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.2] Error getting pending git changes: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "changes": []
        }


@router.post("/consume-git-changes")
async def consume_git_changes_endpoint(max_changes: int = 100):
    """
    Consume (remove from queue) pending Git changes (Phase 8.2).
    
    Retrieves up to max_changes detected file changes from the queue
    and removes them from the queue. These changes are then passed to
    subsequent phases (8.3 Queue, 8.4 AST Diffing, etc.) for processing.
    
    Args:
        max_changes: Maximum number of changes to consume (default: 100)
    
    Returns:
        Dictionary containing:
        - status: "success", "poller_not_running", or "failed"
        - changes: List of consumed change events with structure:
            - event_type: "modified", "added", "deleted", or "renamed"
            - file_path: Path to the changed file (relative to repo root)
            - timestamp: ISO format timestamp of the event
            - git_status: Git status code (M, A, D, R, etc.)
    """
    try:
        result = consume_git_changes(max_changes)
        
        consumed = len(result.get("changes", []))
        if consumed > 0:
            logger.info(f"[PHASE 8.2] Consumed {consumed} changes from git change queue")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.2] Error consuming git changes: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "changes": []
        }


@router.post("/clear-git-changes")
async def clear_git_changes_endpoint():
    """
    Clear all pending Git changes from the queue (Phase 8.2).
    
    Removes all detected file changes from the queue without processing them.
    Use this to reset the poller state or skip accumulated changes.
    
    Returns:
        Dictionary containing:
        - status: "cleared", "poller_not_running", or "failed"
        - changes_cleared: Number of changes that were removed from the queue
    """
    try:
        result = clear_git_changes()
        
        cleared = result.get("changes_cleared", 0)
        if cleared > 0:
            logger.info(f"[PHASE 8.2] Cleared {cleared} changes from git change queue")
        else:
            logger.debug(f"[PHASE 8.2] No git changes to clear")
        
        return result
        
    except Exception as e:
        logger.error(f"[PHASE 8.2] Error clearing git changes: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e),
            "changes_cleared": 0
        }

