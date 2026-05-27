from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload.get("ok") else 1


def validate_answer(root: Path, payload: dict) -> dict:
    config = load_yaml(root / "recipes" / "confirmation-thresholds.yaml")
    failures = []

    level = payload.get("conclusion_level")
    allowed = set(config.get("allowed_conclusion_levels", []))
    if level not in allowed:
        failures.append({"field": "conclusion_level", "reason": f"not allowed: {level}"})

    blocking_fact_ids = set(config.get("blocking_fact_ids", []))
    confirmed = set(payload.get("blocking_facts_confirmed", []))
    missing = set(payload.get("blocking_facts_missing", []))
    phrasing = str(payload.get("phrasing", "")).lower()

    if missing & confirmed:
        failures.append({"field": "blocking_facts", "reason": "same blocking fact marked confirmed and missing"})

    unresolved = blocking_fact_ids - confirmed
    if level == "confirmed_from_provided_facts" and config.get("confirmed_requires_all_blocking_facts", True) and unresolved:
        failures.append(
            {
                "field": "conclusion_level",
                "reason": "confirmed conclusion requires all blocking facts confirmed",
                "unresolved_blocking_facts": sorted(unresolved),
            }
        )

    forbidden_phrases = [phrase.lower() for phrase in config.get("forbidden_phrases_when_blocking_facts_missing", [])]
    if unresolved:
        for phrase in forbidden_phrases:
            if phrase in phrasing:
                failures.append(
                    {
                        "field": "phrasing",
                        "reason": "forbidden phrase used while blocking facts remain unresolved",
                        "phrase": phrase,
                    }
                )

    return {
        "ok": not failures,
        "check": "check_confirmation_boundary",
        "summary": "answer stays within confirmation boundary" if not failures else "answer overclaims beyond confirmation boundary",
        "counts": {
            "blocking_facts_configured": len(blocking_fact_ids),
            "blocking_facts_confirmed": len(confirmed),
            "blocking_facts_missing": len(missing),
            "failures": len(failures),
        },
        "failures": failures,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive_root")
    parser.add_argument("--answer-json", required=True)
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    root = Path(args.archive_root).resolve()
    payload = load_json(Path(args.answer_json).resolve())
    return emit(validate_answer(root, payload))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
