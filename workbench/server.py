"""Local browser interface for the reviewed research workflow."""
import argparse
import csv
import hashlib
import ipaddress
import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import threading
import uuid
import webbrowser
import data_pipeline
import chat_data
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

WEB = Path(__file__).resolve().parent
ROOT = WEB.parent
RUNS = ROOT / "output/agent_runs"
SCENARIOS = ROOT / "output/scenarios"
EXAMPLE = "senior_chas_question_only_v1"
FINISHED = "senior_chas_review_v1"
BUSY = set()
ERRORS = {}
STAGES = {}
LOCK = threading.Lock()
PORT = 8764

def lan_interfaces():
    from qgis.PyQt.QtNetwork import QNetworkInterface
    addresses = []
    for interface in QNetworkInterface.allInterfaces():
        if not interface.flags() & QNetworkInterface.IsRunning or interface.type() not in (
                QNetworkInterface.Wifi, QNetworkInterface.Ethernet):
            continue
        for entry in interface.addressEntries():
            if entry.ip().toIPv4Address() and entry.prefixLength() > 0:
                addresses.append(ipaddress.IPv4Interface(f"{entry.ip().toString()}/{entry.prefixLength()}"))
    return addresses

class WorkbenchServer(ThreadingHTTPServer):
    def verify_request(self, request, client_address):
        local = ipaddress.IPv4Address(request.getsockname()[0])
        remote = ipaddress.IPv4Address(client_address[0])
        if local.is_loopback:
            return remote.is_loopback
        return self.lan_enabled and any(
            local == address.ip and remote in address.network for address in lan_interfaces())

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def run_agent(*args):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    result = subprocess.run([sys.executable, str(ROOT / "analysis/research_agent.py"), *args],
                            cwd=ROOT, env=env, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=1200,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Agent 运行失败")[-1200:])

def run_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:web_[a-f0-9]{32}|senior_chas_(?:question_only_v1|review_v1))', value):
        raise ValueError("无效的研究编号")
    return value

def new_id():
    return "web_" + uuid.uuid4().hex

def start_job(key, function, args, *, reuse=False):
    with LOCK:
        if reuse and key in BUSY:
            return
        if key in BUSY or len(BUSY) >= 3:
            raise ValueError("研究任务正在处理，请稍后重试")
        BUSY.add(key)
        ERRORS.pop(key, None)
    def work():
        try:
            function(*args)
        except Exception as exc:
            with LOCK:
                ERRORS[key] = str(exc)
        finally:
            with LOCK:
                BUSY.discard(key)
                STAGES.pop(key, None)
    threading.Thread(target=work, daemon=True).start()

def stage(key, message):
    with LOCK:
        STAGES[key] = message

def suggest_data(key):
    folder = RUNS / key
    stage(key, "正在核对数据来源并拟定网格标准化方法")
    try:
        chat_data.recommend(folder)
        offer=read(folder/"data_offer.json")
        chat_data.rank_supplements(folder,offer)
        (folder/"data_offer_error.json").unlink(missing_ok=True)
        stage(key,"Agent 正在为必需数据和方法检索公开来源")
        try:
            chat_data.search_required(folder,offer)
            (folder/"partial_data_error.json").unlink(missing_ok=True)
        except Exception as exc:
            chat_data.atomic_save(folder/"partial_data_error.json", {"revision":offer["revision"], "message":"来源检索未完成，可勾选缺口重试："+str(exc)[:400]})
    except Exception as exc:
        chat_data.atomic_save(folder/"data_offer_error.json", {"message": str(exc)[:550]})

def suggest_if_needed(key):
    if read(RUNS/key/"agent_report.json")["status"] == "needs_data":
        suggest_data(key)

def propose(key, question, previous=None):
    args = ["--backend", "codex", "--run-id", key]
    with tempfile.TemporaryDirectory() as tmp:
        if previous is not None:
            context = Path(tmp)/"prior.json"
            context.write_text(json.dumps(previous, ensure_ascii=False), "utf-8")
            args += ["--revision-context", str(context)]
        run_agent(*args, "--", question)
    suggest_if_needed(key)

def prepare_selection(parent, key, offer, selected, search=None):
    folder = RUNS / parent
    error_path = folder / "partial_data_error.json"
    try:
        child=chat_data.process(folder, offer, key, run_agent, lambda message: stage(parent, message), selected,search)
        if child and not (RUNS/child/"data_offer.json").exists():
            suggest_if_needed(child)
        error_path.unlink(missing_ok=True)
    except Exception as exc:
        chat_data.atomic_save(error_path, {"revision": offer["revision"], "message": str(exc)[:600]})

def info(key):
    with LOCK:
        if key in BUSY:
            return {"status":"working", "id":key, "stage":STAGES.get(key, "")}
        if key in ERRORS:
            return {"status":"failed", "error":ERRORS[key], "id":key}
    folder = RUNS / key
    report = read(folder / "agent_report.json")
    result = {k:report[k] for k in ("status","question","candidate_count","entered","exited","retained") if k in report}
    evidence = folder / "evidence.md"
    result.update(id=key, plan=read(folder/"plan.json"), evidence=evidence.read_text("utf-8") if evidence.exists() else "")
    if report["status"] == "needs_data":
        if (folder/"data_offer_error.json").exists():
            result["data_offer_error"] = read(folder/"data_offer_error.json")["message"]
        elif (folder/"data_offer.json").exists():
            offer = result["data_offer"] = read(folder/"data_offer.json")
            result["gap_results"]=chat_data.search_results(folder,offer)
            result["search_version"]=chat_data.fingerprint(result["gap_results"])
            result["data_priorities"]=chat_data.priorities(folder,offer)
            if result["data_priorities"] is not None:
                result["priority_version"]=chat_data.fingerprint(result["data_priorities"])
            if offer["items"] or offer["unresolved"]:
                checkpoint = data_pipeline.directory(offer["revision"][:32])/"approved_data.json"
                if checkpoint.exists():
                    state = read(checkpoint)
                    if state["offer"] == offer:
                        if state.get("next_run"):
                            result["next_run"]=state["next_run"]
                        result["partial_inputs"] = [
                            dict(read(data_pipeline.directory(k)/"prepared.json"), offer_index=int(i))
                            for i,k in chat_data.prepared_items(state).items()]
                child = "web_" + offer["revision"][:32]
                if (RUNS/child/"data_preparation.json").exists():
                    result["next_run"] = child
                error_path = folder/"partial_data_error.json"
                if error_path.exists():
                    failure = read(error_path)
                    if failure["revision"] == offer["revision"]:
                        result["partial_error"] = failure["message"]
    result["prepared_inputs"] = []
    for indicator in result["plan"].get("use_registered_indicators", []):
        if re.fullmatch(r"web_indicator_[a-f0-9]{32}", indicator):
            result["prepared_inputs"].append(read(data_pipeline.directory(indicator[-32:])/"prepared.json"))
    if report["status"] == "completed":
        with (SCENARIOS/key/"baseline_comparison.csv").open(encoding="utf-8-sig", newline="") as f:
            result["changes"] = {r["grid_id"]:r["candidate_change"] for r in csv.DictReader(f)}
    return result

def approve(original, final, edits):
    folder = RUNS / original
    report = read(folder/"agent_report.json")
    if report["status"] != "awaiting_review":
        raise ValueError("仅待审核方案可执行")
    for name,digest in report["review_hashes"].items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest() != digest:
            raise ValueError("审核文件已变更，请重新提案")
    if edits:
        plan = read(folder/"plan.json")
        allowed = {c["indicator_id"]:c for side in ("demand","supply") for c in plan[side+"_changes"]}
        for field,value in edits.items():
            if field not in allowed or type(value) not in (float,int) or not .25 <= value <= 3:
                raise ValueError("权重必须在 0.25–3 内，并属于当前提案")
            change = allowed[field]
            old = change["weight"]
            change.update(weight=value, reason=f"研究者审核时将模型建议 {old} 调整为 {value}。原建议理由：" + change["reason"])
        plan["rationale"] += " 本版含研究者人工调权，最终权重见参数表。"
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp)/"plan.json"
            file.write_text(json.dumps(plan,ensure_ascii=False),"utf-8")
            args=["--plan-file",str(file),"--run-id",final]
            if (folder/"evidence.md").exists():
                args+=["--evidence-file",str(folder/"evidence.md")]
            run_agent(*args,"--",report["question"])
        (RUNS/final/"review_revision.json").write_text(json.dumps({"source_run":original,"source_hashes":report["review_hashes"],"human_edits":edits},ensure_ascii=False,indent=2),"utf-8")
    run_agent("--approve", final)

class Handler(BaseHTTPRequestHandler):
    def valid_host(self):
        local = self.connection.getsockname()[0]
        host = self.headers.get("Host")
        return host == f"{local}:{PORT}" or (local == "127.0.0.1" and host == f"localhost:{PORT}")

    def send(self,body,mime="application/json; charset=utf-8",code=200):
        if not isinstance(body,bytes):
            body=json.dumps(body,ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type",mime)
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            if not self.valid_host():
                return self.send({},code=403)
            path=urlparse(self.path).path
            if path.startswith("/api/prepared/"):
                folder=data_pipeline.directory(path.split("/")[-1])
                item=read(folder/"prepared.json")
                return self.send((folder/"grid"/(item["indicator"]+"_1597.csv")).read_bytes(),"text/csv; charset=utf-8")
            if path.startswith("/api/run/"):
                return self.send(info(run_id(path.split("/")[-1])))
            if path=="/api/sources":
                sources=read(ROOT/"data/manifest.json")["sources"]
                public=[{"name":x["name"],"url":x["source_page"],"purpose":x["purpose"]} for x in sources]
                gtfs=read(ROOT/"data/supply/singapore_gtfs_v2026-07-12.provenance.json")
                return self.send(public+[{"name":"Singapore GTFS · "+gtfs["release_tag"],"url":gtfs["release_page"],"purpose":"routing"}])
            if path.startswith("/api/export/"):
                key=run_id(path.split("/")[-1])
                return self.send((SCENARIOS/key/"baseline_comparison.csv").read_bytes(),"text/csv; charset=utf-8")
            name=path.strip("/") or "index.html"
            if name not in {"index.html","app.js","data-ui.js","atlas.js","atlas.json","style.css","i18n.js"}:
                return self.send({},code=404)
            return self.send((WEB/name).read_bytes(),mimetypes.guess_type(name)[0] or "application/octet-stream")
        except (ValueError,OSError) as e:
            self.send({"error":str(e)},code=404)

    def do_POST(self):
        try:
            origin=self.headers.get("Origin","")
            if not self.valid_host() or origin!="http://"+self.headers.get("Host","") or self.headers.get_content_type()!="application/json":
                return self.send({},code=403)
            size=int(self.headers.get("Content-Length","0"))
            if not 0<size<20000: raise ValueError("请求长度有误")
            data=json.loads(self.rfile.read(size))
            if self.path in ("/api/data/download","/api/data/prepare"):
                fn=data_pipeline.acquire if self.path.endswith("/download") else data_pipeline.prepare
                try:
                    return self.send(fn(data))
                except Exception as exc:
                    return self.send({"error":str(exc)[:550]},code=400)
            if self.path=="/api/data/attach":
                parent=RUNS/run_id(data["parent"]) if data.get("parent") else None
                key=new_id()
                start_job(key,data_pipeline.attach,(data,key,parent,run_agent))
            elif self.path=="/api/data/suggest":
                key=run_id(data["id"])
                if info(key)["status"]!="needs_data": raise ValueError("该研究当前无需补充数据")
                start_job(key,suggest_data,(key,))
            elif self.path=="/api/data/confirm":
                parent=run_id(data["id"])
                current=info(parent)
                if current["status"]!="needs_data" or (RUNS/parent/"data_offer_error.json").exists():
                    raise ValueError("请先查看最新数据建议")
                offer=chat_data.saved_offer(RUNS/parent,data["revision"])
                if data.get("priority_version")!=current.get("priority_version"):
                    raise ValueError("优先级建议已有更新，请刷新后核对选择")
                if data.get("search_version")!=current["search_version"]:
                    raise ValueError("来源检索记录已更新，请刷新后确认")
                selected=data["selected"]
                search=data["search"]
                base=len(offer["items"])
                chat_data.validate_selection(selected,base+len(offer["unresolved"]))
                chat_data.validate_selection(search,len(offer["unresolved"]))
                specs=chat_data.file_specs(offer,current["gap_results"])
                if any(i not in specs for i in selected) or any(i+base in specs for i in search):
                    raise ValueError("请核对最新的检索和下载选项")
                done={chat_data.requirement_key(offer,p["offer_index"]) for p in current.get("partial_inputs",[])}
                blocked=chat_data.required_keys(offer,current["data_priorities"]) - done
                if not selected and not search and blocked:
                    raise ValueError("请先选择本轮要获取的数据")
                key=parent
                child="web_"+offer["revision"][:32]
                start_job(parent,prepare_selection,(parent,child,offer,selected,search))
            elif self.path=="/api/propose":
                question=data["question"].strip()
                if not 1<=len(question)<=1500: raise ValueError("研究问题需在 1–1500 字内")
                key=new_id()
                previous=None
                if data.get("parent"):
                    old=info(run_id(data["parent"]))
                    plan=old["plan"]
                    previous={k:old[k] for k in ("plan","data_offer","gap_results","partial_inputs","prepared_inputs","evidence") if k in old}
                    question=("上一版研究问题："+plan["research_question"]+"。本轮修改要求："+question)
                if len(question)>1940: raise ValueError("本轮问题太长，请缩短补充说明")
                start_job(key,propose,(key,question+" 请用中文提供可审核方案与权重理由。",previous))
            elif self.path=="/api/approve":
                original=run_id(data["id"]); edits=data.get("edits",{})
                if not isinstance(edits,dict): raise ValueError("参数格式有误")
                if info(original)["status"]!="awaiting_review": raise ValueError("方案当前无法审核")
                key=new_id() if edits else original
                start_job(key,approve,(original,key,edits))
            else: return self.send({},code=404)
            self.send({"id":key},code=202)
        except (KeyError,ValueError,OSError,TypeError,AttributeError) as e:
            self.send({"error":str(e)},code=400)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--port", type=int, default=PORT, help="HTTP port (0 chooses an available port)")
    parser.add_argument("--lan", action="store_true", help="Allow clients on the same Wi-Fi/Ethernet subnet")
    args=parser.parse_args()
    interfaces = lan_interfaces() if args.lan else []
    server=WorkbenchServer(("0.0.0.0" if args.lan else "127.0.0.1",args.port),Handler)
    PORT=server.server_port
    server.lan_enabled = args.lan
    for address in interfaces:
        print(f"LAN: http://{address.ip}:{PORT}/", flush=True)
    if args.open: webbrowser.open(f"http://127.0.0.1:{PORT}/")
    print(f"http://127.0.0.1:{PORT}/",flush=True)
    server.serve_forever()
