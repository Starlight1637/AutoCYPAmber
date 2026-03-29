from acypa.reporting import analyze_markdown_results, render_markdown_bundle


def skill_analyze_markdown_results(markdown_path: str, output_dir: str = None) -> dict:
    """
    Skill: Analyze a Markdown experiment report and emit a structured analysis summary.

    Args:
        markdown_path (str): Input Markdown report path.
        output_dir (str, optional): Output directory for generated analysis artifacts.

    Returns:
        dict: Status, analysis Markdown path, and extracted findings.
    """
    return analyze_markdown_results(markdown_path=markdown_path, output_dir=output_dir)


def skill_render_markdown_bundle(
    markdown_path: str,
    output_dir: str = None,
    include_analysis: bool = True,
    metadata_title: str = None,
) -> dict:
    """
    Skill: Convert a Markdown report into DOCX and LaTeX-backed PDF, optionally appending analysis.

    Args:
        markdown_path (str): Input Markdown report path.
        output_dir (str, optional): Output directory for generated report artifacts.
        include_analysis (bool): Whether to append the auto-generated analysis section before rendering.
        metadata_title (str, optional): Optional title override for the rendered report.

    Returns:
        dict: Status and output artifact paths.
    """
    return render_markdown_bundle(
        markdown_path=markdown_path,
        output_dir=output_dir,
        include_analysis=include_analysis,
        metadata_title=metadata_title,
    )
