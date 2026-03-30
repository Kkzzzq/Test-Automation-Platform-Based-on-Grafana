from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

MD_OUTPUT = Path(os.getenv("FAULT_REPRO_MD_FILE", "fault_repro_report.md"))
JSON_OUTPUT = Path(os.getenv("FAULT_REPRO_JSON_FILE", "fault_repro_report.json"))


def _md_escape(value: str) -> str:
    return value.replace("```", "''' ")


def build_markdown_report(summary: dict[str, Any], case_results: list[dict[str, Any]], ai_summary: str | None) -> str:
    lines: list[str] = ["# Fault Reproduction & Troubleshooting Report", ""]
    lines.append("## Run Overview")
    lines.append("")
    lines.append(f"- Allure total cases: {summary['allure']['total']}")
    lines.append(f"- Failed/Broken cases: {summary['allure']['failed_or_broken']}")
    lines.append(f"- Replayed failed tests: {summary['replayed_cases']}")
    lines.append(f"- Reproduced original failures: {summary['reproduced_original_failures']}")
    lines.append(f"- Chain interrupted cases: {summary['chain_interrupted_cases']}")
    lines.append("")

    if ai_summary:
        lines.append("## AI Diagnosis Summary")
        lines.append("")
        lines.append(ai_summary.strip())
        lines.append("")

    lines.append("## Case Diagnostics")
    lines.append("")
    if not case_results:
        lines.append("No failed or broken cases were found in allure results.")
        return "\n".join(lines) + "\n"

    for index, item in enumerate(case_results, start=1):
        state = item["state"]
        lines.append(f"### {index}. {item['test_name']}")
        lines.append("")
        lines.append(f"- Replay target: {item.get('replay_target') or 'unsupported'}")
        lines.append(f"- Replay status: {state['replay_status']}")
        lines.append(f"- Chain status: {item.get('chain_status')}")
        lines.append(f"- Reproduced original failure: {item.get('reproduced_original_failure')}")
        lines.append(f"- First abnormal stage: {item.get('first_abnormal_stage')}")
        lines.append(f"- Suspected segment: {item.get('suspected_segment')}")
        lines.append("")

        if item.get("original_failure"):
            lines.append("**Original failure summary**")
            lines.append("")
            lines.append(f"- Message: {_md_escape(item['original_failure'].get('message', ''))}")
            lines.append("")

        confirmed_facts = item.get("confirmed_facts") or []
        if confirmed_facts:
            lines.append("**Confirmed facts**")
            lines.append("")
            for fact in confirmed_facts:
                lines.append(f"- {_md_escape(fact)}")
            lines.append("")

        excluded_scope = item.get("excluded_scope") or []
        if excluded_scope:
            lines.append("**Excluded scope**")
            lines.append("")
            for scope in excluded_scope:
                lines.append(f"- {_md_escape(scope)}")
            lines.append("")

        remaining_scope = item.get("remaining_scope") or []
        if remaining_scope:
            lines.append("**Remaining scope**")
            lines.append("")
            for scope in remaining_scope:
                lines.append(f"- {_md_escape(scope)}")
            lines.append("")

        evidence_lines = item.get("evidence_lines") or []
        if evidence_lines:
            lines.append("**Evidence**")
            lines.append("")
            for evidence in evidence_lines:
                lines.append(f"- {_md_escape(evidence)}")
            lines.append("")

        manual_checks = item.get("manual_checks") or []
        if manual_checks:
            lines.append("**Manual checks**")
            lines.append("")
            for action in manual_checks:
                lines.append(f"1. {_md_escape(action)}")
            lines.append("")

        snapshot_diff = item.get("snapshot_diff")
        if snapshot_diff:
            lines.append("**Snapshot diff**")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(snapshot_diff, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def write_reports(summary: dict[str, Any], case_results: list[dict[str, Any]], ai_summary: str | None) -> None:
    markdown = build_markdown_report(summary, case_results, ai_summary)
    MD_OUTPUT.write_text(markdown, encoding="utf-8")
    JSON_OUTPUT.write_text(
        json.dumps({"summary": summary, "cases": case_results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
