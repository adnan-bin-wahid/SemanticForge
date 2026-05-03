"""
Aligned Code Suggestions Endpoint

Generates repository-aligned code suggestions for commit-time findings.
Uses pattern detection results and LLM to produce code that matches
repository conventions.
"""

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Request as FastAPIRequest
from pydantic import BaseModel, Field

from app.services.llm_client import OllamaClient
from app.services.graph_expansion import GraphExpansion
from app.services.vector_search import search_by_query


router = APIRouter()


class AlignedCodeRequest(BaseModel):
    """Request to generate aligned code suggestion."""
    
    workspace_name: str
    affected_file: str
    affected_symbol: Optional[str] = None
    current_code: str  # The staged code that needs alignment
    reason: str  # Why this code needs alignment
    matched_pattern: Optional[str] = None
    pattern_convention: Optional[str] = None  # From pattern detection summary
    pattern_examples: list[str] = Field(default_factory=list)  # Example code from repo
    file_content: Optional[str] = None  # Full file context (if available)


class AlignedCodeResponse(BaseModel):
    """Response with aligned code suggestion."""
    
    status: str = "ok"
    suggested_code: str  # The aligned version
    explanation: str  # Why these changes align with repository patterns
    confidence: float  # 0.0 to 1.0
    changes_summary: str  # Brief description of what changed


async def _build_alignment_prompt(
    request: AlignedCodeRequest,
    retrieved_examples: list[dict[str, Any]]
) -> str:
    """
    Build a prompt for the LLM to generate aligned code.
    
    Args:
        request: The aligned code request
        retrieved_examples: Similar code examples from repository
        
    Returns:
        Formatted prompt string
    """
    prompt_parts = [
        "You are a code alignment assistant. Your task is to rewrite the given code",
        "to match the repository's established patterns and conventions.\n",
    ]
    
    # Add context about the issue
    prompt_parts.append(f"## Issue Detected\n{request.reason}\n")
    
    if request.pattern_convention:
        prompt_parts.append(f"## Repository Convention\n{request.pattern_convention}\n")
    
    # Add examples from repository
    if retrieved_examples:
        prompt_parts.append("## Repository Examples\n")
        for idx, example in enumerate(retrieved_examples[:3], 1):
            name = example.get("name", "unknown")
            content = example.get("content", "")
            if content:
                prompt_parts.append(f"### Example {idx}: {name}\n```python\n{content}\n```\n")
    
    elif request.pattern_examples:
        prompt_parts.append("## Repository Examples\n")
        for idx, example in enumerate(request.pattern_examples[:3], 1):
            prompt_parts.append(f"### Example {idx}\n```python\n{example}\n```\n")
    
    # Add the code to align
    prompt_parts.append("## Code to Align\n")
    if request.affected_symbol:
        prompt_parts.append(f"Symbol: {request.affected_symbol}\n")
    prompt_parts.append(f"```python\n{request.current_code}\n```\n")
    
    # Instructions
    prompt_parts.append(
        "\n## Task\n"
        "Rewrite the code to align with the repository patterns shown above.\n"
        "Requirements:\n"
        "- Keep the same functionality and behavior\n"
        "- Match the style, structure, and conventions from the examples\n"
        "- Use the same return types, error handling patterns, and helper calls\n"
        "- Preserve variable names and logic where appropriate\n"
        "- Output ONLY the aligned Python code, no explanations\n"
        "\n## Aligned Code:\n"
    )
    
    return "".join(prompt_parts)


async def _retrieve_context_for_alignment(
    request: AlignedCodeRequest,
    fastapi_req: FastAPIRequest
) -> list[dict[str, Any]]:
    """
    Retrieve similar code examples from the repository.
    
    Args:
        request: The aligned code request
        fastapi_req: FastAPI request for accessing app state
        
    Returns:
        List of similar code examples with metadata
    """
    query_parts = []
    
    if request.affected_symbol:
        query_parts.append(request.affected_symbol)
    
    if request.matched_pattern:
        # Extract key terms from pattern name
        pattern_terms = request.matched_pattern.replace("-", " ").split()
        query_parts.extend(pattern_terms)
    
    # Add a snippet of the current code
    query_parts.append(request.current_code[:200])
    
    query = " ".join(query_parts)
    
    try:
        results = await search_by_query(query, limit=5)
        
        # Enhance with graph context if available
        if hasattr(fastapi_req.app.state, "graph_expansion_service"):
            graph_service = fastapi_req.app.state.graph_expansion_service
            symbol_names = [r.get("name") for r in results if r.get("name")]
            
            if symbol_names:
                expanded = await graph_service.expand_context(symbol_names[:3])
                # Merge expanded context into results
                for result in results:
                    name = result.get("name")
                    if name and name in expanded:
                        result["content"] = expanded[name].get("code", result.get("content", ""))
        
        return results
        
    except Exception as e:
        # If retrieval fails, continue with pattern examples from request
        return []


def _extract_code_from_llm_response(response: str) -> str:
    """
    Extract clean Python code from LLM response.
    
    Handles cases where LLM adds markdown code blocks or explanations.
    
    Args:
        response: Raw LLM response
        
    Returns:
        Cleaned Python code
    """
    lines = response.strip().split("\n")
    code_lines = []
    in_code_block = False
    
    for line in lines:
        # Detect code block markers
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        
        # Skip explanation lines before/after code
        if not in_code_block:
            # If line looks like code (starts with def, class, import, etc.), include it
            stripped = line.lstrip()
            if stripped and (
                stripped.startswith(("def ", "class ", "import ", "from ", "async def ", "@"))
                or (code_lines and line.startswith((" ", "\t")))  # Indented continuation
            ):
                in_code_block = True
            else:
                continue
        
        if in_code_block:
            code_lines.append(line)
    
    # If we didn't find a clear code block, return the whole response
    if not code_lines:
        return response.strip()
    
    return "\n".join(code_lines).strip()


def _generate_explanation(
    request: AlignedCodeRequest,
    original: str,
    suggested: str
) -> str:
    """
    Generate a human-readable explanation of the changes.
    
    Args:
        request: The aligned code request
        original: Original code
        suggested: Suggested aligned code
        
    Returns:
        Explanation string
    """
    explanations = []
    
    if request.matched_pattern:
        pattern_name = request.matched_pattern.replace("-", " ").title()
        explanations.append(f"Addresses {pattern_name} issue.")
    
    if request.pattern_convention:
        explanations.append(f"Aligns with repository convention: {request.pattern_convention}")
    
    # Simple heuristics for common changes
    if "return" in original and "return" in suggested:
        if original.count("return") != suggested.count("return"):
            explanations.append("Adjusted return statement structure.")
    
    if "try:" in suggested and "try:" not in original:
        explanations.append("Added error handling to match repository patterns.")
    elif "try:" in original and "try:" not in suggested:
        explanations.append("Removed unnecessary error handling.")
    
    # Check for helper calls
    original_calls = set(word for word in original.split() if word.endswith("("))
    suggested_calls = set(word for word in suggested.split() if word.endswith("("))
    new_calls = suggested_calls - original_calls
    
    if new_calls:
        helpers = [c.rstrip("(") for c in new_calls if "validate" in c or "sanitize" in c or "format" in c]
        if helpers:
            explanations.append(f"Added helper calls: {', '.join(helpers[:2])}")
    
    if not explanations:
        explanations.append("Restructured code to match repository patterns.")
    
    return " ".join(explanations)


@router.post("/api/v1/generate-aligned-code", response_model=AlignedCodeResponse)
async def generate_aligned_code(
    request: AlignedCodeRequest,
    fastapi_req: FastAPIRequest
) -> AlignedCodeResponse:
    """
    Generate repository-aligned code suggestion for a finding.
    
    This endpoint takes code that has been flagged during commit analysis
    and generates an aligned version that matches repository patterns and
    conventions.
    
    Args:
        request: Request containing code to align and context
        fastapi_req: FastAPI request for accessing app state
        
    Returns:
        AlignedCodeResponse with suggested aligned code and explanation
        
    Raises:
        HTTPException: If LLM service is unavailable or generation fails
    """
    # Retrieve similar examples from repository
    retrieved_examples = await _retrieve_context_for_alignment(request, fastapi_req)
    
    # Build alignment prompt
    prompt = await _build_alignment_prompt(request, retrieved_examples)
    
    # Generate aligned code using LLM
    try:
        # Get LLM client from app state or create new one
        if hasattr(fastapi_req.app.state, "llm_client"):
            llm_client = fastapi_req.app.state.llm_client
        else:
            # Fallback: create client with default settings
            ollama_url = "http://ollama:11434"
            llm_client = OllamaClient(base_url=ollama_url, model="tinyllama")
        
        # Generate with lower temperature for more consistent alignment
        raw_response = await llm_client.generate(
            prompt=prompt,
            temperature=0.3,  # Lower temperature for more deterministic output
            max_tokens=1000
        )
        
        # Extract clean code from response
        suggested_code = _extract_code_from_llm_response(raw_response)
        
        # Generate explanation
        explanation = _generate_explanation(request, request.current_code, suggested_code)
        
        # Calculate confidence based on retrieval quality and pattern match
        confidence = 0.6  # Base confidence
        if retrieved_examples:
            confidence += 0.2
        if request.pattern_convention:
            confidence += 0.15
        if request.pattern_examples:
            confidence += 0.05
        confidence = min(1.0, confidence)
        
        # Generate changes summary
        original_lines = request.current_code.strip().split("\n")
        suggested_lines = suggested_code.strip().split("\n")
        changes_summary = f"Modified {len(original_lines)} lines into {len(suggested_lines)} lines"
        
        return AlignedCodeResponse(
            suggested_code=suggested_code,
            explanation=explanation,
            confidence=confidence,
            changes_summary=changes_summary
        )
        
    except ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM service unavailable: {str(e)}"
        )
    except TimeoutError as e:
        raise HTTPException(
            status_code=504,
            detail=f"LLM generation timed out: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate aligned code: {str(e)}"
        )
