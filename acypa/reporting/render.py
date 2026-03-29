import os
import shutil
import subprocess
from typing import Dict, List, Optional

from ..utils.system import summarize_process_output, write_file
from .analysis import analyze_markdown_results


def _run_command(argv: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def render_markdown_bundle(
    markdown_path: str,
    output_dir: Optional[str] = None,
    include_analysis: bool = True,
    metadata_title: Optional[str] = None,
) -> Dict[str, object]:
    """Render a Markdown report to DOCX and PDF, optionally appending analysis."""
    markdown_path = os.path.abspath(markdown_path)
    if not os.path.exists(markdown_path):
        return {"status": "error", "message": f"Markdown file not found: {markdown_path}"}

    pandoc = shutil.which("pandoc")
    xelatex = shutil.which("xelatex")
    if not pandoc:
        return {"status": "error", "message": "pandoc was not found on PATH."}
    if not xelatex:
        return {"status": "error", "message": "xelatex was not found on PATH."}

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(markdown_path), "report_outputs")
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    working_markdown = markdown_path
    analysis_result = None
    if include_analysis:
        analysis_result = analyze_markdown_results(markdown_path, output_dir=output_dir)
        if analysis_result.get("status") != "success":
            return analysis_result
        with open(markdown_path, "r", encoding="utf-8") as src_handle:
            original = src_handle.read().rstrip() + "\n\n"
        with open(analysis_result["analysis_markdown"], "r", encoding="utf-8") as analysis_handle:
            analysis = analysis_handle.read()
        combined_path = os.path.join(output_dir, "combined_report.md")
        write_file(combined_path, original + analysis)
        working_markdown = combined_path

    base_name = os.path.splitext(os.path.basename(markdown_path))[0]
    docx_path = os.path.join(output_dir, f"{base_name}.docx")
    pdf_path = os.path.join(output_dir, f"{base_name}.pdf")

    common_args: List[str] = [pandoc, working_markdown, "--from", "markdown", "--standalone"]
    if metadata_title:
        common_args.extend(["--metadata", f"title={metadata_title}"])

    docx_res = _run_command(common_args + ["--to", "docx", "--output", docx_path])
    if docx_res.returncode != 0 or not os.path.exists(docx_path):
        return {
            "status": "error",
            "message": f"DOCX rendering failed: {summarize_process_output(docx_res.stdout, docx_res.stderr)}",
        }

    pdf_res = _run_command(common_args + ["--pdf-engine=xelatex", "--to", "pdf", "--output", pdf_path])
    if pdf_res.returncode != 0 or not os.path.exists(pdf_path):
        return {
            "status": "error",
            "message": f"PDF rendering failed: {summarize_process_output(pdf_res.stdout, pdf_res.stderr)}",
            "docx": docx_path,
        }

    result: Dict[str, object] = {
        "status": "success",
        "source_markdown": markdown_path,
        "working_markdown": working_markdown,
        "docx": docx_path,
        "pdf": pdf_path,
    }
    if analysis_result is not None:
        result["analysis_markdown"] = analysis_result["analysis_markdown"]
        result["findings"] = analysis_result["findings"]
    return result
