"""Download public datasets and prepare reviewed grid indicators for the web UI."""
import json
import math
import os
import re
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "data"))
from download_sources import api_json, download_file, DOWNLOAD_ROOT, METADATA_ROOT
from ingest_raw_indicator import ingest, profile, OPERATIONS, VALUE_OPERATIONS
from register_indicator import validate_manifest
from run_scenario import REGISTRY, sha256

STORE = ROOT / "output/data_preparation"
METHODS = {
    "access_program":"按审核的出行方式和时间阈值计算目的地可达性",
    "point_count":"网格内点记录数", "point_sum":"网格内点属性求和", "point_mean":"网格内点属性平均",
    "grid_sum":"按 grid_id 求和", "grid_mean":"按 grid_id 求平均",
    "polygon_coverage_share":"网格内面覆盖比例", "polygon_area_weighted_mean":"按重叠面积加权平均",
    "polygon_prorated_sum":"按重叠面积分配总量",
}
def read(p):
    return json.loads(p.read_text("utf-8-sig"))

def save(p,obj):
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),"utf-8")

def directory(key):
    if not isinstance(key,str) or not re.fullmatch("[a-f0-9]{32}",key):
        raise ValueError("数据版本编号无效")
    return STORE/key

def dataset_id(value):
    m=re.fullmatch(r"(?:https://data\.gov\.sg/(?:datasets|dataset)/)?(d_[a-f0-9]{32})(?:/view)?/?(?:\?[^#]*)?",str(value).strip())
    if not m:
        raise ValueError("请输入 data.gov.sg 数据集详情链接或 d_ 开头的数据集 ID")
    return m[1]

def acquire(data):
    ident=dataset_id(data.get("dataset",""))
    mode=data.get("mode","download")
    key=uuid.uuid4().hex
    folder=directory(key)
    folder.mkdir(parents=True)
    source=f"https://data.gov.sg/datasets/{ident}/view"
    if mode=="snapshot":
        entries=read(ROOT/"data/manifest.json")["sources"]
        entry=next((x for x in entries if x["dataset_id"]==ident and x.get("status")=="downloaded"),None)
        if not entry: raise ValueError("本机没有这个数据集的快照，可改选官方下载")
        path=ROOT/"data"/entry["file"]
        if sha256(path)!=entry["sha256"]: raise ValueError("本地快照校验失败")
        name,year=entry["name"],entry["last_updated_at"]
    elif mode=="download":
        meta=api_json(f"{METADATA_ROOT}/{ident}/metadata")
        fmt=str(meta.get("format","")).lower()
        if fmt not in {"csv","geojson"}: raise ValueError("此入口支持 CSV 和 GeoJSON")
        name,year=meta["name"],meta.get("lastUpdatedAt") or "来源未提供更新日期"
        if data.get("expected_updated") and year != data["expected_updated"]:
            raise ValueError("发布方已更新数据版本，请重新生成并确认数据建议")
        url=f"{DOWNLOAD_ROOT}/{ident}"
        if fmt=="csv": api_json(url+"/initiate-download")
        for attempt in range(5):
            download=api_json(url+"/poll-download").get("url")
            if download: break
            time.sleep(3)
        if not download: raise ValueError("官方文件尚未准备好，请稍后重试")
        path=folder/("source."+fmt)
        download_file(download,path)
    else: raise ValueError("未知数据获取方式")
    meta=profile(path)
    geo=set(meta["geometry_types"] or [])
    columns=[c["name"] for c in meta["columns"]]
    if geo=={"Point"}: ops=["point_count","point_sum","point_mean","access_program"]
    elif geo and geo <= {"Polygon","MultiPolygon"}: ops=[x for x in METHODS if x.startswith("polygon")]
    elif not geo and "grid_id" in columns: ops=["grid_sum","grid_mean"]
    else: ops=[]
    obj={"key":key,"dataset":ident,"name":name,"source":source,"updated":year,"mode":mode,
         "operations":{op:METHODS[op] for op in ops},"profile":meta}
    save(folder/"source.json",obj)
    return obj

def prepare(data):
    src=read(directory(data["key"])/"source.json")
    op=data.get("operation")
    compatible_access = op == "access_program" and set(src["profile"]["geometry_types"] or []) == {"Point"}
    if op not in src["operations"] and not compatible_access: raise ValueError("该操作与数据空间结构不匹配")
    side=data.get("side")
    name=str(data.get("name","")).strip()
    unit=str(data.get("unit","")).strip()
    if not name or not unit: raise ValueError("请填写指标含义与单位")
    key=uuid.uuid4().hex
    folder=directory(key)
    folder.mkdir(parents=True)
    indicator="web_indicator_"+key
    spec={"id":indicator,"side":side,"description":name,"unit":unit,
          "source":src["source"],"source_year":src["updated"],"source_file":src["profile"]["source_file"],
          "direction":data.get("direction"),"factor":data.get("factor") if side=="supply" else None,
          "value_field":data.get("field") if op in VALUE_OPERATIONS else None,"operation":op,
          "source_crs":None,"layer":None,"sheet":None,"x_field":None,"y_field":None,
          "where":[],"missing_policy":data.get("missing")}
    if op == "access_program":
        spec["analysis_code"] = data.get("analysis_code")
    product=ingest(spec,folder/"grid",expected_source_sha256=src["profile"]["source_sha256"])
    _,manifest=validate_manifest(read(Path(product["manifest"])))
    audit=read(Path(product["audit"]))
    obj={"key":key,"source_key":src["key"],"name":name,"side":side,"unit":unit,"indicator":indicator,
         "operation":METHODS[op],"direction":spec["direction"],"missing":spec["missing_policy"],
         "source":src["source"],"source_name":src["name"],"raw_rows":product["source_rows"],
         "grid_rows":product["grid_rows"],"summary":audit["value_summary"],"aggregation":audit["aggregation"]}
    save(folder/"manifest.json",manifest)
    save(folder/"prepared.json",obj)
    return obj

def register_prepared(key):
    folder=directory(key)
    obj=read(folder/"prepared.json")
    _,manifest=validate_manifest(read(folder/"manifest.json"))
    if manifest!=read(folder/"manifest.json"): raise ValueError("标准化数据已变化，请重新准备")
    REGISTRY.mkdir(exist_ok=True,parents=True)
    target=REGISTRY/(obj["indicator"]+".json")
    if not target.exists():
        with tempfile.NamedTemporaryFile(dir=REGISTRY,suffix=".tmp",delete=False) as f:
            tmp=Path(f.name)
        save(tmp,manifest)
        os.replace(tmp,target)
    if read(target)!=manifest: raise ValueError("指标版本不一致")
    return obj

def attach(data,run_key,parent,run_agent):
    obj=register_prepared(data["key"])
    weight=data.get("weight",1)
    if type(weight) not in (int,float) or not math.isfinite(weight) or not .25<=weight<=3:
        raise ValueError("权重范围为 0.25 至 3")
    if parent:
        plan=read(parent/"plan.json")
        if plan["decision"]!="run": raise ValueError("该研究仍缺数据，请先生成可执行的研究方案，或从等权基线建立新方案")
    else:
        plan={"decision":"run","research_question":"引入"+obj["name"]+"后，公共交通供需缺口如何变化？",
              "rationale":"在等权基线上纳入研究者选择的新指标。","supply_changes":[],"demand_changes":[],
              "use_registered_indicators":[],"data_needed":[],"limitations":["结果为网格尺度的相对筛选。"]}
    indicator=obj["indicator"]
    if indicator in plan["use_registered_indicators"]: raise ValueError("此版本指标已在方案内")
    plan["use_registered_indicators"].append(indicator)
    reason=f"{obj['source_name']}，采用{obj['operation']}，单位为{obj['unit']}。"
    plan[obj["side"]+"_changes"].append({"indicator_id":indicator,"weight":weight,"reason":reason})
    plan["rationale"]+=" 新增指标："+obj["name"]+"。"+reason
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/"plan.json"
        save(path,plan)
        args=["--run-id",run_key,"--plan-file",str(path)]
        if parent and (parent/"evidence.md").exists(): args+=["--evidence-file",str(parent/"evidence.md")]
        run_agent(*args,"--",plan["research_question"])
    save(ROOT/"output/agent_runs"/run_key/"data_preparation.json",
         {"prepared":obj,"parent":parent.name if parent else None})
