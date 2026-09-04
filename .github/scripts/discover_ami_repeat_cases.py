from __future__ import annotations

import argparse
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

NITE_NS = "http://nite.sourceforge.net/"
NITE_ID = f"{{{NITE_NS}}}id"
REPEAT_TYPE = "ami_dsfl_12"
REPARANS_TYPE = "ami_dsfl_18"
REPARANDUM_TYPE = "ami_dsfl_19"
_ID_RE = re.compile(r"id\(([^)]+)\)")
_WORD_NUM_RE = re.compile(r"^(.*?\.words)(\d+)$")
_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _normalise(text: str) -> str:
    """Mirror production word normalisation: punctuation is removed, not token-split."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    tokens: list[str] = []
    for raw in asciiish.split():
        token = _TOKEN_RE.sub("", raw)
        if token:
            tokens.append(token)
    return " ".join(tokens)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _direct_type(element: ET.Element) -> str | None:
    for child in list(element):
        if _local_name(child.tag) != "pointer" or child.attrib.get("role") != "dsfl-type":
            continue
        href = child.attrib.get("href", "")
        match = re.search(r"id\((ami_dsfl_\d+)\)", href)
        if match:
            return match.group(1)
    return None


def _expand_child_href(href: str) -> list[str]:
    ids = _ID_RE.findall(href)
    if not ids:
        return []
    if len(ids) == 1:
        return [ids[0]]
    first, last = ids[0], ids[-1]
    first_match = _WORD_NUM_RE.match(first)
    last_match = _WORD_NUM_RE.match(last)
    if not first_match or not last_match or first_match.group(1) != last_match.group(1):
        raise ValueError(f"Unsupported AMI word range: {href}")
    start = int(first_match.group(2))
    end = int(last_match.group(2))
    if end < start:
        raise ValueError(f"Reverse AMI word range: {href}")
    prefix = first_match.group(1)
    return [f"{prefix}{index}" for index in range(start, end + 1)]


def _direct_word_ids(element: ET.Element) -> list[str]:
    result: list[str] = []
    for child in list(element):
        if _local_name(child.tag) == "child":
            result.extend(_expand_child_href(child.attrib.get("href", "")))
    return result


def _load_words(path: Path) -> dict[str, dict[str, Any]]:
    root = ET.parse(path).getroot()
    words: dict[str, dict[str, Any]] = {}
    for element in root.iter():
        word_id = element.attrib.get(NITE_ID)
        if not word_id or ".words" not in word_id:
            continue
        text = " ".join("".join(element.itertext()).split())
        start_raw = element.attrib.get("starttime")
        end_raw = element.attrib.get("endtime")
        try:
            start = float(start_raw) if start_raw is not None else None
            end = float(end_raw) if end_raw is not None else None
        except ValueError:
            start = None
            end = None
        words[word_id] = {"text": text, "start": start, "end": end}
    return words


def _span_from_ids(word_ids: Iterable[str], words: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    items = [words.get(word_id) for word_id in word_ids]
    if not items or any(item is None for item in items):
        return None
    lexical = [item for item in items if item and _normalise(str(item["text"]))]
    if not lexical:
        return None
    starts = [float(item["start"]) for item in lexical if item["start"] is not None]
    ends = [float(item["end"]) for item in lexical if item["end"] is not None]
    if not starts or not ends:
        return None
    text = " ".join(str(item["text"]).strip() for item in lexical if str(item["text"]).strip())
    normalised = _normalise(text)
    return {
        "text": text,
        "normalised": normalised,
        "token_count": len(normalised.split()),
        "start": min(starts),
        "end": max(ends),
    }


def load_speaker_channels(meetings_xml: Path) -> dict[tuple[str, str], int]:
    root = ET.parse(meetings_xml).getroot()
    mapping: dict[tuple[str, str], int] = {}
    for meeting in root.iter():
        if _local_name(meeting.tag) != "meeting":
            continue
        observation = meeting.attrib.get("observation")
        if not observation:
            continue
        for speaker in list(meeting):
            if _local_name(speaker.tag) != "speaker":
                continue
            agent = speaker.attrib.get("nxt_agent")
            channel = speaker.attrib.get("channel")
            if not agent or channel is None:
                continue
            try:
                mapping[(observation, agent)] = int(channel)
            except ValueError:
                continue
    return mapping


def discover_cases(corpus_root: Path, *, min_tokens: int = 3) -> list[dict[str, Any]]:
    disfluency_dir = corpus_root / "disfluency"
    words_dir = corpus_root / "words"
    meetings_xml = corpus_root / "corpusResources" / "meetings.xml"
    if not disfluency_dir.is_dir() or not words_dir.is_dir() or not meetings_xml.is_file():
        raise FileNotFoundError(f"Incomplete AMI corpus root: {corpus_root}")

    channels = load_speaker_channels(meetings_xml)
    discovered: list[dict[str, Any]] = []
    words_cache: dict[Path, dict[str, dict[str, Any]]] = {}

    for disfluency_path in sorted(disfluency_dir.glob("*.disfluency.xml")):
        stem = disfluency_path.name.removesuffix(".disfluency.xml")
        if "." not in stem:
            continue
        meeting, speaker = stem.rsplit(".", 1)
        channel = channels.get((meeting, speaker))
        if channel is None:
            continue
        words_path = words_dir / f"{meeting}.{speaker}.words.xml"
        if not words_path.is_file():
            continue
        if words_path not in words_cache:
            words_cache[words_path] = _load_words(words_path)
        words = words_cache[words_path]

        root = ET.parse(disfluency_path).getroot()
        for parent in list(root):
            if _local_name(parent.tag) != "dsfl" or _direct_type(parent) != REPEAT_TYPE:
                continue
            reparandum = next(
                (child for child in list(parent) if _local_name(child.tag) == "dsfl" and _direct_type(child) == REPARANDUM_TYPE),
                None,
            )
            reparans = next(
                (child for child in list(parent) if _local_name(child.tag) == "dsfl" and _direct_type(child) == REPARANS_TYPE),
                None,
            )
            if reparandum is None or reparans is None:
                continue
            reparandum_ids = _direct_word_ids(reparandum)
            reparans_ids = _direct_word_ids(reparans)
            reparandum_span = _span_from_ids(reparandum_ids, words)
            reparans_span = _span_from_ids(reparans_ids, words)
            if reparandum_span is None or reparans_span is None:
                continue
            if reparandum_span["normalised"] != reparans_span["normalised"]:
                continue
            if int(reparandum_span["token_count"]) < min_tokens:
                continue
            if float(reparans_span["start"]) < float(reparandum_span["start"]):
                continue

            parent_id = parent.attrib.get(NITE_ID, "")
            reparandum_id = reparandum.attrib.get(NITE_ID, "")
            reparans_id = reparans.attrib.get(NITE_ID, "")
            clip_start = max(0.0, float(reparandum_span["start"]) - 4.0)
            clip_end = float(reparans_span["end"]) + 4.0
            parent_suffix = parent_id.rsplit(".", 1)[-1] if parent_id else str(len(discovered) + 1)
            discovered.append(
                {
                    "id": f"ami-{meeting.lower()}-{speaker.lower()}-repeat-{parent_suffix}",
                    "meeting": meeting,
                    "speaker": speaker,
                    "channel": channel,
                    "audio_source_id": f"{meeting}-{speaker}",
                    "human_label": "removable_reparandum",
                    "annotation_type": "repeat",
                    "annotation_parent_id": parent_id,
                    "reparandum_annotation_id": reparandum_id,
                    "reparans_annotation_id": reparans_id,
                    "reparandum_word_ids": reparandum_ids,
                    "reparans_word_ids": reparans_ids,
                    "reparandum_text": reparandum_span["text"],
                    "reparans_text": reparans_span["text"],
                    "reparandum_start": round(float(reparandum_span["start"]), 3),
                    "reparandum_end": round(float(reparandum_span["end"]), 3),
                    "reparans_start": round(float(reparans_span["start"]), 3),
                    "reparans_end": round(float(reparans_span["end"]), 3),
                    "token_count": int(reparandum_span["token_count"]),
                    "clip_start": round(clip_start, 3),
                    "clip_duration": round(max(5.0, clip_end - clip_start), 3),
                    "detector_expectation": "long_detector_compatible",
                    "expected_candidate_kind": "possible_repetition",
                }
            )
    return discovered


def select_cases(
    cases: list[dict[str, Any]],
    *,
    max_cases: int = 8,
    max_sources: int = 4,
    max_per_source: int = 2,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[str(case["audio_source_id"])].append(case)
    for values in grouped.values():
        values.sort(key=lambda item: (-int(item["token_count"]), float(item["clip_duration"]), item["id"]))
    ranked_sources = sorted(
        grouped,
        key=lambda key: (
            -len(grouped[key]),
            -max(int(item["token_count"]) for item in grouped[key]),
            key,
        ),
    )[:max_sources]
    selected: list[dict[str, Any]] = []
    cursor = 0
    while len(selected) < max_cases:
        added = False
        for source in ranked_sources:
            values = grouped[source]
            if cursor < len(values) and cursor < max_per_source:
                selected.append(values[cursor])
                added = True
                if len(selected) >= max_cases:
                    break
        if not added:
            break
        cursor += 1
    return selected


def build_selection_payload(cases: list[dict[str, Any]], selected: list[dict[str, Any]]) -> dict[str, Any]:
    sources: dict[str, dict[str, Any]] = {}
    for case in selected:
        source_id = str(case["audio_source_id"])
        if source_id not in sources:
            meeting = str(case["meeting"])
            speaker = str(case["speaker"])
            channel = int(case["channel"])
            audio = f"{meeting}.Headset-{channel}.wav"
            sources[source_id] = {
                "meeting": meeting,
                "speaker": speaker,
                "channel": channel,
                "source_kind": "individual_headset",
                "audio": audio,
                "url": f"https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/{meeting}/audio/{audio}",
            }
    return {
        "schema_version": 1,
        "discovered_exact_repeat_cases": len(cases),
        "selected_cases": len(selected),
        "selected_sources": len(sources),
        "audio_sources": sources,
        "cases": selected,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover exact AMI repeat reparandum/reparans positives for Video_Tunner 2D.6.")
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--min-tokens", type=int, default=3)
    parser.add_argument("--max-cases", type=int, default=8)
    parser.add_argument("--max-sources", type=int, default=4)
    parser.add_argument("--max-per-source", type=int, default=2)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = discover_cases(args.corpus_root, min_tokens=args.min_tokens)
    selected = select_cases(
        cases,
        max_cases=args.max_cases,
        max_sources=args.max_sources,
        max_per_source=args.max_per_source,
    )
    payload = build_selection_payload(cases, selected)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    compact = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    print(f"AMI_REPEAT_DISCOVERY_TOTAL={len(cases)}")
    print(f"AMI_REPEAT_DISCOVERY_SELECTED={len(selected)}")
    print(f"AMI_REPEAT_DISCOVERY_SOURCES={len(payload['audio_sources'])}")
    for case in selected:
        print(
            "AMI_REPEAT_DISCOVERY_CASE="
            f"{case['id']}|{case['meeting']}|{case['speaker']}|{case['channel']}|"
            f"tokens={case['token_count']}|{case['reparandum_text']}"
        )
    print(f"AMI_REPEAT_DISCOVERY_SUMMARY={compact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
