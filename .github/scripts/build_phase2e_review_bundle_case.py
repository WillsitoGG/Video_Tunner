from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from video_tunner.approval import load_json_object, sha256_path
from video_tunner.post_render_verification import (
    build_post_render_verification,
    save_post_render_verification,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--proposal", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--technical-report", required=True)
    parser.add_argument("--decision-template", required=True)
    parser.add_argument("--portable-ffmpeg-dir", required=True)
    args = parser.parse_args()

    os.environ["VIDEO_TUNNER_FFMPEG_DIR"] = str(Path(args.portable_ffmpeg_dir).resolve())

    analysis = load_json_object(args.analysis)
    proposal = load_json_object(args.proposal)
    authorization = load_json_object(args.authorization)
    plan = load_json_object(args.plan)

    report = build_post_render_verification(
        args.source,
        args.output,
        analysis,
        proposal,
        authorization,
        plan,
        analysis_sha256=sha256_path(args.analysis),
        proposal_sha256=sha256_path(args.proposal),
        authorization_sha256=sha256_path(args.authorization),
    )
    report_path = save_post_render_verification(report, args.technical_report)
    report_sha = sha256_path(report_path)

    template = {
        "schema_version": 1,
        "record_type": "semantic_render_human_review_decision_template",
        "technical_report_file": report_path.name,
        "technical_report_sha256": report_sha,
        "output_sha256": report["output"]["sha256"],
        "plan_fingerprint": report["execution_chain"]["plan_fingerprint"],
        "instructions": (
            "Listen to the ORIGINAL and RENDERED WAV for this case. For every join, replace PENDING with PASS or FAIL "
            "and write a concrete perceptual reason. PASS requires no audible click/pop, no clipped phoneme/word, no "
            "unnatural timing jump and no meaning loss caused by the join."
        ),
        "join_decisions": [
            {
                "join_id": join["id"],
                "output_join_seconds": join["output_join_seconds"],
                "technical_status": join["status"],
                "decision": "PENDING",
                "reason": "",
            }
            for join in report["post_render_join_audits"]
        ],
    }
    template_path = Path(args.decision_template)
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "technical_report": str(report_path),
                "technical_report_sha256": report_sha,
                "technical_pass": report["technical_pass"],
                "join_count": report["summary"]["join_audit_count"],
                "join_statuses": [item["status"] for item in report["post_render_join_audits"]],
                "decision_template": str(template_path),
            },
            indent=2,
        )
    )
    return 0 if report["technical_pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
