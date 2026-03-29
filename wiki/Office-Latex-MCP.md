# Local Office + LaTeX MCP

This repository now includes a **local-only** Office/LaTeX MCP server for Markdown report rendering and experiment-result analysis.

## What It Does

- Analyze a Markdown experiment report and produce `analysis_summary.md`
- Convert Markdown into:
  - `DOCX` via `pandoc`
  - `PDF` via `pandoc --pdf-engine=xelatex`
- Optionally append the generated analysis section before rendering

## Files

- `scripts/mcp/office_latex_mcp_server.py`
  Local stdio MCP server
- `scripts/reporting/report_pipeline.py`
  CLI pipeline without MCP
- `mcp/office-latex.local.example.json`
  Example local MCP client configuration
- `examples/sample_experiment_report.md`
  Smoke-test Markdown report

## Local Usage Without MCP

```bash
python scripts/reporting/report_pipeline.py examples/sample_experiment_report.md
```

This generates outputs under `examples/report_outputs/` by default.

## Local MCP Usage

Copy the example config and adapt the absolute paths if needed:

```json
{
  "mcpServers": {
    "office-latex-local": {
      "command": "python",
      "args": [
        "C:/Users/eos/Desktop/101/AutoCYPAmber-main/scripts/mcp/office_latex_mcp_server.py"
      ],
      "cwd": "C:/Users/eos/Desktop/101/AutoCYPAmber-main"
    }
  }
}
```

Because this is the **local-only** option, the repo does not modify your global MCP settings automatically.

## Requirements

- `pandoc`
- `xelatex`
- Python 3

The current machine already has `pandoc` and `xelatex`, so the local pipeline can run immediately.
