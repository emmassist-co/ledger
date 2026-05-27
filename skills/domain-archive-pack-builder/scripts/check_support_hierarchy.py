from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


SUPPORT_RANK = {
    "derived_summary": 1,
    "extract": 2,
    "raw_source": 3,
}


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0 if payload.get("ok") else 1


def validate_claims(root: Path, payload: dict) -> dict:
    config = load_yaml(root / "recipes" / "support-hierarchy.yaml")
    failures = []
    checked = 0

    minimum = config.get("decisive_claim_minimum", "extract")
    minimum_rank = SUPPORT_RANK.get(minimum, 2)
    require_label = bool(config.get("require_support_label_per_decisive_claim", True))

    for claim in payload.get("claims", []):
        if not claim.get("decisive"):
            continue
        checked += 1
        support_type = claim.get("support_type")
        if require_label and not support_type:
            failures.append({"claim_id": claim.get("claim_id"), "reason": "missing support_type"})
            continue
        if support_type not in SUPPORT_RANK:
            failures.append({"claim_id": claim.get("claim_id"), "reason": f"unknown support_type: {support_type}"})
            continue
        if SUPPORT_RANK[support_type] < minimum_rank:
            failures.append(
                {
                    "claim_id": claim.get("claim_id"),
                    "reason": f"decisive claim requires at least {minimum}",
                    "support_type": support_type,
                }
            )
    return {
        "ok": not failures,
        "check": "check_support_hierarchy",
        "summary": "decisive claims meet support hierarchy" if not failures else "decisive claims blocked by support hierarchy",
        "counts": {"claims_checked": checked, "failures": len(failures)},
        "failures": failures,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive_root")
    parser.add_argument("--claims-json", required=True)
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    root = Path(args.archive_root).resolve()
    payload = load_json(Path(args.claims_json).resolve())
    return emit(validate_claims(root, payload))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
