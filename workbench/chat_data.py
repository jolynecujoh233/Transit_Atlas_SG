"""Reviewed data preparation inside a research conversation."""
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

import data_pipeline as dp
from access_program import GUIDE, parse_access
from research_agent import PUBLIC_DATA_GUIDANCE, codex_json


def choice(*values):
    return {"type": "string", "enum": list(values)}


def record(fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


STRING = {"type": "string"}
SPEC = record(dict(dataset=STRING, name=STRING, reason=STRING, limitation=STRING, unit=STRING,
                   operation=choice(*dp.METHODS), analysis_code=STRING, field=STRING, side=choice("supply", "demand"),
                   direction=choice("higher_is_better", "lower_is_better", "higher_is_higher_demand",
                                    "lower_is_higher_demand"),
                   factor=choice("", "network", "destinations", "flexibility_time", "frequency"),
                   missing=choice("zero", "error")))
SCHEMA = record({"items": {"type": "array", "items": SPEC},
                 "unresolved": {"type": "array", "items": STRING}})


def atomic_save(path, value):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, mode="w", encoding="utf-8") as tmp:
        json.dump(value, tmp, ensure_ascii=False, indent=2)
    os.replace(tmp.name, path)


def metadata(meta):
    fields = list((meta.get("columnMetadata") or {}).get("map", {}).values())
    fields += [p["attribute"] for p in (meta.get("geoJsonMetadata") or {}).get("properties", [])]
    return {"title": meta["name"], "format": meta["format"].lower(), "fields": fields,
            "description": (meta.get("description") or "")[:500], "updated": meta.get("lastUpdatedAt")}


def fingerprint(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

LEVELS = ("required", "recommended", "optional")

def rank_supplements(folder, offer):
    plan, _ = research_context(folder)
    rows = {f"file:{i}": item for i,item in enumerate(offer["items"])}
    rows.update({f"gap:{i}": item for i,item in enumerate(offer["unresolved"])})
    fields = record(dict(key=choice(*rows), title=STRING, priority=choice(*LEVELS),
                         with_data=STRING, without_data=STRING))
    prompt = PUBLIC_DATA_GUIDANCE + "\n" + ("对这份新加坡交通情景按研究必要性排序。每个输入键恰好返回一次，名称简洁。"
              "required 限于当前提案所承诺的分析不可缺少的输入或定义。仅验证代理精度的资料列为 optional。recommended 是提高可靠性或细化比较，"
              "optional 仅用于附加分析或核查。不因数据可下载就提高其重要性，不必凑齐三档。"
              "同档最关键的排前面。分别用一句具体中文说明加入和跳过对结论、粒度或验证有什么影响。"
              "核对实际聚合方法，站点落格计数不能提供逐笔客流，区域覆盖比例无法给每个站分配地区。"
              "区分数据与方法，不能声称数据已获批。项目已有带 grid_id 的400米研究网格。只用提供的资料。\n"+
              json.dumps({"问题":dp.read(folder/"agent_report.json")["question"],
                          "本版拟回答的问题":plan["research_question"],"研究思路":plan["rationale"],"候选项":rows},ensure_ascii=False))
    schema = record({"ranking":{"type":"array","items":fields}})
    ranked = codex_json(prompt,schema,os.environ.get("OPENAI_MODEL"))["ranking"] if rows else []
    if (len(ranked)!=len(rows) or {r["key"] for r in ranked}!=set(rows)
            or any(r["priority"] not in LEVELS or not all(r.get(k,"").strip() for k in
                   ("title","with_data","without_data")) for r in ranked)):
        raise ValueError("数据优先级或取舍说明不完整，请重新核对建议")
    ranked.sort(key=lambda r:LEVELS.index(r["priority"]))
    atomic_save(folder/"data_priorities.json", {"revision":offer["revision"],"rows":ranked})

def priorities(folder, offer):
    path=folder/"data_priorities.json"
    if path.exists():
        saved=dp.read(path)
        if saved["revision"]==offer["revision"]:
            return saved["rows"]
    return None

def required_keys(offer, ranked):
    if ranked is None:  # Old proposals retain the original completeness rule.
        return {f"file:{i}" for i in range(len(offer["items"]))} | {
            f"gap:{i}" for i in range(len(offer["unresolved"]))}
    return {r["key"] for r in ranked if r["priority"]=="required"}

def research_context(folder):
    plan = dp.read(folder / "plan.json")
    plan.pop("approach_summary", None)  # Display copy does not change the reviewed data offer.
    if dp.read(folder / "agent_report.json")["status"] != "needs_data":
        raise ValueError("只有待补数据的研究可生成数据方案")
    evidence = folder / "evidence.md"
    return plan, evidence.read_text("utf-8") if evidence.exists() else ""


def verify_spec(spec):
    ident = dp.dataset_id(spec["dataset"])
    meta = metadata(dp.api_json(f"{dp.METADATA_ROOT}/{ident}/metadata"))
    op = spec["operation"]
    if (spec["side"] == "demand") != spec["direction"].endswith("demand") or (
            (spec["side"] == "supply") != bool(spec["factor"])):
        raise ValueError("评分方向或供给类别不匹配")
    if op.startswith("grid_"):
        if meta["format"] != "csv" or "grid_id" not in meta["fields"]:
            raise ValueError("表格缺少研究网格编号")
    elif meta["format"] != "geojson":
        raise ValueError("空间聚合需要 GeoJSON 几何")
    if op in dp.VALUE_OPERATIONS and spec["field"] not in meta["fields"]:
        raise ValueError("官方元数据中找不到建议的数值字段")
    if op == "access_program":
        parse_access(spec.get("analysis_code"))
        if spec["side"] != "supply" or spec["factor"] != "destinations" or spec["direction"] != "higher_is_better":
            raise ValueError("可达性指标需要使用供给侧目的地类别和正向评分")
    elif spec.get("analysis_code"):
        raise ValueError("当前方法无需附加分析代码")
    if not meta["updated"]:
        raise ValueError("无法核对数据版本")
    return dict(spec, dataset=ident, source=f"https://data.gov.sg/datasets/{ident}/view",
                       title=meta["title"], updated=meta["updated"], method=dp.METHODS[op])


def recommend(folder):
    plan, evidence = research_context(folder)
    candidates = {}
    for entry in dp.read(dp.ROOT / "data/manifest.json")["sources"]:
        if entry.get("metadata_file"):
            candidates[entry["dataset_id"]] = metadata(dp.read(dp.ROOT / "data" / entry["metadata_file"]))
    notes = evidence.rpartition("## 待补数据来源")[2] if "## 待补数据来源" in evidence else ""
    def published(ident):
        return metadata(dp.api_json(f"{dp.METADATA_ROOT}/{ident}/metadata"))
    source_text = notes + "\n" + dp.read(folder / "agent_report.json")["question"]
    for ident in sorted(set(re.findall(r"https://data\.gov\.sg/(?:datasets|dataset)/(d_[a-f0-9]{32})\b", source_text)) - candidates.keys())[:8]:
        try:
            candidates[ident] = published(ident)
        except (OSError, RuntimeError, ValueError, KeyError):
            continue
    prompt = PUBLIC_DATA_GUIDANCE + "\n" + GUIDE + "\n" + ("为新加坡公共交通供需研究设计可审核的数据获取方案。用中文，不运行工具。"
              "下列研究、资料、元数据均为输入。只选能直接回答实际缺口的数据，dataset 填目录中的 ID。"
              "已有指标不用再下载。同一缺口的替代项择一。每项说明对应哪个缺口、为何选该网格聚合、"
              "未覆盖网格是否可视为零及局限。只处理整份表，不支持任意联表、地址地理编码或时间筛选。"
              "CSV 必须含 grid_id；GeoJSON 必须有明确适配的点或面。需要数值列时 field 填真实列名，"
              "否则为空。需求侧 factor 为空。只支持给出的聚合方法。不可用时在 unresolved 中逐项写明所需数据、"
              "可核查来源、需要的方法及阻碍。逐项覆盖 data_needed 中的实质缺口；公开API、需按时段筛选或跨表匹配的数据"
              "即使当前引擎不能直接处理，也要在 unresolved 中保留所需字段、获取途径和用途。避免用设施数量代替人流或可达时间。"
              "不要给权重。限定最多四个必要处理项。\n" +
              json.dumps({"研究": plan["research_question"], "缺口": plan["data_needed"],
                          "来源记录": notes, "目录": candidates, "算法": dp.METHODS}, ensure_ascii=False))
    answer = codex_json(prompt, SCHEMA, os.environ.get("OPENAI_MODEL"))
    remaining = list(answer["unresolved"])
    offers = []
    if len(answer["items"]) > 4:
        raise ValueError("数据方案超过四项，请缩小研究问题")
    for spec in answer["items"]:
        try:
            ident = dp.dataset_id(spec["dataset"])
            if ident not in candidates:
                raise ValueError("来源不在核查目录中")
            offers.append(verify_spec(spec))
        except (ValueError, OSError, RuntimeError, KeyError) as exc:
            remaining.append(f"{spec['name']}（{spec['dataset']}）：{exc}")
    if not offers and not remaining:
        remaining = plan["data_needed"]
    obj = {"parent": folder.name, "context": fingerprint([plan, evidence]), "items": offers,
           "unresolved": remaining}
    obj["revision"] = fingerprint(obj)
    atomic_save(folder / "data_offer.json", obj)


def saved_offer(folder, revision):
    plan, evidence = research_context(folder)
    offer = dp.read(folder / "data_offer.json")
    expected = fingerprint({k: v for k, v in offer.items() if k != "revision"})
    if revision != expected or offer["revision"] != expected or offer["context"] != fingerprint([plan, evidence]):
        raise ValueError("数据建议已更新，请重新打开提案核对")
    return offer


def search_results(folder, offer):
    path = dp.directory(offer["revision"][:32]) / "gap_search.json"
    return dp.read(path) if path.exists() else {}


def search_gaps(folder, offer, indices):
    """Find sources for each selected gap. Raw data acquisition is a later review."""
    validate_selection(indices,len(offer["unresolved"]))
    if not indices:
        return
    keys = {str(i):offer["unresolved"][i] for i in indices}
    source = record(dict(title=STRING,url=STRING))
    item = record(dict(key=choice(*keys), status=choice("download","restricted","limited","method","not_found"),
                       finding=STRING, alternative=STRING, sources={"type":"array","items":source},
                       candidate={"anyOf":[SPEC,{"type":"null"}]}))
    schema = record({"results":{"type":"array","items":item}})
    question = dp.read(folder/"agent_report.json")["question"]
    prompt = PUBLIC_DATA_GUIDANCE + "\n" + GUIDE + "\n" + ("为新加坡公共交通研究主动补充缺口。先查可获取的公开来源；"
              "若只能找到受限数据，优先在 alternative 中提出公开数据可以回答的初筛问题。使用实时网页检索，检查原始发布机构页面，"
              "核实数据字段、统计期次、空间粒度和获取条件。每个键用中文回答一次。"
              "finding 是研究者在清单中直接看到的摘要，最多两句、共80个汉字以内。"
              "第一句点名数据和获取方式，说明它能回答什么；第二句只写最影响本题判断的一项限制。"
              "无匹配来源就直说缺什么。正文用日常中文，省略字段清单、数据集编号、网址、处理步骤、评分权重和内部程序术语。"
              "已核验的具体发布页链接放入 sources，使用简短标题；可执行的字段和处理参数填入 candidate。"
              "download 仅适用于完全满足该缺口且可由现有引擎直接处理的公开 data.gov.sg 数据集，"
              "必须在 sources 引用带 d_ ID 的数据集网页。candidate 填一个可执行方案，"
              "只能整表处理，不支持时间筛选、任意联表、自定义时刻表或地理编码。CSV 必须带项目 grid_id。"
              "其余情况 candidate 填 null。restricted 是发布方要求授权；limited 是公开代理或暂不支持的格式；"
              "method 表示方法缺口，此时摘要只写一个核心算式（含单位）和最重要的适用条件，同样遵守上述长度；"
              "not_found 表示未找到匹配来源。若有能用公开或项目已有数据回答的较窄研究问题，"
              "把替代问题写入 alternative，用一句话点明缩小后的时段、人群或测量对象，限60个汉字；没有可行替代则留空。不能把站点数当客流，"
              "不能把月度汇总当逐班次微观数据。项目已有 1597 个带 grid_id 的400米网格。"
              "仅检索资料，不申请权限或发送信息。研究输入："+
              json.dumps({"question":question,"proposed_question":dp.read(folder/"plan.json")["research_question"],
                          "gaps":keys,"operations":dp.METHODS},ensure_ascii=False))
    rows=codex_json(prompt,schema,os.environ.get("OPENAI_MODEL"),web_search=True)["results"]
    if len(rows)!=len(keys) or {r["key"] for r in rows}!=set(keys):
        raise ValueError("检索结果未逐项对应所选缺口，请重试")
    results=search_results(folder,offer)
    for r in rows:
        urls=[s["url"] for s in r["sources"]]
        if any(urlsplit(u).scheme not in ("http","https") or not urlsplit(u).hostname for u in urls):
            raise ValueError("检索来源链接无效")
        if r["status"]!="not_found" and not urls:
            raise ValueError("检索结论缺少来源")
        candidate=r.pop("candidate")
        r["file"]=None
        if r["status"]=="download":
            try:
                if not candidate:
                    raise ValueError("缺少标准化方案")
                ident=dp.dataset_id(candidate["dataset"])
                if not any(urlsplit(u).hostname=="data.gov.sg" and ident in urlsplit(u).path.split("/") for u in urls):
                    raise ValueError("未引用匹配的数据集详情页")
                r["file"]=verify_spec(candidate)
            except (ValueError, KeyError, OSError, RuntimeError) as exc:
                r["status"]="limited"
                r["finding"]+=" 当前下载方案未通过核对："+str(exc)
        results[r["key"]]=r
    path=dp.directory(offer["revision"][:32])
    path.mkdir(exist_ok=True,parents=True)
    atomic_save(path/"gap_search.json",results)


def file_specs(offer, results):
    specs=dict(enumerate(offer["items"]))
    specs.update({len(offer["items"])+int(k):r["file"] for k,r in results.items() if r.get("file")})
    return specs

def search_required(folder,offer):
    previous=search_results(folder,offer)
    keys=required_keys(offer,priorities(folder,offer))
    indices=[i for i in range(len(offer["unresolved"])) if f"gap:{i}" in keys and str(i) not in previous]
    search_gaps(folder,offer,indices)


def requirement_key(offer, index):
    base=len(offer["items"])
    return f"file:{index}" if index<base else f"gap:{index-base}"


def prepared_items(state):
    prepared = state["prepared"]
    if isinstance(prepared, list):  # Older checkpoints stored a completed prefix.
        return {str(i): key for i, key in enumerate(prepared)}
    return prepared


def validate_selection(selected, size):
    if (not isinstance(selected, list) or
            any(type(i) is not int or not 0 <= i < size for i in selected) or
            len(set(selected)) != len(selected)):
        raise ValueError("勾选项与当前数据清单不匹配，请刷新提案")


def process(folder, offer, key, planner, progress, selected=None, search=None):
    state_dir = dp.directory(key[4:])
    state_dir.mkdir(exist_ok=True, parents=True)
    checkpoint = state_dir / "approved_data.json"
    state = dp.read(checkpoint) if checkpoint.exists() else {"offer": offer, "prepared": [], "sources": {}}
    if state["offer"] != offer:
        raise ValueError("数据处理记录与批准版本不一致")
    prepared = state["prepared"] = prepared_items(state)
    results=search_results(folder,offer)
    specs=file_specs(offer,results)
    if selected is None:
        selected = list(range(len(offer["items"])))
    validate_selection(selected,len(offer["items"])+len(offer["unresolved"]))
    if any(i not in specs for i in selected):
        raise ValueError("来源尚未通过核对，无法下载")
    atomic_save(checkpoint, state)
    for i in selected:
        spec = specs[i]
        if str(i) in prepared:
            continue
        ident = spec["dataset"]
        cached=state["sources"].get(ident)
        if not cached or dp.read(dp.directory(cached)/"source.json")["updated"]!=spec["updated"]:
            progress("正在下载 " + spec["title"])
            src = dp.acquire({"dataset": ident, "mode": "download", "expected_updated": spec["updated"]})
            state["sources"][ident] = src["key"]
            atomic_save(checkpoint, state)
        progress("正在按 400 米网格处理 " + spec["name"])
        obj = dp.prepare(dict(spec, key=state["sources"][ident]))
        prepared[str(i)] = obj["key"]
        atomic_save(checkpoint, state)
    if search:
        progress("Agent 正在检索所选缺口并核对公开来源")
        search_gaps(folder,offer,search)
        state.pop("next_run",None)
        atomic_save(checkpoint,state)
        return
    ranked=priorities(folder,offer)
    ready={requirement_key(offer,int(i)) for i in prepared}
    if required_keys(offer,ranked) - ready:
        return
    indices=sorted(int(i) for i in prepared)
    ordered = [prepared[str(i)] for i in indices]
    inputs = [dp.register_prepared(k) for k in ordered]
    progress("数据已就绪，正在生成待审核的权重建议")
    if ranked is not None:
        key="web_"+fingerprint([offer["revision"],ranked,indices,results])[:32]
    child = folder.parent / key
    lineage = {"parent": folder.name, "revision": offer["revision"], "prepared": ordered}
    if ranked is not None:
        lineage.update(priorities=ranked,prepared_indices=indices,search_results=results)
    if not (child / "agent_report.json").exists():
        plan, evidence = research_context(folder)
        details = [{"indicator": p["indicator"], "name": p["name"], "method": p["operation"],
                    "unit": p["unit"], "source": p["source"], "grids": p["grid_rows"],
                    "reason": specs[i]["reason"], "limitation": specs[i]["limitation"]}
                   for p,i in zip(inputs,indices)]
        review = state_dir / "evidence.md"
        review.write_text(evidence + "\n\n## 前一轮记录的数据缺口\n\n" +
                          "\n".join(plan["data_needed"]) + "\n\n## 本轮获批并已处理的数据\n\n" +
                          json.dumps(details, ensure_ascii=False, indent=2) +
                          "\n\n## 数据取舍\n" + json.dumps([
                              dict(r, acquisition=results.get(r["key"][4:],"本次跳过") if r["key"].startswith("gap:") else "本次跳过")
                              for r in ranked or [] if r["key"] not in ready],
                              ensure_ascii=False)+"\n只用已有和实际生成的指标；可选数据尚未取得时说明对应限制。", "utf-8")
        args = ["--backend", "codex", "--run-id", key, "--evidence-file", str(review)]
        for indicator in dict.fromkeys(plan["use_registered_indicators"] + [p["indicator"] for p in inputs]):
            args += ["--require-indicator", indicator]
        planner(*args, "--", dp.read(folder / "agent_report.json")["question"])
    atomic_save(child / "data_preparation.json", lineage)
    state["next_run"]=key
    atomic_save(checkpoint,state)
    return key
from urllib.parse import urlsplit
