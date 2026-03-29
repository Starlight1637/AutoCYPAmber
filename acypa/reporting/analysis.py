import os
import re
from typing import Dict, List, Optional

from ..utils.system import write_file

TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")
NUMERIC_RE = re.compile(r"[-+]?\d+(?:\.\d+)?%?")

HIGHER_IS_BETTER = (
    "acc",
    "accuracy",
    "auc",
    "auroc",
    "f1",
    "precision",
    "recall",
    "score",
    "success",
    "yield",
    "bleu",
    "rouge",
    "spearman",
    "pearson",
    "r2",
)

LOWER_IS_BETTER = (
    "loss",
    "error",
    "mae",
    "mse",
    "rmse",
    "rmsd",
    "rmsf",
    "deviation",
    "latency",
    "time",
    "runtime",
    "ppl",
    "perplexity",
)


def _split_table_row(line: str) -> List[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def _parse_numeric(value: str) -> Optional[float]:
    value = value.strip().replace(",", "")
    if not value:
        return None
    match = NUMERIC_RE.search(value)
    if not match:
        return None
    token = match.group(0)
    if token.endswith("%"):
        token = token[:-1]
    try:
        return float(token)
    except ValueError:
        return None


def _metric_direction(header: str) -> Optional[str]:
    header_lower = header.lower()
    if any(token in header_lower for token in HIGHER_IS_BETTER):
        return "max"
    if any(token in header_lower for token in LOWER_IS_BETTER):
        return "min"
    return None


def _extract_tables(lines: List[str]) -> List[Dict[str, object]]:
    tables: List[Dict[str, object]] = []
    i = 0
    while i < len(lines) - 1:
        if "|" not in lines[i] or not TABLE_SEPARATOR_RE.match(lines[i + 1]):
            i += 1
            continue
        header = _split_table_row(lines[i])
        rows: List[List[str]] = []
        i += 2
        while i < len(lines) and "|" in lines[i] and lines[i].strip():
            rows.append(_split_table_row(lines[i]))
            i += 1
        if header and rows:
            tables.append({"header": header, "rows": rows})
        continue
    return tables


def _collect_key_findings(tables: List[Dict[str, object]]) -> List[str]:
    findings: List[str] = []
    for table_idx, table in enumerate(tables, start=1):
        header = table["header"]  # type: ignore[index]
        rows = table["rows"]  # type: ignore[index]
        if len(header) < 2:
            continue
        label_idx = 0
        for col_idx, column_name in enumerate(header[1:], start=1):
            direction = _metric_direction(column_name)
            if not direction:
                continue
            scored_rows = []
            for row in rows:
                if len(row) <= col_idx:
                    continue
                numeric = _parse_numeric(row[col_idx])
                if numeric is None:
                    continue
                label = row[label_idx] if len(row) > label_idx else f"row_{len(scored_rows) + 1}"
                scored_rows.append((label, numeric))
            if not scored_rows:
                continue
            best = max(scored_rows, key=lambda item: item[1]) if direction == "max" else min(scored_rows, key=lambda item: item[1])
            findings.append(
                f"Table {table_idx}: `{best[0]}` is best on `{column_name}` with value `{best[1]:g}`."
            )
    return findings


def _collect_numeric_sentences(text: str, limit: int = 8) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    collected = []
    for sentence in sentences:
        normalized = " ".join(sentence.split()).strip()
        if not normalized:
            continue
        if normalized.startswith("#") or normalized.startswith("|"):
            continue
        if NUMERIC_RE.search(normalized):
            collected.append(normalized)
        if len(collected) >= limit:
            break
    return collected


def _collect_tradeoff_findings(tables: List[Dict[str, object]]) -> List[str]:
    findings: List[str] = []
    for table_idx, table in enumerate(tables, start=1):
        header = table["header"]  # type: ignore[index]
        rows = table["rows"]  # type: ignore[index]
        if len(header) < 3:
            continue

        best_by_metric: Dict[str, str] = {}
        for col_idx, column_name in enumerate(header[1:], start=1):
            direction = _metric_direction(column_name)
            if not direction:
                continue
            scored_rows = []
            for row in rows:
                if len(row) <= col_idx:
                    continue
                numeric = _parse_numeric(row[col_idx])
                if numeric is None:
                    continue
                label = row[0] if row else f"row_{len(scored_rows) + 1}"
                scored_rows.append((label, numeric))
            if not scored_rows:
                continue
            best = max(scored_rows, key=lambda item: item[1]) if direction == "max" else min(scored_rows, key=lambda item: item[1])
            best_by_metric[column_name] = best[0]

        winners = {winner for winner in best_by_metric.values()}
        if len(winners) > 1:
            findings.append(
                f"Table {table_idx}: no single setting dominates every metric; compare quality metrics against cost/runtime before selecting a default."
            )
    return findings


def analyze_markdown_results(markdown_path: str, output_dir: Optional[str] = None) -> Dict[str, object]:
    """Analyze a Markdown experiment report and write a compact analysis summary."""
    markdown_path = os.path.abspath(markdown_path)
    if not os.path.exists(markdown_path):
        return {"status": "error", "message": f"Markdown file not found: {markdown_path}"}

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(markdown_path), "report_outputs")
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    with open(markdown_path, "r", encoding="utf-8") as handle:
        raw = handle.read()

    lines = raw.splitlines()
    tables = _extract_tables(lines)
    findings = _collect_key_findings(tables)
    findings.extend(_collect_tradeoff_findings(tables))
    numeric_sentences = _collect_numeric_sentences(raw)
    headings = [line.strip() for line in lines if line.strip().startswith("#")]

    analysis_lines = [
        "# Automated Result Analysis",
        "",
        "## Report Overview",
        f"- Source: `{markdown_path}`",
        f"- Headings detected: `{len(headings)}`",
        f"- Markdown tables detected: `{len(tables)}`",
        "",
        "## Key Findings",
    ]

    if findings:
        analysis_lines.extend(f"- {item}" for item in findings)
    else:
        analysis_lines.append("- No metric table with an obvious optimization direction was detected.")

    analysis_lines.extend(
        [
            "",
            "## Numeric Evidence",
        ]
    )
    if numeric_sentences:
        analysis_lines.extend(f"- {sentence}" for sentence in numeric_sentences)
    else:
        analysis_lines.append("- No numeric statements were detected in the Markdown body.")

    analysis_lines.extend(
        [
            "",
            "## Suggested Interpretation",
            "- Check whether the top-performing setting is consistently best across all critical metrics, not only one headline metric.",
            "- If there is a tradeoff between quality and runtime, call it out explicitly in the final report.",
            "- Confirm whether the reported sample size, seeds, or replicate count is sufficient before drawing strong conclusions.",
        ]
    )

    output_path = os.path.join(output_dir, "analysis_summary.md")
    write_file(output_path, "\n".join(analysis_lines) + "\n")
    return {
        "status": "success",
        "analysis_markdown": output_path,
        "tables_detected": len(tables),
        "headings_detected": len(headings),
        "findings": findings,
    }
