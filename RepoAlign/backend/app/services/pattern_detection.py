import ast
from collections import Counter
from typing import Any

from app.models.staged_changes import (
    ChangedSymbol,
    CommitBlockingFinding,
    PatternCandidate,
    PatternDetectionResult,
    PatternSummary,
)
from app.db.neo4j_driver import get_neo4j_driver
from app.services.vector_search import search_by_query


def _safe_parse(content: str) -> ast.AST | None:
    try:
        return ast.parse(content or "")
    except SyntaxError:
        return None


def _extract_features(content: str) -> dict[str, Any]:
    tree = _safe_parse(content)
    if tree is None:
        return {
            "parseable": False,
            "calls": [],
            "imports": [],
            "return_style": "unknown",
            "has_try_except": False,
            "raises": False,
            "parameter_count": 0,
        }

    calls: list[str] = []
    imports: list[str] = []
    returns: list[str] = []
    parameter_count = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and parameter_count == 0:
            parameter_count = len(node.args.args)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Return):
            value = node.value
            if isinstance(value, ast.Dict):
                returns.append("dict")
            elif isinstance(value, ast.Call):
                returns.append("call")
            elif isinstance(value, ast.Constant):
                returns.append(type(value.value).__name__)
            elif value is None:
                returns.append("none")
            else:
                returns.append(type(value).__name__)

    return {
        "parseable": True,
        "calls": sorted(set(calls)),
        "imports": sorted(set(imports)),
        "return_style": Counter(returns).most_common(1)[0][0] if returns else "none",
        "has_try_except": any(isinstance(node, ast.Try) for node in ast.walk(tree)),
        "raises": any(isinstance(node, ast.Raise) for node in ast.walk(tree)),
        "parameter_count": parameter_count,
    }


def _is_helper_candidate(candidate: PatternCandidate) -> bool:
    lowered = candidate.name.lower()
    return lowered.startswith(("validate_", "sanitize_", "parse_", "format_"))


def _summarize_candidates(candidates: list[PatternCandidate]) -> PatternSummary | None:
    if not candidates:
        return None

    implementation_candidates = [
        candidate for candidate in candidates if not _is_helper_candidate(candidate)
    ]
    summary_candidates = implementation_candidates or candidates
    feature_list = [
        _extract_features(candidate.content or "") for candidate in summary_candidates
    ]
    examples = [candidate.name for candidate in candidates[:5]]

    def common_value(key: str, default: Any = None) -> Any:
        values = [features.get(key, default) for features in feature_list]
        return Counter(str(value) for value in values).most_common(1)[0][0]

    common_calls = Counter(
        call for features in feature_list for call in features.get("calls", [])
    )
    common_imports = Counter(
        import_name
        for features in feature_list
        for import_name in features.get("imports", [])
    )

    structural_features = {
        "return_style": common_value("return_style", "unknown"),
        "has_try_except": common_value("has_try_except", False) == "True",
        "raises": common_value("raises", False) == "True",
        "parameter_count": int(common_value("parameter_count", 0)),
        "common_calls": [name for name, count in common_calls.items() if count >= 2][:8],
        "common_imports": [name for name, count in common_imports.items() if count >= 2][:8],
    }

    convention = (
        f"Similar repository symbols usually return {structural_features['return_style']}, "
        f"{'use' if structural_features['has_try_except'] else 'do not usually use'} local try/except, "
        f"and call {', '.join(structural_features['common_calls'][:3]) or 'no repeated helper'}."
    )

    return PatternSummary(
        convention=convention,
        examples=examples,
        structural_features=structural_features,
    )


def _compare_symbol_to_pattern(
    symbol: ChangedSymbol,
    summary: PatternSummary,
    candidate_score: float,
) -> tuple[float, list[CommitBlockingFinding]]:
    symbol_features = _extract_features(symbol.content)
    pattern = summary.structural_features
    findings: list[CommitBlockingFinding] = []
    mismatch_points = 0
    possible_points = 0

    def add_finding(reason: str, matched_pattern: str, suggested_fix: str) -> None:
        findings.append(
            CommitBlockingFinding(
                severity="warning",
                affected_file="staged-change",
                affected_symbol=symbol.name,
                reason=reason,
                matched_pattern=matched_pattern,
                suggested_fix=suggested_fix,
                validation_status="warning",
            )
        )

    possible_points += 1
    if symbol_features["return_style"] != pattern.get("return_style"):
        mismatch_points += 1
        add_finding(
            f"{symbol.name} returns {symbol_features['return_style']} but matched examples usually return {pattern.get('return_style')}",
            "return-style-drift",
            "Align the return shape with the matched repository examples or document why this path differs.",
        )

    possible_points += 1
    if symbol_features["has_try_except"] != pattern.get("has_try_except"):
        mismatch_points += 1
        add_finding(
            "exception handling shape differs from matched repository examples",
            "exception-flow-drift",
            "Use the repository's usual local try/except style for similar code, or intentionally leave this finding ignored.",
        )

    common_calls = set(pattern.get("common_calls", []))
    if common_calls:
        possible_points += 1
        missing_calls = sorted(common_calls - set(symbol_features["calls"]))
        if missing_calls:
            mismatch_points += 1
            add_finding(
                f"missing common helper/service calls used by similar symbols: {', '.join(missing_calls[:4])}",
                "helper-call-drift",
                "Check whether the staged code should use the same helper/service calls as the matched examples.",
            )

    possible_points += 1
    if abs(symbol_features["parameter_count"] - pattern.get("parameter_count", 0)) >= 2:
        mismatch_points += 1
        add_finding(
            f"signature shape differs: {symbol_features['parameter_count']} parameters vs common {pattern.get('parameter_count')}",
            "signature-shape-drift",
            "Compare the staged signature with similar repository symbols.",
        )

    mismatch_score = mismatch_points / max(possible_points, 1)
    confidence = min(1.0, max(0.0, candidate_score) * mismatch_score)

    # A single explicit structural mismatch can be meaningful in small demo
    # repositories. Keep the semantic gate on candidate_score, but do not hide
    # helper/return/exception drift merely because mismatch_score is fractional.
    if candidate_score < 0.45 or mismatch_score < 0.20:
        return mismatch_score, []

    for finding in findings:
        if finding.matched_pattern in {"helper-call-drift", "exception-flow-drift"}:
            finding.severity = "warning"
            finding.validation_status = "warning"

        if confidence >= 0.40 and finding.matched_pattern in {
            "return-style-drift",
            "exception-flow-drift",
        }:
            finding.severity = "error"
            finding.validation_status = "failed"

    return mismatch_score, findings


async def _get_sibling_candidates(symbol: ChangedSymbol) -> list[PatternCandidate]:
    if not symbol.filePath:
        return []

    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (file:File {path: $file_path})-[:DEFINES]->(s)
                WHERE (s:Function OR s:Class) AND s.name <> $symbol_name
                RETURN s.name AS name,
                       labels(s)[0] AS type,
                       s.content AS content,
                       file.path AS path
                LIMIT 8
                """,
                file_path=symbol.filePath,
                symbol_name=symbol.name,
            )
            records = await result.data()
    except Exception:
        return []

    return [
        PatternCandidate(
            name=record["name"],
            type=(record.get("type") or "unknown").lower(),
            score=0.58,
            path=record.get("path"),
            content=record.get("content"),
        )
        for record in records
        if record.get("content")
    ]


async def detect_repository_patterns(
    changed_symbols: list[ChangedSymbol],
    graph_expansion_service: Any,
) -> list[PatternDetectionResult]:
    results: list[PatternDetectionResult] = []

    for symbol in changed_symbols:
        candidates: list[PatternCandidate] = []
        try:
            vector_results = await search_by_query(
                f"{symbol.type} {symbol.name} {symbol.content[:1200]}",
                limit=6,
            )
        except Exception:
            vector_results = []

        symbol_names = [
            result["name"]
            for result in vector_results
            if result.get("name") and result.get("name") != symbol.name
        ]

        expanded_context = {}
        if symbol_names:
            try:
                expanded_context = await graph_expansion_service.expand_context(symbol_names)
            except Exception:
                expanded_context = {}

        for result in vector_results:
            name = result.get("name", "")
            if not name or name == symbol.name:
                continue
            context = expanded_context.get(name, {})
            candidates.append(
                PatternCandidate(
                    name=name,
                    type=result.get("type", "unknown"),
                    score=float(result.get("score", 0.0)),
                    path=context.get("path"),
                    content=context.get("code"),
                )
            )

        sibling_candidates = await _get_sibling_candidates(symbol)
        by_name = {candidate.name: candidate for candidate in candidates}
        for candidate in sibling_candidates:
            existing = by_name.get(candidate.name)
            if not existing or candidate.score > existing.score:
                by_name[candidate.name] = candidate
        candidates = list(by_name.values())

        candidates = [
            candidate for candidate in candidates if candidate.content and candidate.score >= 0.45
        ][:5]
        summary = _summarize_candidates(candidates)
        if not summary:
            results.append(PatternDetectionResult(changed_symbol=symbol.name))
            continue

        top_score = max(candidate.score for candidate in candidates)
        mismatch_score, findings = _compare_symbol_to_pattern(
            symbol,
            summary,
            top_score,
        )
        results.append(
            PatternDetectionResult(
                changed_symbol=symbol.name,
                candidates=candidates,
                summary=summary,
                mismatch_score=mismatch_score,
                confidence=min(1.0, top_score * mismatch_score),
                findings=findings,
            )
        )

    return results
