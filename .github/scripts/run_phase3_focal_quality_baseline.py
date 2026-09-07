from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from video_tunner.approval import sha256_path
from video_tunner.audiovisual_quality import measure_audio_loudness
from video_tunner.human_render_review import validate_human_render_review

EXPECTED_MANIFEST_SHA256 = "d0b12929ede07c1c5a56b074008d0903a868a7cf61e5ce10801c2b682f164ed0"
EXPECTED_CASE_IDS = (
    "ami-es2002b-d-repeat-157",
    "ami-ts3005d-c-repeat-298",
    "ami-es2002b-d-repeat-13",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _case_delta(source: dict[str, float | None], rendered: dict[str, float | None]) -> dict[str, float | None]:
    def delta(key: str) -> float | None:
        left = source.get(key)
        right = rendered.get(key)
        if left is None or right is None:
            return None
        return round(float(right) - float(left), 4)

    return {
        "integrated_loudness_delta_lu": delta("integrated_lufs"),
        "true_peak_delta_db": delta("true_peak_dbtp"),
        "loudness_range_delta_lu": delta("loudness_range_lu"),
    }


def build_baseline(bundle_root: Path, reviews_root: Path) -> dict[str, Any]:
    manifest_path = bundle_root / "manifest.json"
    if sha256_path(manifest_path) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("Phase 2E.5 bundle manifest SHA mismatch.")
    manifest = _load_json(manifest_path)
    cases = manifest.get("cases") or []
    ids = tuple(str(item.get("id") or "") for item in cases)
    if set(ids) != set(EXPECTED_CASE_IDS) or len(ids) != len(EXPECTED_CASE_IDS):
        raise ValueError("Unexpected Phase 2E.5 focal case set.")

    results: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case["id"])
        case_dir = bundle_root / case_id
        technical_path = case_dir / "technical_verification.json"
        technical = _load_json(technical_path)
        technical_sha = sha256_path(technical_path)
        if technical_sha != str(case.get("technical_report_sha256") or "").lower():
            raise ValueError(f"Technical report SHA mismatch for {case_id}.")

        review_path = reviews_root / f"{case_id}-human_render_review.json"
        review = _load_json(review_path)
        validation = validate_human_render_review(
            technical,
            review,
            technical_report_sha256=technical_sha,
        )
        if not validation.get("valid") or not validation.get("human_perceptual_pass"):
            raise ValueError(f"Human PASS evidence invalid for {case_id}: {validation}")

        original = measure_audio_loudness(case_dir / "original.wav")
        rendered = measure_audio_loudness(case_dir / "rendered.wav")
        join = (technical.get("post_render_join_audits") or [None])[0]
        if not isinstance(join, dict) or not join.get("technical_pass"):
            raise ValueError(f"Technical join evidence invalid for {case_id}.")

        results.append(
            {
                "id": case_id,
                "audio_source_id": case.get("audio_source_id"),
                "technical_report_sha256": technical_sha,
                "human_review_sha256": sha256_path(review_path),
                "human_perceptual_pass": True,
                "join_status": join.get("status"),
                "join_metrics": join.get("metrics"),
                "original_review_audio": original,
                "rendered_review_audio": rendered,
                "delta": _case_delta(original, rendered),
            }
        )

    loudness_deltas = [abs(float(item["delta"]["integrated_loudness_delta_lu"])) for item in results]
    peak_deltas = [abs(float(item["delta"]["true_peak_delta_db"])) for item in results]
    return {
        "schema_version": 1,
        "record_type": "phase3_focal_quality_baseline",
        "source_phase2e_run_id": 34119952855,
        "source_bundle_manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "case_count": len(results),
        "distinct_audio_sources": len({str(item["audio_source_id"]) for item in results}),
        "cases": results,
        "observed_summary": {
            "max_abs_integrated_loudness_delta_lu": round(max(loudness_deltas), 4),
            "max_abs_true_peak_delta_db": round(max(peak_deltas), 4),
            "human_perceptual_pass_count": sum(bool(item["human_perceptual_pass"]) for item in results),
        },
        "evidence_interpretation": {
            "renderer_induced_mandatory_normalization_supported": False,
            "default_join_smoothing_supported": False,
            "denoise_policy_supported": False,
            "reason": (
                "The three precommitted real joins already pass technical and human perceptual review, "
                "and the focal ORIGINAL/RENDERED measurements show only small observed loudness/true-peak deltas. "
                "This corpus therefore does not justify adding treatment by default."
            ),
        },
        "treatment_authorized": False,
        "auto_apply": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", required=True)
    parser.add_argument("--reviews-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    baseline = build_baseline(Path(args.bundle_root), Path(args.reviews_root))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"PHASE3_FOCAL_BASELINE_CASES={baseline['case_count']}")
    print(f"PHASE3_FOCAL_BASELINE_SOURCES={baseline['distinct_audio_sources']}")
    print(
        "PHASE3_FOCAL_BASELINE_MAX_ABS_LOUDNESS_DELTA_LU="
        f"{baseline['observed_summary']['max_abs_integrated_loudness_delta_lu']}"
    )
    print(
        "PHASE3_FOCAL_BASELINE_MAX_ABS_TRUE_PEAK_DELTA_DB="
        f"{baseline['observed_summary']['max_abs_true_peak_delta_db']}"
    )
    print("PHASE3_FOCAL_BASELINE_TREATMENT_AUTHORIZED=0")
    print("PHASE3_FOCAL_BASELINE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
