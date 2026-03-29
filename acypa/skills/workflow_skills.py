def skill_prepare_local_smoke_case(config_path: str) -> dict:
    """Prepare the directory layout and resolved config for a local smoke case."""
    from ..workflows import prepare_local_smoke_case

    return prepare_local_smoke_case(config_path)


def skill_run_local_smoke_pipeline(config_path: str) -> dict:
    """Run the full local smoke pipeline from preparation through report rendering."""
    from ..workflows import run_local_smoke_pipeline

    return run_local_smoke_pipeline(config_path)


def skill_analyze_md_stability(run_dir: str, config_path: str = None) -> dict:
    """Run heme-centered trajectory analysis and emit a Markdown report."""
    from ..analysis import analyze_md_stability

    return analyze_md_stability(run_dir=run_dir, config_path=config_path)


def skill_render_md_report(report_md_path: str, output_dir: str = None) -> dict:
    """Render a generated Markdown report into DOCX and PDF without extra report augmentation."""
    from ..reporting import render_markdown_bundle

    return render_markdown_bundle(markdown_path=report_md_path, output_dir=output_dir, include_analysis=False)
