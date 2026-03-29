#!/usr/bin/env python
import json
import os
import sys
from typing import Any, Dict, Optional


def _bootstrap_repo() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def _read_message() -> Optional[Dict[str, Any]]:
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        key, value = line.decode("utf-8").split(":", 1)
        headers[key.strip().lower()] = value.strip()

    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = sys.stdin.buffer.read(length)
    return json.loads(body.decode("utf-8"))


def _write_message(payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    sys.stdout.buffer.write(header)
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def _success_response(message_id: Any, result: Dict[str, Any]) -> None:
    _write_message({"jsonrpc": "2.0", "id": message_id, "result": result})


def _error_response(message_id: Any, code: int, message: str) -> None:
    _write_message(
        {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {"code": code, "message": message},
        }
    )


def _tool_result(message_id: Any, payload: Dict[str, Any], is_error: bool = False) -> None:
    _success_response(
        message_id,
        {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, ensure_ascii=False, indent=2),
                }
            ],
            "isError": is_error,
        },
    )


def main() -> int:
    _bootstrap_repo()
    from acypa.reporting import analyze_markdown_results, render_markdown_bundle

    tools = [
        {
            "name": "analyze_markdown_results",
            "description": "Analyze a Markdown experiment report and produce an analysis summary Markdown file.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "markdown_path": {"type": "string"},
                    "output_dir": {"type": "string"},
                },
                "required": ["markdown_path"],
            },
        },
        {
            "name": "render_markdown_bundle",
            "description": "Render a Markdown report into DOCX and XeLaTeX PDF, optionally appending analysis.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "markdown_path": {"type": "string"},
                    "output_dir": {"type": "string"},
                    "include_analysis": {"type": "boolean"},
                    "metadata_title": {"type": "string"},
                },
                "required": ["markdown_path"],
            },
        },
    ]

    while True:
        message = _read_message()
        if message is None:
            return 0

        method = message.get("method")
        message_id = message.get("id")

        if method == "initialize":
            _success_response(
                message_id,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "office-latex-local",
                        "version": "0.1.0",
                    },
                    "capabilities": {
                        "tools": {},
                    },
                },
            )
            continue

        if method == "notifications/initialized":
            continue

        if method == "tools/list":
            _success_response(message_id, {"tools": tools})
            continue

        if method == "tools/call":
            params = message.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {}) or {}
            try:
                if tool_name == "analyze_markdown_results":
                    result = analyze_markdown_results(
                        markdown_path=arguments["markdown_path"],
                        output_dir=arguments.get("output_dir"),
                    )
                elif tool_name == "render_markdown_bundle":
                    result = render_markdown_bundle(
                        markdown_path=arguments["markdown_path"],
                        output_dir=arguments.get("output_dir"),
                        include_analysis=arguments.get("include_analysis", True),
                        metadata_title=arguments.get("metadata_title"),
                    )
                else:
                    _error_response(message_id, -32601, f"Unknown tool: {tool_name}")
                    continue
            except KeyError as exc:
                _error_response(message_id, -32602, f"Missing required argument: {exc}")
                continue
            except Exception as exc:  # pragma: no cover - defensive
                _tool_result(message_id, {"status": "error", "message": str(exc)}, is_error=True)
                continue

            _tool_result(message_id, result, is_error=result.get("status") != "success")
            continue

        if method == "ping":
            _success_response(message_id, {})
            continue

        if message_id is not None:
            _error_response(message_id, -32601, f"Unsupported method: {method}")


if __name__ == "__main__":
    raise SystemExit(main())
