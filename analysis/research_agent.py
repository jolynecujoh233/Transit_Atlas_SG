"""Single-model research agent: question -> reviewed proposal -> approved recalculation.

Live planning uses the authenticated Codex CLI or OpenAI Responses API.
For local verification, --plan-file reads an already structured plan and
exercises the same validation, scoring, and comparison path without an API.
Only the question and indicator metadata are sent to the model, never grid rows.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from run_scenario import REGISTRY, ROOT, sha256, source_path
from render_agent_report import render


BASELINE_CONFIG = ROOT / "config/scenarios/baseline_v1.json"
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "decision": {"type": "string", "enum": ["run", "needs_data"]},
        "research_question": {"type": "string"},
        "approach_summary": {"type": "string"},
        "rationale": {"type": "string"},
        "demand_changes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"indicator_id": {"type": "string"},
                           "weight": {"type": "number"},
                           "reason": {"type": "string"}},
            "required": ["indicator_id", "weight", "reason"]}},
        "supply_changes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"indicator_id": {"type": "string"},
                           "weight": {"type": "number"},
                           "reason": {"type": "string"}},
            "required": ["indicator_id", "weight", "reason"]}},
        "use_registered_indicators": {"type": "array", "items": {"type": "string"}},
        "data_needed": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["decision", "research_question", "approach_summary", "rationale", "demand_changes",
                 "supply_changes", "use_registered_indicators", "data_needed", "limitations"],
}

DEMAND_DESCRIPTIONS = {
    "n_low_income_households_lt3000": "2020 low-income resident households, estimated grid count",
    "n_non_car_commuters": "2020 employed residents commuting without car-only mode, estimated grid count",
    "n_unemployed_residents": "2020 unemployed residents, estimated grid count",
    "n_low_education_residents_15plus": "2020 residents 15+ with low qualifications, estimated grid count",
    "n_youth_residents_10_19": "2020 residents aged 10-19, estimated grid count",
    "n_older_residents_65plus": "2020 residents aged 65+, estimated grid count",
    "n_one_person_households": "2020 one-person resident households, estimated grid count",
    "n_mobility_difficulty_residents_5plus": "2020 residents 5+ with mobility difficulty, estimated grid count",
    "n_public_transit_users_work_school_sum": "2020 public transit users for work/school, estimated grid count",
}
PUBLIC_DATA_GUIDANCE = """你是新加坡公共交通供需缺口研究助手。先读研究问题，再查指标目录。明确研究对象、时段、空间尺度，以及需求和供给分别要量什么。

逐项核对已有指标的字段、粒度和覆盖范围。能复用的就复用；核心条件没有覆盖的，主动把对应的新数据列入建议清单。优先查公开、可追溯的数据；区分可直接下载、需注册或申请、尚未核实。不能把待查数据当作已取得。

每项补充建议写清需要哪些字段、用来计算什么。按回答原问题的重要性排序。先列公开汇总数据可支持的最小初筛组合，再列验证真实结果所需的精细资料。除非用户明确只接受实测或逐班次结果，不要把受限微观数据列为开展初筛的前提。已有数据足够时不必添加新数据。

同时说明现有数据可以先回答哪个较窄的问题，写清代理指标的含义和局限。涉及更换时段、研究人群或测量对象时，把替代方案交给用户审核，保留原问题和它的数据需求。"""

PLANNER_RULES = PUBLIC_DATA_GUIDANCE + "\n" + (
    "遇到可达性问题，先核对已有指标的出行方式、时段和阈值。需要新口径时，可提出用点目的地计算"
    "步行或工作日09:00步行加公共交通的1–60分钟累计或时间衰减可达性，写明待选源数据和参数；"
    "只有处理完成并注册后才能配置权重。周末班表和任意新算法仍须单独核实。\n"
    "研究范围为新加坡1,597个估计人口为正的400米网格。research_question 保留用户关心的核心条件；在 rationale 中说明研究思路、"
    "现有指标可做的初筛和需要确认的假设。文献和旧提案提供背景，以用户本轮问题为准。\n"
    "approach_summary 是展示给研究者的研究思路，用一至两句中文、最多120字。点名需求看哪个量、供给看哪个量，"
    "说明如何在同一空间或时间口径下比较，以及怎样识别缺口。比较方法须与本份提案一致。"
    "若做初筛，写清所用代理；待补数据用拟开展的语气。省略背景、字段列表和结果，避免复述问题。\n"
    "原问题缺少关键输入时，decision 填 needs_data，并把具体建议写入 data_needed，不能只写在 limitations。"
    "若当前目录已能支持本轮问题，或用户已同意较窄的代理方案，则填 run；有实质价值的可选补充仍可列入 data_needed，注明可跳过。\n"
    "只有目录中的指标能进入本轮权重配置；尚待获取的数据只作为建议。默认权重为1，通常只列需调整的项，权重范围0.25–3。"
    "基线指标归入对应的 demand_changes 或 supply_changes；use_registered_indicators 只填实际选用的 registered=true 指标。"
    "对本轮指定必须纳入的已注册指标逐项说明权重及理由，即使权重为1。\n"
    "需求计数表示需求规模，预计到站是频次代理。不要虚构字段、来源、计算结果或因果关系。"
)


def locate_codex() -> str | None:
    explicit = os.environ.get("CODEX_CLI_PATH")
    if explicit:
        path = Path(explicit)
        return str(path) if path.is_file() else None
    on_path = shutil.which("codex")
    if on_path:
        return on_path
    local_app_data = Path(os.environ.get(
        "LOCALAPPDATA", str(Path.home() / "AppData/Local")))
    candidates = sorted((local_app_data / "OpenAI/Codex/bin").glob("*/codex.exe"),
                        key=lambda path: path.stat().st_mtime, reverse=True)
    return str(candidates[0]) if candidates else None


def catalog() -> tuple[dict, dict]:
    baseline = json.loads(BASELINE_CONFIG.read_text(encoding="utf-8"))
    supply_dictionary = json.loads((ROOT /
        "output/supply/supply_indicator_dictionary.json").read_text(encoding="utf-8"))
    entries = {}
    for field in baseline["demand"]["weights"]:
        entries[field] = {"side": "demand", "field": field,
                          "description": DEMAND_DESCRIPTIONS[field],
                          "registered": False}
    for item in supply_dictionary["indicators"]:
        entries[item["id"]] = {"side": "supply", "field": item["output_field"],
            "description": item["method"], "unit": item["unit"],
            "factor": item["factor"], "registered": False}
    if REGISTRY.exists():
        for path in sorted(REGISTRY.glob("*.json")):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            indicator_id = manifest["id"]
            if path.stem != indicator_id or indicator_id in entries:
                raise ValueError(f"Invalid registered indicator: {path}")
            source = source_path(manifest["source_csv"])
            if sha256(source) != manifest["source_sha256"]:
                raise ValueError(f"Registered indicator source changed: {indicator_id}")
            entries[indicator_id] = {"side": manifest["side"],
                "field": manifest["field"], "description": manifest["description"],
                "unit": manifest["unit"], "source_year": manifest["source_year"],
                "source": manifest["source"], "method": manifest["method"],
                "registered": True}
    return entries, baseline


def request_plan(question: str, entries: dict, model: str) -> dict:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set; live model planning cannot run")
    payload = {
        "model": model, "store": False, "parallel_tool_calls": False,
        "instructions": PLANNER_RULES + " Return one submit_research_plan call.",
        "input": json.dumps({"question": question, "indicator_catalog": entries},
                            ensure_ascii=False),
        "tools": [{"type": "function", "name": "submit_research_plan",
                   "description": "Submit a bounded research scenario plan for local validation.",
                   "strict": True, "parameters": SCHEMA}],
        "tool_choice": {"type": "function", "name": "submit_research_plan"},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(1000).decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API returned HTTP {exc.code}: {detail}") from exc
    if body.get("status") != "completed":
        raise RuntimeError(f"Model response did not complete: {body.get('status')}")
    calls = [item for item in body.get("output", [])
             if item.get("type") == "function_call" and
             item.get("name") == "submit_research_plan"]
    if len(calls) != 1:
        raise RuntimeError("Expected exactly one structured research plan call")
    return json.loads(calls[0]["arguments"])


def codex_json(prompt: str, schema: dict, model: str | None, *, web_search: bool = False) -> dict:
    executable = locate_codex()
    if not executable:
        raise RuntimeError("Codex CLI is not installed")
    (ROOT / "tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="research_plan_", dir=ROOT / "tmp") as temp:
        folder = Path(temp).resolve()
        if not folder.is_relative_to(ROOT / "tmp"):
            raise RuntimeError("Unsafe model output directory")
        schema_path = folder / "schema.json"
        answer_path = folder / "answer.json"
        schema_path.write_text(json.dumps(schema, ensure_ascii=False),
                               encoding="utf-8")
        command = [executable, "exec", "--skip-git-repo-check", "--ephemeral",
                   "--sandbox", "read-only", "-C", str(ROOT / "tmp"),
                   "-c", "model_reasoning_effort=low",
                   "--output-schema", str(schema_path),
                   "--output-last-message", str(answer_path)]
        if web_search:
            command.insert(1, "--search")
            command.append("--json")
        if model:
            command.extend(["--model", model])
        command.append("-")
        environment = os.environ.copy()
        environment.setdefault("CODEX_HOME", str(Path.home() / ".codex"))
        completed = subprocess.run(command, input=prompt, cwd=ROOT / "tmp",
                                   text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=300,
                                   check=False, env=environment)
        if completed.returncode or not answer_path.is_file():
            raise RuntimeError("Codex CLI planning failed: " + completed.stderr[-1200:])
        if web_search:
            events = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
            if not any(event.get("item", {}).get("type") == "web_search" for event in events):
                raise RuntimeError("No web search recorded; supply verified notes with --evidence-file")
        return json.loads(answer_path.read_text(encoding="utf-8"))


def lookup_evidence(question: str, model: str | None, *, datasets: bool = False) -> str:
    fields = ("title", "url", "finding", "limitation")
    study = {"type": "object", "additionalProperties": False,
             "properties": {key: {"type": "string"} for key in fields},
             "required": list(fields)}
    schema = {"type": "object", "additionalProperties": False,
              "properties": {"sources": {"type": "array", "items": study}},
              "required": ["sources"]}
    prompt = ("Use live web search and inspect primary sources for this Singapore public "
              "transport question. Return up to three directly relevant studies. Give the "
              "actual source URL, title, a concise evidence statement and a limitation "
              "in Chinese. Explain transferability to Singapore. Exclude unverified "
              "sources. Do not propose weights. Use only web search. Research question: "
              + json.dumps(question, ensure_ascii=False))
    if not datasets:
        schema["properties"]["synthesis"] = {"type": "string"}
        schema["required"].append("synthesis")
        prompt += ("\nIn synthesis give two short Chinese sentences integrating these studies' "
                   "findings and their limits for this question. Attribute claims by study title "
                   "or author and do not infer numerical weights. Prefer relevant studies that "
                   "explain or validate indicators reproducible with public data. Distinguish "
                   "a study's restricted validation inputs from inputs needed for preliminary screening.")
    if datasets:
        prompt = PUBLIC_DATA_GUIDANCE + "\n" + ("Search live for primary publisher pages of Singapore datasets that could "
                  "fill these data gaps. Search by the missing fields and resolution across "
                  "publisher portals, including LTA DataMall and data.gov.sg when relevant. "
                  "Check whether day type, time fields and spatial IDs can actually be combined. "
                  "Distinguish an observed time series from a timetable or a monthly aggregate. "
                  "Only include URLs you inspected. Explain in Chinese "
                  "the actual fields, time and spatial scale and what still needs checking. "
                  "Return an empty sources array if none could be found. Data gaps: "
                  + json.dumps(question, ensure_ascii=False))
    result = codex_json(prompt, schema, model, web_search=True)
    sources = result.get("sources", [])
    if not sources:
        if datasets:
            return "## 待补数据来源\n\n暂未找到可核实的数据集页面。"
        raise RuntimeError("No relevant primary source found; supply reviewed literature notes")
    notes = ["## 待补数据来源" if datasets else "# 文献检索记录", ""]
    for item in sources:
        if not all(isinstance(item.get(k), str) and item[k].strip() for k in fields):
            raise ValueError("Incomplete literature record")
        if not re.fullmatch(r"https?://[^\s]+", item["url"]):
            raise ValueError("Invalid literature URL")
        notes.extend([item["title"], item["url"], item["finding"], item["limitation"], ""])
    if not datasets and result.get("synthesis", "").strip():
        notes.extend(["## 文献综合", "", result["synthesis"].strip(), ""])
    return "\n".join(notes)


def request_plan_codex(question: str, entries: dict, model: str | None) -> dict:
    prompt = (PLANNER_RULES + "\nProduce only a JSON object matching the supplied output schema. "
              "Do not call tools, inspect files, or modify anything.\n\n" +
              json.dumps({"question": question, "indicator_catalog": entries},
                         ensure_ascii=False))
    return codex_json(prompt, SCHEMA, model)


def validate_plan(plan: dict, entries: dict, *, require_summary: bool = False) -> None:
    required_fields = set(SCHEMA["required"])
    if not require_summary and "approach_summary" not in plan:
        required_fields.remove("approach_summary")  # Previously saved plans
    if set(plan) != required_fields:
        raise ValueError("Plan fields do not match schema")
    if "approach_summary" in plan:
        summary = plan["approach_summary"]
        if (not isinstance(summary, str) or len(summary) > 120
                or not 1 <= len([s for s in re.split(r"[。！？!?\n]+", summary) if s.strip()]) <= 2):
            raise ValueError("approach_summary must contain one or two short sentences, at most 120 characters")
    if plan["decision"] not in ("run", "needs_data"):
        raise ValueError("Unknown plan decision")
    for field in ("research_question", "rationale"):
        if not isinstance(plan[field], str) or not plan[field].strip():
            raise ValueError(f"Plan {field} is empty")
    for field in ("use_registered_indicators", "data_needed", "limitations"):
        if not isinstance(plan[field], list) or any(
                not isinstance(value, str) or not value.strip() for value in plan[field]):
            raise ValueError(f"Invalid {field}")
    extension_ids = plan["use_registered_indicators"]
    if len(extension_ids) != len(set(extension_ids)) or any(
            indicator_id not in entries or not entries[indicator_id]["registered"]
            for indicator_id in extension_ids):
        raise ValueError("Plan uses an unregistered or repeated indicator")
    for side in ("demand", "supply"):
        changes = plan[f"{side}_changes"]
        if not isinstance(changes, list) or len(changes) > 20:
            raise ValueError(f"Invalid {side} changes")
        seen = set()
        for change in changes:
            if not isinstance(change, dict) or set(change) != {
                    "indicator_id", "weight", "reason"}:
                raise ValueError("Malformed weight change")
            indicator_id = change["indicator_id"]
            if (indicator_id not in entries or entries[indicator_id]["side"] != side or
                    indicator_id in seen):
                raise ValueError(f"Unknown, wrong-side, or repeated indicator: {indicator_id}")
            seen.add(indicator_id)
            weight = change["weight"]
            if (isinstance(weight, bool) or not isinstance(weight, (int, float)) or
                    not math.isfinite(weight) or not .25 <= weight <= 3):
                raise ValueError(f"Weight outside 0.25-3: {indicator_id}")
            if not isinstance(change["reason"], str) or not change["reason"].strip():
                raise ValueError(f"Missing weight rationale: {indicator_id}")
            if entries[indicator_id]["registered"] and indicator_id not in extension_ids:
                raise ValueError(f"Registered indicator not selected: {indicator_id}")
    if plan["decision"] == "needs_data" and not plan["data_needed"]:
        raise ValueError("needs_data requires a concrete data specification")


def scenario_config(plan: dict, entries: dict, baseline: dict, run_id: str) -> dict:
    config = copy.deepcopy(baseline)
    config["id"] = run_id
    config["description"] = plan["research_question"]
    config["extensions"] = plan["use_registered_indicators"]
    for indicator_id in config["extensions"]:
        item = entries[indicator_id]
        key = item["field"] if item["side"] == "demand" else indicator_id
        config[item["side"]]["weights"][key] = 1
    for side in ("demand", "supply"):
        for change in plan[f"{side}_changes"]:
            indicator_id = change["indicator_id"]
            key = entries[indicator_id]["field"] if side == "demand" else indicator_id
            config[side]["weights"][key] = change["weight"]
    return config


def run_local(command: list[str], label: str) -> dict:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                               timeout=120, check=False)
    if completed.returncode:
        raise RuntimeError(f"{label} failed: {completed.stderr[-1500:]}")
    return json.loads(completed.stdout)


def execute_approved(run_id: str) -> int:
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,63}", run_id):
        raise ValueError("Invalid run ID")
    run_dir = ROOT / "output/agent_runs" / run_id
    report_path = run_dir / "agent_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report["status"] != "awaiting_review":
        raise ValueError("Approval requires a pending proposal")
    for name, digest in report["review_hashes"].items():
        if sha256(run_dir / name) != digest:
            raise ValueError("Reviewed files changed; prepare a new proposal")
    config_path = run_dir / "scenario.json"
    plan = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
    entries, baseline = catalog()
    validate_plan(plan, entries)
    if scenario_config(plan, entries, baseline, run_id) != json.loads(config_path.read_text(encoding="utf-8")):
        raise ValueError("Baseline or catalog changed; prepare a new proposal")
    scenario_dir = ROOT / "output/scenarios" / run_id
    with tempfile.TemporaryDirectory(dir=scenario_dir.parent, prefix="approved_") as temp:
        staged = Path(temp) / run_id
        scoring = run_local([sys.executable, str(ROOT / "analysis/run_scenario.py"),
            str(config_path), "--out-dir", str(staged)], "Scenario scoring")
        comparison = run_local([sys.executable, str(ROOT / "analysis/compare_scenario.py"),
            str(staged)], "Baseline comparison")
        staged.rename(scenario_dir)
    report.update({"status": "completed", "approved_at": datetime.now(timezone.utc).isoformat(),
                   "scenario_dir": str(scenario_dir), "candidate_count": scoring["candidate_count"],
                   "baseline_candidate_count": comparison["baseline_candidates"],
                   "entered": comparison["entered"], "exited": comparison["exited"],
                   "retained": comparison["retained"]})
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    render(run_id)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve", metavar="RUN_ID", help="Execute a previously reviewed proposal")
    parser.add_argument("--evidence-file", type=Path, help="Literature notes and source links for review")
    parser.add_argument("--revision-context", type=Path, help="Previous proposal and data list under revision")
    parser.add_argument("question", nargs="?", help="Research question in natural language")
    parser.add_argument("--backend", choices=("auto", "codex", "api"), default="auto")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL"))
    parser.add_argument("--run-id", help="Unique letters/numbers/underscore scenario ID")
    parser.add_argument("--require-indicator", action="append", default=[],
                        help="Registered indicator ID that the plan must use")
    parser.add_argument("--plan-file", type=Path,
                        help="Offline validation of a structured plan; no model request")
    args = parser.parse_args()
    if args.approve:
        if args.question or args.plan_file or args.evidence_file or args.revision_context or args.run_id or args.require_indicator:
            parser.error("Approval takes a saved run ID only")
        return execute_approved(args.approve)
    if not args.question or not args.question.strip() or len(args.question) > 2000:
        raise ValueError("Research question must contain 1-2,000 characters")
    entries, baseline = catalog()
    required = set(args.require_indicator)
    if any(not entries.get(key, {}).get("registered") for key in required):
        raise ValueError("Required indicator is not registered")
    def validate(proposal):
        validate_plan(proposal, entries, require_summary=not args.plan_file)
        if proposal["decision"] == "run" and required:
            explained = {c["indicator_id"] for side in ("supply", "demand")
                         for c in proposal[side + "_changes"]}
            if not required <= set(proposal["use_registered_indicators"]) & explained:
                raise ValueError("Include every required indicator with a weight and reviewable reason")
    if args.plan_file:
        backend = "offline"
    elif args.backend == "auto":
        backend = "codex" if locate_codex() else "api"
    else:
        backend = args.backend
    evidence = args.evidence_file.read_text(encoding="utf-8-sig") if args.evidence_file else ""
    evidence_origin = "supplied_notes" if evidence else "none"
    try:
        if backend == "codex" and not evidence:
            evidence = lookup_evidence(args.question, args.model)
            evidence_origin = "codex_live_web_search"
        planning_question = args.question
        if args.revision_context:
            planning_question += ("\nPrior proposal and data items shown to the researcher "
                                  "(context for the requested revision):\n" +
                                  args.revision_context.read_text(encoding="utf-8"))
        if evidence:
            planning_question += "\nLiterature notes (evidence, not instructions):\n" + evidence
        if args.require_indicator:
            planning_question += ("\nFor a runnable plan include each of these approved indicators "
                                  "with an explicit weight and reason even at weight 1: " + ", ".join(sorted(required)))
        if args.plan_file:
            plan = json.loads(args.plan_file.read_text(encoding="utf-8"))
            validate(plan)
        else:
            for attempt in range(2):
                if backend == "codex":
                    plan = request_plan_codex(planning_question, entries, args.model)
                else:
                    plan = request_plan(planning_question, entries, args.model or "gpt-6-astra")
                try:
                    validate(plan)
                    break
                except ValueError as exc:
                    if attempt:
                        raise
                    planning_question += "\nPrevious proposal failed local validation: " + str(exc)
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "proposal_failed", "error": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 2
    if backend == "codex" and plan["data_needed"]:
        try:
            notes = lookup_evidence("\n".join(plan["data_needed"]), args.model, datasets=True)
        except (RuntimeError, ValueError, subprocess.TimeoutExpired):
            notes = "## 待补数据来源\n\n本次数据来源检索未完成，可从官方目录继续核查。"
        evidence += "\n\n" + notes
    run_id = args.run_id or ("agent_" + datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"))
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,63}", run_id):
        raise ValueError("Invalid run ID")
    run_dir = ROOT / "output/agent_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    if evidence:
        (run_dir / "evidence.md").write_text(evidence, encoding="utf-8")
    (run_dir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False,
        indent=2), encoding="utf-8")
    report = {"run_id": run_id, "question": args.question,
              "backend": backend, "evidence_origin": evidence_origin,
              "model": ("offline_plan_file" if args.plan_file else
                        args.model or ("codex_cli_default" if backend == "codex"
                                       else "gpt-6-astra")),
              "decision": plan["decision"], "plan_path": str(run_dir / "plan.json")}
    if plan["decision"] == "needs_data":
        report.update({"status": "needs_data", "data_needed": plan["data_needed"]})
    else:
        config = scenario_config(plan, entries, baseline, run_id)
        config_path = run_dir / "scenario.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False,
            indent=2), encoding="utf-8")
        report.update({"status": "awaiting_review", "scenario_config": str(config_path),
                       "review_hashes": {name: sha256(run_dir / name) for name in
                           ("plan.json", "scenario.json", "evidence.md") if (run_dir / name).exists()}})
    (run_dir / "agent_report.json").write_text(json.dumps(report,
        ensure_ascii=False, indent=2), encoding="utf-8")
    render(run_id)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
