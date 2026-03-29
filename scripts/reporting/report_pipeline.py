#!/usr/bin/env python
import argparse
import json
import os
import sys


def _bootstrap_repo() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def main() -> int:
    _bootstrap_repo()
    from acypa.reporting import analyze_markdown_results, render_markdown_bundle

    parser = argparse.ArgumentParser(description="Render Markdown reports to DOCX/PDF and analyze experiment results.")
    parser.add_argument("markdown_path", help="Path to the input Markdown file.")
    parser.add_argument("--output-dir", default=None, help="Directory for generated outputs.")
    parser.add_argument("--analyze-only", action="store_true", help="Only generate the analysis Markdown summary.")
    parser.add_argument("--no-analysis", action="store_true", help="Skip appending the generated analysis before rendering.")
    parser.add_argument("--title", default=None, help="Optional title override for the rendered report.")
    args = parser.parse_args()

    if args.analyze_only:
        result = analyze_markdown_results(args.markdown_path, output_dir=args.output_dir)
    else:
        result = render_markdown_bundle(
            markdown_path=args.markdown_path,
            output_dir=args.output_dir,
            include_analysis=not args.no_analysis,
            metadata_title=args.title,
        )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
