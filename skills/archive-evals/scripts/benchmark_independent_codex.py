from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


RUN_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "question_id": {"type": "string"},
        "answer": {"type": "string"},
        "support_status": {"type": "string"},
        "used_only_dr": {"type": "boolean"},
        "source_urls": {"type": "array", "items": {"type": "string"}},
        "persisted_artifacts": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "required": [
        "question_id",
        "answer",
        "support_status",
        "used_only_dr",
        "source_urls",
        "persisted_artifacts",
        "notes",
    ],
    "additionalProperties": False,
}


JUDGE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "question_id": {"type": "string"},
        "verdict": {"type": "string", "enum": ["pass", "partial", "fail"]},
        "used_only_allowed_sources": {"type": "boolean"},
        "must_hit_results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "point": {"type": "string"},
                    "status": {"type": "string", "enum": ["hit", "partial", "miss"]},
                    "reason": {"type": "string"},
                },
                "required": ["point", "status", "reason"],
                "additionalProperties": False,
            },
        },
        "reasoning_summary": {"type": "string"},
        "source_policy_notes": {"type": "string"},
    },
    "required": [
        "question_id",
        "verdict",
        "used_only_allowed_sources",
        "must_hit_results",
        "reasoning_summary",
        "source_policy_notes",
    ],
    "additionalProperties": False,
}


@dataclass
class BenchmarkQuestion:
    question_id: str
    question: str
    expected_answer: str
    must_hit_points: list[str]
    source_urls: list[str]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_schema_file(schema: dict, path: Path) -> None:
    path.write_text(json.dumps(schema, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def parse_benchmark_markdown(path: Path) -> list[BenchmarkQuestion]:
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n### ", text)[1:]
    questions: list[BenchmarkQuestion] = []
    for block in blocks:
        lines = block.splitlines()
        question_id = lines[0].strip()
        question = ""
        expected_answer_lines: list[str] = []
        must_hit_points: list[str] = []
        source_urls: list[str] = []
        mode: str | None = None
        for line in lines[1:]:
            if line.startswith("- Question: "):
                question = line[len("- Question: ") :].strip().strip("`")
                mode = None
            elif line.startswith("- Expected answer:"):
                mode = "expected"
                tail = line[len("- Expected answer:") :].strip()
                if tail:
                    expected_answer_lines.append(tail)
            elif line.startswith("- Must-hit points:"):
                mode = "must_hit"
            elif line.startswith("- DR source:") or line.startswith("- Source:"):
                mode = "sources"
            elif line.startswith("- ") and mode == "must_hit":
                must_hit_points.append(line[2:].strip())
            elif line.startswith("  - ") and mode == "must_hit":
                must_hit_points.append(line[4:].strip())
            elif line.startswith("  - [") and mode == "sources":
                match = re.search(r"\((https?://[^)]+)\)", line)
                if match:
                    source_urls.append(match.group(1))
            elif line.startswith("- [") and mode == "sources":
                match = re.search(r"\((https?://[^)]+)\)", line)
                if match:
                    source_urls.append(match.group(1))
            elif line.startswith("- ") and mode == "expected":
                expected_answer_lines.append(line[2:].strip())
            elif line.startswith("  ") and mode == "expected":
                expected_answer_lines.append(line.strip())
            elif line.strip() and mode == "expected":
                expected_answer_lines.append(line.strip())
            elif not line.strip():
                continue
        if question_id and question:
            questions.append(
                BenchmarkQuestion(
                    question_id=question_id,
                    question=question,
                    expected_answer=" ".join(expected_answer_lines).strip(),
                    must_hit_points=must_hit_points,
                    source_urls=source_urls,
                )
            )
    return questions


def load_answer(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def slug_hosts(urls: list[str]) -> list[str]:
    hosts = []
    for url in urls:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        hosts.append(host)
    return sorted(set(hosts))


def allowed_sources_from_benchmark(path: Path) -> list[str]:
    name = path.name.lower()
    if "dr-only" in name:
        return ["diariodarepublica.pt", "files.diariodarepublica.pt"]
    return []


def build_run_prompt(question: BenchmarkQuestion, allowed_hosts: list[str]) -> str:
    source_rule = (
        "Use only Diário da República sources."
        if allowed_hosts
        else "Use the benchmark's official source family only."
    )
    return textwrap.dedent(
        f"""\
        Cold independent Codex session.

        Answer one Portuguese legal question.
        Rules:
        - Use the local archive first.
        - If local support is weak, expand from canonical official sources.
        - {source_rule}
        - Keep tool use minimal. Do not run broad test suites.
        - Persist only the minimal reusable source-backed slice needed for the answer.
        - If you persist, rebuild only what is necessary.
        - Final output must satisfy the JSON schema.

        Question ID: {question.question_id}
        Question: {question.question}
        """
    )


def build_judge_prompt(question: BenchmarkQuestion, answer_payload: dict, allowed_hosts: list[str]) -> str:
    return textwrap.dedent(
        f"""\
        Judge one benchmark answer.

        Decide whether the candidate answer is pass, partial, or fail against the benchmark.

        Rules:
        - Use the expected answer and must-hit points as the grading contract.
        - Be strict about legal completeness and source-family discipline.
        - A pass should hit all material must-hit points with no material legal error.
        - Partial is for broadly right but missing a condition, scope limit, timing rule, or consequence.
        - Fail is for material legal error, unsupported invention, or wrong source family.
        - Treat these hosts as allowed sources: {", ".join(allowed_hosts) if allowed_hosts else "benchmark-declared official hosts"}.

        Question ID: {question.question_id}
        Question: {question.question}
        Expected answer: {question.expected_answer}
        Must-hit points:
        {json.dumps(question.must_hit_points, ensure_ascii=False)}
        Benchmark source URLs:
        {json.dumps(question.source_urls, ensure_ascii=False)}

        Candidate answer payload:
        {json.dumps(answer_payload, ensure_ascii=False)}
        """
    )


def run_codex(prompt: str, schema_path: Path, output_path: Path, workdir: Path, timeout_sec: int) -> tuple[int | None, str, str]:
    cmd = [
        "codex",
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--dangerously-bypass-approvals-and-sandbox",
        "--dangerously-bypass-hook-trust",
        "-C",
        str(workdir),
        "--output-schema",
        str(schema_path),
        "-o",
        str(output_path),
        prompt,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec, check=False)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        return None, exc.stdout or "", exc.stderr or ""


def run_question(
    repo_root: Path,
    archive_root: Path,
    question: BenchmarkQuestion,
    output_dir: Path,
    timeout_sec: int,
    allowed_hosts: list[str],
) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"{question.question_id}-", dir="/tmp") as tmpdir:
        tmp_root = Path(tmpdir) / archive_root.name
        shutil.copytree(archive_root, tmp_root, symlinks=True)
        schema_path = Path(tmpdir) / "run-schema.json"
        write_schema_file(RUN_SCHEMA, schema_path)
        output_path = output_dir / f"{question.question_id}.json"
        prompt = build_run_prompt(question, allowed_hosts)
        started_at = time.time()
        returncode, stdout, stderr = run_codex(prompt, schema_path, output_path, tmp_root, timeout_sec)
        elapsed = round(time.time() - started_at, 1)
        status = "ok" if returncode == 0 and output_path.exists() else "timeout" if returncode is None else "error"
        return {
            "question_id": question.question_id,
            "status": status,
            "returncode": returncode,
            "elapsed_sec": elapsed,
            "outfile_exists": output_path.exists(),
            "stdout_tail": stdout[-1000:],
            "stderr_tail": stderr[-1000:],
        }


def score_question(
    repo_root: Path,
    benchmark_path: Path,
    question: BenchmarkQuestion,
    answers_dir: Path,
    grades_dir: Path,
    timeout_sec: int,
    allowed_hosts: list[str],
) -> dict:
    answer_path = answers_dir / f"{question.question_id}.json"
    if not answer_path.exists():
        return {
            "question_id": question.question_id,
            "status": "missing_answer",
            "verdict": "fail",
            "used_only_allowed_sources": False,
        }
    answer_payload = load_answer(answer_path)
    with tempfile.TemporaryDirectory(prefix=f"judge-{question.question_id}-", dir="/tmp") as tmpdir:
        schema_path = Path(tmpdir) / "judge-schema.json"
        output_path = grades_dir / f"{question.question_id}.json"
        write_schema_file(JUDGE_SCHEMA, schema_path)
        prompt = build_judge_prompt(question, answer_payload, allowed_hosts)
        returncode, stdout, stderr = run_codex(prompt, schema_path, output_path, repo_root, timeout_sec)
        if returncode != 0 or not output_path.exists():
            return {
                "question_id": question.question_id,
                "status": "judge_failed" if returncode is not None else "judge_timeout",
                "verdict": "fail",
                "used_only_allowed_sources": False,
                "stdout_tail": stdout[-1000:],
                "stderr_tail": stderr[-1000:],
            }
        payload = load_answer(output_path)
        payload["status"] = "ok"
        return payload


def summarize_grades(benchmark_path: Path, questions: list[BenchmarkQuestion], answers_dir: Path, grades_dir: Path) -> dict:
    allowed_hosts = allowed_sources_from_benchmark(benchmark_path)
    rows = []
    verdict_counts = {"pass": 0, "partial": 0, "fail": 0}
    source_ok = 0
    for question in questions:
        answer_path = answers_dir / f"{question.question_id}.json"
        grade_path = grades_dir / f"{question.question_id}.json"
        answer_payload = load_answer(answer_path) if answer_path.exists() else None
        grade_payload = load_answer(grade_path) if grade_path.exists() else None
        if grade_payload:
            verdict = grade_payload["verdict"]
            verdict_counts[verdict] += 1
            if grade_payload.get("used_only_allowed_sources"):
                source_ok += 1
        row = {
            "question_id": question.question_id,
            "answer_present": answer_path.exists(),
            "grade_present": grade_path.exists(),
            "verdict": grade_payload.get("verdict") if grade_payload else "fail",
            "used_only_allowed_sources": grade_payload.get("used_only_allowed_sources", False) if grade_payload else False,
            "answer_support_status": answer_payload.get("support_status") if answer_payload else None,
            "answer_source_hosts": slug_hosts(answer_payload.get("source_urls", [])) if answer_payload else [],
        }
        rows.append(row)
    total = len(questions)
    return {
        "benchmark": benchmark_path.name,
        "question_count": total,
        "allowed_source_hosts": allowed_hosts,
        "verdict_counts": verdict_counts,
        "pass_rate": round(verdict_counts["pass"] / total, 4) if total else 0.0,
        "pass_or_partial_rate": round((verdict_counts["pass"] + verdict_counts["partial"]) / total, 4) if total else 0.0,
        "source_discipline_rate": round(source_ok / total, 4) if total else 0.0,
        "questions": rows,
    }


def write_summary_markdown(path: Path, summary: dict) -> None:
    lines = [
        f"# Independent Codex Benchmark Summary",
        "",
        f"- benchmark: `{summary['benchmark']}`",
        f"- questions: `{summary['question_count']}`",
        f"- pass: `{summary['verdict_counts']['pass']}`",
        f"- partial: `{summary['verdict_counts']['partial']}`",
        f"- fail: `{summary['verdict_counts']['fail']}`",
        f"- pass rate: `{summary['pass_rate']}`",
        f"- pass-or-partial rate: `{summary['pass_or_partial_rate']}`",
        f"- source discipline rate: `{summary['source_discipline_rate']}`",
        "",
        "## Per Question",
        "",
    ]
    for row in summary["questions"]:
        lines.append(f"### {row['question_id']}")
        lines.append("")
        lines.append(f"- verdict: `{row['verdict']}`")
        lines.append(f"- used_only_allowed_sources: `{row['used_only_allowed_sources']}`")
        if row["answer_support_status"]:
            lines.append(f"- support_status: `{row['answer_support_status']}`")
        if row["answer_source_hosts"]:
            lines.append(f"- source_hosts: `{', '.join(row['answer_source_hosts'])}`")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def command_run(args: argparse.Namespace) -> int:
    benchmark_path = Path(args.benchmark).resolve()
    archive_root = Path(args.archive_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    questions = parse_benchmark_markdown(benchmark_path)
    if args.filter:
        wanted = set(args.filter)
        questions = [q for q in questions if q.question_id in wanted]
    allowed_hosts = allowed_sources_from_benchmark(benchmark_path)
    results: list[dict] = []

    def worker(question: BenchmarkQuestion) -> dict:
        return run_question(Path.cwd(), archive_root, question, output_dir, args.timeout, allowed_hosts)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallelism) as executor:
        futures = {executor.submit(worker, question): question.question_id for question in questions}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            results = sorted(results, key=lambda row: row["question_id"])
            write_json(output_dir / "runner-status.json", results)
            print(json.dumps({"question_id": result["question_id"], "status": result["status"], "elapsed_sec": result["elapsed_sec"]}, ensure_ascii=False))
    return 0


def command_score(args: argparse.Namespace) -> int:
    benchmark_path = Path(args.benchmark).resolve()
    answers_dir = Path(args.answers_dir).resolve()
    grades_dir = Path(args.grades_dir).resolve()
    grades_dir.mkdir(parents=True, exist_ok=True)
    questions = parse_benchmark_markdown(benchmark_path)
    if args.filter:
        wanted = set(args.filter)
        questions = [q for q in questions if q.question_id in wanted]
    allowed_hosts = allowed_sources_from_benchmark(benchmark_path)
    for question in questions:
        grade = score_question(Path.cwd(), benchmark_path, question, answers_dir, grades_dir, args.timeout, allowed_hosts)
        if grade.get("status") == "ok":
            write_json(grades_dir / f"{question.question_id}.json", grade)
        else:
            write_json(grades_dir / f"{question.question_id}.json", grade)
            print(json.dumps({"question_id": question.question_id, "status": grade["status"]}, ensure_ascii=False), file=sys.stderr)
    summary = summarize_grades(benchmark_path, questions, answers_dir, grades_dir)
    write_json(grades_dir / "summary.json", summary)
    write_summary_markdown(grades_dir / "summary.md", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("benchmark")
    run_parser.add_argument("archive_root")
    run_parser.add_argument("output_dir")
    run_parser.add_argument("--timeout", type=int, default=240)
    run_parser.add_argument("--parallelism", type=int, default=3)
    run_parser.add_argument("--filter", nargs="*")
    run_parser.set_defaults(func=command_run)

    score_parser = subparsers.add_parser("score")
    score_parser.add_argument("benchmark")
    score_parser.add_argument("answers_dir")
    score_parser.add_argument("grades_dir")
    score_parser.add_argument("--timeout", type=int, default=180)
    score_parser.add_argument("--filter", nargs="*")
    score_parser.set_defaults(func=command_score)
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
