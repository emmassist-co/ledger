from __future__ import annotations

import json
import tempfile
from pathlib import Path


SUPPORT_RANK = {
    "derived_summary": 1,
    "extract": 2,
    "raw_source": 3,
}


def load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PyYAML is required for recipe-backed checks. Re-run with `uv run python scripts/run_archive_check.py ...`."
        ) from exc
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_source_freshness(root: Path) -> dict:
    path = root / "artifacts" / "state" / "source-freshness.json"
    if not path.exists():
        return {}
    return load_json_file(path)


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    _, _, remainder = text.partition("---\n")
    frontmatter, marker, _ = remainder.partition("\n---")
    if not marker:
        return {}
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PyYAML is required for recipe-backed checks. Re-run with `uv run python scripts/run_archive_check.py ...`."
        ) from exc
    return yaml.safe_load(frontmatter) or {}


def load_registry_meta(root: Path, artifact_id: str) -> dict:
    path = root / "artifacts" / "registry" / f"{artifact_id}.md"
    if not path.exists():
        return {}
    return parse_frontmatter(path.read_text(encoding="utf-8"))


def iter_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            rows.append(json.loads(stripped))
    return rows


def documents_by_id(root: Path) -> dict[str, dict]:
    return {row.get("artifact_id"): row for row in iter_jsonl(root / "index" / "documents.jsonl")}


def load_artifact_meta(root: Path, artifact_id: str) -> dict:
    artifact = documents_by_id(root).get(artifact_id, {})
    artifact_path = str(artifact.get("path", "")).strip()
    if not artifact_path:
        return {}
    path = Path(artifact_path)
    if not path.exists():
        return {}
    return parse_frontmatter(path.read_text(encoding="utf-8"))


def resolve_doc_id_from_role(root: Path, family_name: str, doc_role: str | None) -> str | None:
    if not doc_role:
        return None
    freshness = load_source_freshness(root).get("families", {}).get(family_name, {})
    mapping = {
        "newest_discovered": "newest_discovered_doc_id",
        "newest_temporary": "newest_temporary_doc_id",
        "newest_durable": "newest_durable_doc_id",
    }
    key = mapping.get(doc_role)
    if not key:
        return None
    value = freshness.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def tokenize(text: str) -> list[str]:
    token = []
    tokens = []
    for ch in text.lower():
        if ch.isalnum():
            token.append(ch)
        elif token:
            tokens.append("".join(token))
            token = []
    if token:
        tokens.append("".join(token))
    return tokens


def labels_for_entry(entry: dict) -> list[str]:
    labels = []
    for key in ("topic", "label"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            labels.append(value.strip())
    for key in ("labels", "match_terms", "artifact_ids"):
        value = entry.get(key)
        if isinstance(value, list):
            labels.extend(str(item).strip() for item in value if str(item).strip())
    return labels


def entry_matches_term(entry: dict, term: str) -> bool:
    if not term.strip():
        return False
    lowered_term = term.lower()
    term_tokens = set(tokenize(term))
    for label in labels_for_entry(entry):
        lowered_label = label.lower()
        if lowered_term in lowered_label or lowered_label in lowered_term:
            return True
        label_tokens = set(tokenize(label))
        if term_tokens and label_tokens and term_tokens <= label_tokens:
            return True
        if term_tokens and label_tokens and len(term_tokens & label_tokens) >= min(2, len(term_tokens)):
            return True
    return False


def infer_support_kind(claim: dict, archive_documents: dict[str, dict]) -> str | None:
    support_kind = claim.get("support_kind") or claim.get("support_type")
    if support_kind:
        return str(support_kind)
    evidence_ids = claim.get("evidence_ids", [])
    inferred = []
    for artifact_id in evidence_ids:
        artifact = archive_documents.get(artifact_id, {})
        artifact_type = artifact.get("artifact_type")
        if artifact_type == "extract":
            inferred.append("extract")
        elif artifact_type in {"raw_source", "source_document"}:
            inferred.append("raw_source")
        elif artifact_type:
            inferred.append("derived_summary")
    if "raw_source" in inferred:
        return "raw_source"
    if "extract" in inferred:
        return "extract"
    if "derived_summary" in inferred:
        return "derived_summary"
    return None


def normalize_question_shape_policies(raw_policies: object) -> dict[str, dict]:
    if isinstance(raw_policies, dict):
        return {
            str(name): value
            for name, value in raw_policies.items()
            if isinstance(name, str) and isinstance(value, dict)
        }
    if isinstance(raw_policies, list):
        return {
            row.get("name"): row
            for row in raw_policies
            if isinstance(row, dict) and row.get("name")
        }
    return {}


def check_support_hierarchy(root: Path, claims_payload: dict) -> dict:
    config = load_yaml(root / "recipes" / "support-hierarchy.yaml")
    failures = []
    checked = 0
    archive_documents = documents_by_id(root)
    minimum = config.get("decisive_claim_minimum", "extract")
    minimum_rank = SUPPORT_RANK.get(minimum, 2)
    require_label = bool(config.get("require_support_label_per_decisive_claim", True))
    for claim in claims_payload.get("claims", []):
        if not claim.get("decisive"):
            continue
        checked += 1
        support_type = infer_support_kind(claim, archive_documents)
        if require_label and not support_type:
            failures.append({"claim_id": claim.get("claim_id"), "reason": "missing support_type"})
            continue
        if support_type not in SUPPORT_RANK:
            failures.append({"claim_id": claim.get("claim_id"), "reason": f"unknown support_type: {support_type}"})
            continue
        if SUPPORT_RANK[support_type] < minimum_rank:
            failures.append(
                {"claim_id": claim.get("claim_id"), "reason": f"decisive claim requires at least {minimum}", "support_type": support_type}
            )
    if claims_payload.get("claims") and checked == 0:
        failures.append({"reason": "no decisive claims were supplied"})
    return {
        "ok": not failures,
        "check": "check_support_hierarchy",
        "summary": "decisive claims meet support hierarchy" if not failures else "decisive claims blocked by support hierarchy",
        "counts": {"claims_checked": checked, "failures": len(failures)},
        "failures": failures,
    }


def check_coverage_state(root: Path, term: str | None, task_type: str | None) -> dict:
    coverage = load_yaml(root / "domain" / "coverage-ledger.yaml")
    answer_contract = load_yaml(root / "recipes" / "answer-contract.yaml")
    normalized_term = (term or "").strip()
    matched_provisional = []
    for entry in coverage.get("provisional_weak_slices", []):
        if not isinstance(entry, dict):
            continue
        task_types = entry.get("task_types")
        if isinstance(task_types, list) and task_type and task_type not in {str(item) for item in task_types}:
            continue
        if entry_matches_term(entry, normalized_term):
            matched_provisional.append(entry)
    matched_partial = []
    for entry in coverage.get("partial_topics", []):
        if isinstance(entry, dict) and entry_matches_term(entry, normalized_term):
            matched_partial.append(entry)
    matched_gaps = []
    for entry in coverage.get("support_gaps", []):
        if not isinstance(entry, dict):
            continue
        task_types = entry.get("task_types")
        if isinstance(task_types, list) and task_type and task_type not in {str(item) for item in task_types}:
            continue
        if entry_matches_term(entry, normalized_term):
            matched_gaps.append(entry)
    support_targets = answer_contract.get("support_targets", {}) if isinstance(answer_contract, dict) else {}
    support_target = support_targets.get(task_type or "", support_targets.get("rule_lookup"))
    if matched_provisional or matched_partial or matched_gaps:
        failures = []
        status = "known_below_target"
        summary = "coverage ledger marks this topic below target quality"
        if matched_provisional and not matched_partial and not matched_gaps:
            status = "likely_below_target"
            summary = "coverage ledger records a provisional weak slice for this topic"
            failures.append({"reason": "matched provisional weak slice", "provisional_weak_slices": matched_provisional})
        elif matched_provisional:
            failures.append({"reason": "matched provisional weak slice", "provisional_weak_slices": matched_provisional})
        if matched_partial:
            failures.append({"reason": "matched partial topic", "topics": matched_partial})
        if matched_gaps:
            failures.append({"reason": "matched support gap", "gaps": matched_gaps})
        return {
            "ok": False,
            "check": "check_coverage_state",
            "summary": summary,
            "status": status,
            "counts": {
                "matched_provisional_weak_slices": len(matched_provisional),
                "matched_partial_topics": len(matched_partial),
                "matched_support_gaps": len(matched_gaps),
            },
            "support_target": support_target,
            "suggested_action": "expand",
            "can_answer_provisionally": True,
            "failures": failures,
        }
    return {
        "ok": True,
        "check": "check_coverage_state",
        "summary": "no matching partial topic or support gap in coverage ledger",
        "status": "clear",
        "counts": {
            "matched_provisional_weak_slices": 0,
            "matched_partial_topics": 0,
            "matched_support_gaps": 0,
        },
        "support_target": support_target,
        "failures": [],
    }


def check_source_freshness(
    root: Path,
    family_name: str | None,
    require_sync_ok: bool,
    required_doc_roles: list[str],
) -> dict:
    if not family_name:
        return {
            "ok": False,
            "check": "check_source_freshness",
            "summary": "source family is required",
            "failures": [{"reason": "provide --source-family"}],
        }
    freshness = load_source_freshness(root)
    families = freshness.get("families", {})
    family = families.get(family_name, {})
    if not family:
        return {
            "ok": False,
            "check": "check_source_freshness",
            "summary": "freshness state missing for source family",
            "failures": [{"reason": f"no freshness state for source family: {family_name}"}],
        }
    failures = []
    if require_sync_ok and family.get("last_sync_ok") is not True:
        failures.append({"reason": "last listing sync is not ok"})
    role_map = {
        "newest_discovered": "newest_discovered_doc_id",
        "newest_temporary": "newest_temporary_doc_id",
        "newest_durable": "newest_durable_doc_id",
    }
    resolved_roles = {}
    for role in required_doc_roles:
        key = role_map.get(role)
        value = family.get(key) if key else None
        if not key:
            failures.append({"reason": f"unsupported doc role: {role}"})
            continue
        resolved_roles[role] = value
        if not isinstance(value, str) or not value.strip():
            failures.append({"reason": f"missing freshness doc id for role: {role}"})
    return {
        "ok": not failures,
        "check": "check_source_freshness",
        "summary": "source freshness state is present and current enough" if not failures else "source freshness state is incomplete",
        "source_family": family_name,
        "family_state": family,
        "resolved_roles": resolved_roles,
        "failures": failures,
    }


def infer_currentness_status(artifact_meta: dict, family_state: dict) -> str:
    source_doc_id = str(artifact_meta.get("source_document_id") or artifact_meta.get("doc_id") or "").strip()
    newest_ids = [
        str(family_state.get("newest_discovered_doc_id", "")).strip(),
        str(family_state.get("newest_temporary_doc_id", "")).strip(),
        str(family_state.get("newest_durable_doc_id", "")).strip(),
    ]
    newest_ids = [value for value in newest_ids if value]
    if source_doc_id and newest_ids:
        if source_doc_id in newest_ids:
            return "current"
        return "superseded"
    return "unproven"


def build_currentness_bundle(
    root: Path,
    artifact_id: str | None,
    question_shape: str | None,
    source_family: str | None,
    status: str | None,
    reason: str | None,
    checked_at: str | None,
    canonical_source_url: str | None,
) -> dict:
    if not artifact_id:
        return {
            "ok": False,
            "check": "build_currentness_bundle",
            "summary": "artifact id is required",
            "failures": [{"reason": "provide --artifact-id"}],
        }
    artifact_meta = load_artifact_meta(root, artifact_id)
    if not artifact_meta:
        return {
            "ok": False,
            "check": "build_currentness_bundle",
            "summary": "artifact metadata is unavailable",
            "failures": [{"reason": f"artifact not found in archive index or file missing: {artifact_id}"}],
        }
    family_state = {}
    if source_family:
        family_state = load_source_freshness(root).get("families", {}).get(source_family, {})
    resolved_status = str(status or "").strip() or infer_currentness_status(artifact_meta, family_state)
    resolved_checked_at = (
        str(checked_at or "").strip()
        or str(family_state.get("last_listing_sync_at", "")).strip()
        or str(artifact_meta.get("verified_at", "")).strip()
    )
    resolved_url = (
        str(canonical_source_url or "").strip()
        or str(artifact_meta.get("source_url", "")).strip()
        or str(artifact_meta.get("raw_source_url", "")).strip()
    )
    resolved_reason = str(reason or "").strip()
    if not resolved_reason:
        if resolved_status == "current":
            if source_family and family_state:
                resolved_reason = f"artifact source document matches the latest freshness state for {source_family}"
            else:
                resolved_reason = "artifact metadata supports current status"
        elif resolved_status == "superseded":
            resolved_reason = "artifact source document does not match the latest source-family freshness state"
        elif resolved_status == "stale":
            resolved_reason = "freshness state indicates the relied-on slice is stale"
        else:
            resolved_reason = "currentness could not be proven from archive state alone"
    return {
        "ok": True,
        "check": "build_currentness_bundle",
        "summary": "currentness bundle built",
        "currentness": {
            "question_shape": str(question_shape or "").strip() or "rule_lookup",
            "status": resolved_status or "unproven",
            "checked_at": resolved_checked_at,
            "canonical_source_url": resolved_url,
            "relied_artifact_ids": [artifact_id],
            "reason": resolved_reason,
        },
        "failures": [],
    }


def check_source_registry_state(
    root: Path,
    family_name: str | None,
    doc_id: str | None,
    doc_role: str | None,
    expected_state: str | None,
    require_local_file: bool,
    require_page_index: bool,
    require_extracted_markdown: bool,
) -> dict:
    resolved_doc_id = doc_id or resolve_doc_id_from_role(root, family_name or "", doc_role)
    if not resolved_doc_id:
        return {
            "ok": False,
            "check": "check_source_registry_state",
            "summary": "document id could not be resolved",
            "failures": [{"reason": "provide --doc-id or a doc role with matching freshness state"}],
        }
    artifact_id = f"reg-{resolved_doc_id.lower()}"
    meta = load_registry_meta(root, artifact_id)
    if not meta:
        return {
            "ok": False,
            "check": "check_source_registry_state",
            "summary": "registry note missing for document",
            "failures": [{"reason": f"missing registry note: {artifact_id}"}],
        }
    failures = []
    actual_family = str(meta.get("source_family", "")).strip()
    if family_name and actual_family and actual_family != family_name:
        failures.append({"reason": f"registry source family mismatch: expected {family_name}, got {actual_family}"})
    actual_state = str(meta.get("discovery_state", "")).strip()
    if expected_state and actual_state != expected_state:
        failures.append({"reason": f"registry state mismatch: expected {expected_state}, got {actual_state}"})
    local_file = str(meta.get("temporary_local_file") or meta.get("local_file") or "").strip()
    if require_local_file:
        if not local_file:
            failures.append({"reason": "registry note missing local file pointer"})
        elif not Path(local_file).exists():
            failures.append({"reason": f"local file missing: {local_file}"})
    page_index_path = root / "source" / "index" / "pdf-pages" / f"{resolved_doc_id}.jsonl"
    if require_page_index and not page_index_path.exists():
        failures.append({"reason": f"page index missing: {page_index_path}"})
    extracted_md_path = root / "source" / "extracted" / f"{resolved_doc_id}.extracted.md"
    if require_extracted_markdown and not extracted_md_path.exists():
        failures.append({"reason": f"extracted markdown missing: {extracted_md_path}"})
    return {
        "ok": not failures,
        "check": "check_source_registry_state",
        "summary": "registry document state satisfies latest-source requirements" if not failures else "registry document state is incomplete",
        "source_family": family_name,
        "doc_id": resolved_doc_id,
        "doc_role": doc_role,
        "artifact_id": artifact_id,
        "registry_state": actual_state,
        "local_file": local_file,
        "page_index_path": str(page_index_path),
        "extracted_markdown_path": str(extracted_md_path),
        "failures": failures,
    }


def check_confirmation_boundary(root: Path, answer_payload: dict) -> dict:
    config = load_yaml(root / "recipes" / "confirmation-thresholds.yaml")
    failures = []
    level = answer_payload.get("conclusion_level")
    allowed = set(config.get("allowed_conclusion_levels", []))
    if level not in allowed:
        failures.append({"field": "conclusion_level", "reason": f"not allowed: {level}"})
    blocking_fact_ids = set(config.get("blocking_fact_ids", []))
    confirmed = set(answer_payload.get("blocking_facts_confirmed", []))
    missing = set(answer_payload.get("blocking_facts_missing", []))
    phrasing = str(answer_payload.get("phrasing", "")).lower()
    unresolved = blocking_fact_ids - confirmed
    if missing & confirmed:
        failures.append({"field": "blocking_facts", "reason": "same blocking fact marked confirmed and missing"})
    if level == "confirmed_from_provided_facts" and config.get("confirmed_requires_all_blocking_facts", True) and unresolved:
        failures.append(
            {
                "field": "conclusion_level",
                "reason": "confirmed conclusion requires all blocking facts confirmed",
                "unresolved_blocking_facts": sorted(unresolved),
            }
        )
    for phrase in [p.lower() for p in config.get("forbidden_phrases_when_blocking_facts_missing", [])]:
        if unresolved and phrase in phrasing:
            failures.append({"field": "phrasing", "reason": "forbidden phrase used while blocking facts remain unresolved", "phrase": phrase})
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


def check_currentness(root: Path, currentness_payload: dict) -> dict:
    config = load_yaml(root / "recipes" / "currentness-rules.yaml")
    failures = []
    question_shape = currentness_payload.get("question_shape")
    status = currentness_payload.get("status")
    reason = str(currentness_payload.get("reason", "")).strip()
    allowed_statuses = set(config.get("allowed_statuses", []))
    required_fields = ["status", *config.get("proof_bundle_fields", [])]
    for field in required_fields:
        value = currentness_payload.get(field)
        if not isinstance(value, str) or not value.strip():
            failures.append({"field": field, "reason": "missing required field"})
    current_shapes = set(config.get("current_question_shapes", []))
    if question_shape and current_shapes and question_shape not in current_shapes:
        failures.append({"field": "question_shape", "reason": f"not enabled for currentness: {question_shape}"})
    if status and status not in allowed_statuses:
        failures.append({"field": "status", "reason": f"not allowed: {status}"})
    blocking_status = config.get("block_decisive_current_answers_unless_status", "current")
    if status and status != blocking_status:
        failures.append({"field": "status", "reason": f"current-state answer blocked while status is {status}"})
    if status in {"stale", "superseded", "unproven"} and not reason:
        failures.append({"field": "reason", "reason": f"{status} status requires an explanation"})
    return {
        "ok": not failures,
        "check": "check_currentness",
        "summary": "currentness proof accepted" if not failures else "currentness proof blocked",
        "status": status,
        "question_shape": question_shape,
        "counts": {"failures": len(failures)},
        "failures": failures,
    }


def check_expansion_plan(root: Path, plan_payload: dict) -> dict:
    source_families = load_yaml(root / "recipes" / "source-families.yaml")
    acquisition = load_yaml(root / "recipes" / "source-acquisition.yaml")
    extract_units = load_yaml(root / "recipes" / "extract-units.yaml")
    answer_contract = load_yaml(root / "recipes" / "answer-contract.yaml")
    failures = []
    required = {
        "task_type",
        "question_shape",
        "source_family",
        "source_url",
        "unit_type",
        "materialize_as",
        "persistence_action",
        "search_stage",
        "query_terms",
        "reason",
    }
    for key in sorted(required - set(plan_payload)):
        failures.append({"field": key, "reason": "missing required field"})
    question_shape_policies = normalize_question_shape_policies(acquisition.get("question_shape_policies", []))
    allowed_families = {
        row.get("name")
        for row in source_families.get("source_families", [])
        if isinstance(row, dict) and row.get("name")
    }
    source_family = plan_payload.get("source_family")
    question_shape = plan_payload.get("question_shape")
    if source_family and source_family not in allowed_families:
        failures.append({"field": "source_family", "reason": f"not allowed: {source_family}"})
    if question_shape and question_shape not in question_shape_policies:
        failures.append({"field": "question_shape", "reason": f"unknown question shape: {question_shape}"})
    if source_family and source_family not in set(acquisition.get("allowed_source_families", [])):
        failures.append({"field": "source_family", "reason": "not present in source-acquisition recipe"})
    if question_shape and source_family and question_shape in question_shape_policies:
        allowed_for_shape = set(question_shape_policies[question_shape].get("allowed_source_families", []))
        if source_family not in allowed_for_shape:
            failures.append({"field": "source_family", "reason": f"not allowed for question_shape {question_shape}: {source_family}"})
    unit_map = {
        row.get("source_family"): row
        for row in extract_units.get("units", [])
        if isinstance(row, dict) and row.get("source_family")
    }
    unit_config = unit_map.get(source_family, {})
    if plan_payload.get("unit_type") and unit_config.get("retrieval_unit") and plan_payload["unit_type"] != unit_config["retrieval_unit"]:
        failures.append({"field": "unit_type", "reason": f"expected {unit_config['retrieval_unit']} for source_family {source_family}"})
    if plan_payload.get("materialize_as") and unit_config.get("materialize_as") and plan_payload["materialize_as"] != unit_config["materialize_as"]:
        failures.append({"field": "materialize_as", "reason": f"expected {unit_config['materialize_as']} for source_family {source_family}"})
    if answer_contract.get("exact_wording") in {"important", "critical"} and plan_payload.get("exact_wording_claim") and plan_payload.get("materialize_as") != "extract":
        failures.append({"field": "materialize_as", "reason": "exact wording claims require extract materialization under this domain pack"})
    if plan_payload.get("task_type") == "case_application" and not plan_payload.get("facts_status"):
        failures.append({"field": "facts_status", "reason": "required for case_application"})
    if plan_payload.get("persistence_action") not in {"persist", "skip_persist"}:
        failures.append({"field": "persistence_action", "reason": "must be persist or skip_persist"})
    if plan_payload.get("persistence_action") == "skip_persist":
        skip_reason = plan_payload.get("skip_reason")
        if not skip_reason:
            failures.append({"field": "skip_reason", "reason": "required when persistence_action is skip_persist"})
        elif skip_reason not in set(acquisition.get("skip_persist_reasons", [])):
            failures.append({"field": "skip_reason", "reason": f"not allowed: {skip_reason}"})
    search_stage = plan_payload.get("search_stage")
    if search_stage not in {"initial", "refinement"}:
        failures.append({"field": "search_stage", "reason": "must be initial or refinement"})
    query_terms = plan_payload.get("query_terms")
    if not isinstance(query_terms, list) or not query_terms or not all(isinstance(term, str) and term.strip() for term in query_terms):
        failures.append({"field": "query_terms", "reason": "must be a non-empty list of strings"})
    if question_shape in question_shape_policies and isinstance(query_terms, list):
        bounded_search = question_shape_policies[question_shape].get("bounded_search", {})
        initial_budget = bounded_search.get("initial_query_budget")
        refinement_budget = bounded_search.get("refinement_query_budget")
        if search_stage == "initial" and isinstance(initial_budget, int) and len(query_terms) > initial_budget:
            failures.append({"field": "query_terms", "reason": f"initial search exceeds budget for question_shape {question_shape}"})
        if search_stage == "refinement":
            if bounded_search.get("allow_second_stage_refinement") is not True:
                failures.append({"field": "search_stage", "reason": f"refinement not allowed for question_shape {question_shape}"})
            if isinstance(refinement_budget, int) and len(query_terms) > refinement_budget:
                failures.append({"field": "query_terms", "reason": f"refinement search exceeds budget for question_shape {question_shape}"})
    return {
        "ok": not failures,
        "check": "check_expansion_plan",
        "summary": "expansion plan accepted" if not failures else "expansion plan blocked",
        "counts": {"failures": len(failures)},
        "failures": failures,
    }


def write_temp_payload(payload_text: str, prefix: str) -> str:
    data = json.loads(payload_text)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", prefix=prefix, delete=False)
    with handle as fh:
        json.dump(data, fh, ensure_ascii=True, indent=2)
        fh.write("\n")
    return handle.name
