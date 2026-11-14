"""Download versioned, public Singapore source datasets for the transit baseline.

Only the two raw-data directories, demand/ and supply/, are used. API responses
are treated as data; download URLs are never logged or stored in the manifest.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SNAPSHOT = datetime.now(timezone.utc).date().isoformat()
METADATA_ROOT = "https://api-production.data.gov.sg/v2/public/api/datasets"
DOWNLOAD_ROOT = "https://api-open.data.gov.sg/v1/public/api/datasets"
API_PAUSE_SECONDS = 5.2
MAX_FILE_BYTES = 250_000_000

# The purpose describes why a raw dataset is staged; one file may support
# several of the 9 demand or 11 supply indicators.
SOURCES = [
    ("demand", "d_4e150bbd35c3145ea43019212c7b46c2", "household income"),
    ("demand", "d_1f8f5ec7201964e365c77551cab99503", "commute mode and bus use"),
    ("demand", "d_e9b1f437263fceebc0c1f0e60cd7b0f0", "labour force status"),
    ("demand", "d_90215b2256c68fe94a058cb931d29591", "education"),
    ("demand", "d_d95ae740c0f8961a0b10435836660ce0", "age by geography"),
    ("demand", "d_0ef47f84a0776b27010b242038ea2c6b", "household size"),
    ("demand", "d_21d8b67788ed8ef5705aa4bd5ec66b4b", "activity difficulty"),
    ("demand", "d_9eaccc6cc0f257cfd74d5c1ceb0fb663", "student travel mode"),
    ("demand", "d_4765db0e87b9c86336792efe8a1f7a66", "planning area boundaries"),
    ("demand", "d_8594ae9ff96d0c708bc2af633048edfb", "subzone boundaries"),
    ("demand", "d_17f5382f26140b1fdae0ba2ef6239d2f", "HDB dwelling units for grid allocation"),
    ("demand", "d_16b157c52ed637edd6ba1232e026258d", "HDB building geometries for dwelling-unit matching"),
    ("demand", "d_be71daeab5930f96b90ad2857454d876", "private dwelling units for grid allocation"),
    ("demand", "d_90d86daa5bfaa371668b84fa5f01424f", "URA Master Plan 2019 land-use polygons for zero-proxy grid audit"),
    ("demand", "d_e4495201ba4f77fa2ef9855bad6d2cd1", "SLA state private dwelling points for zero-proxy grid audit"),
    ("demand", "d_e8e3249d4433845bdd8034ae44329d9e", "URA Master Plan 2019 building footprints for zero-proxy grid audit"),
    ("supply", "d_3f172c6feb3f4f92a2f47d93eed2908a", "bus stop points"),
    ("supply", "d_b39d3a0871985372d7e1637193335da5", "MRT station exits"),
    ("supply", "d_be89529e906103da82ff06adec019f17", "workplace area by income"),
    ("supply", "d_548c33ea2d99e29ec63a7cc9edcccedc", "CHAS clinic points"),
    ("supply", "d_11edd0117280c5776651d7891114c88c", "supermarket licence addresses"),
]

_last_api_call = 0.0


def api_json(url: str) -> dict:
    global _last_api_call
    elapsed = time.monotonic() - _last_api_call
    if elapsed < API_PAUSE_SECONDS:
        time.sleep(API_PAUSE_SECONDS - elapsed)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "sg-transit-research/0.1"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=40) as response:
                payload = json.load(response)
            _last_api_call = time.monotonic()
            if payload.get("code") != 0:
                raise RuntimeError(f"API code {payload.get('code')}: {payload.get('errorMsg', '')}")
            return payload["data"]
        except urllib.error.HTTPError as exc:
            _last_api_call = time.monotonic()
            if exc.code in (429, 503) and attempt == 0:
                time.sleep(12)
                continue
            raise
    raise RuntimeError("unreachable")


def download_file(url: str, target: Path) -> tuple[int, str]:
    host = urllib.parse.urlparse(url).hostname or ""
    if not (host == "data.gov.sg" or host.endswith(".data.gov.sg") or host.endswith(".amazonaws.com")):
        raise ValueError(f"Unexpected download host: {host}")
    tmp = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    size = 0
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "sg-transit-research/0.1"})
        with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as output:
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > MAX_FILE_BYTES:
                    raise ValueError("File exceeds 100 MB safety limit")
                digest.update(block)
                output.write(block)
        if size == 0:
            raise ValueError("Empty file")
        tmp.replace(target)
        return size, digest.hexdigest()
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    previous_path = ROOT / "manifest.json"
    previous = {}
    if previous_path.exists():
        previous = {
            item["dataset_id"]: item
            for item in json.loads(previous_path.read_text(encoding="utf-8")).get("sources", [])
        }
    manifest = {"snapshot_utc": SNAPSHOT, "sources": []}
    for side, dataset_id, purpose in SOURCES:
        old = previous.get(dataset_id)
        if old and old.get("status") == "downloaded" and old.get("file"):
            old_path = ROOT / old["file"]
            if old_path.is_file() and hashlib.sha256(old_path.read_bytes()).hexdigest() == old.get("sha256"):
                manifest["sources"].append(old)
                continue
        entry = {
            "side": side,
            "dataset_id": dataset_id,
            "purpose": purpose,
            "source_page": f"https://data.gov.sg/datasets/{dataset_id}/view",
        }
        print(f"{side:6} {dataset_id} {purpose}", flush=True)
        try:
            metadata = api_json(f"{METADATA_ROOT}/{dataset_id}/metadata")
            fmt = str(metadata.get("format", "")).lower()
            if fmt not in {"csv", "geojson"}:
                raise ValueError(f"Unsupported format: {fmt!r}")
            directory = ROOT / side
            directory.mkdir(exist_ok=True)
            target = directory / f"{dataset_id}_{SNAPSHOT}.{fmt}"
            metadata_path = directory / f"{dataset_id}_{SNAPSHOT}.metadata.json"
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            entry.update({
                "name": metadata.get("name"),
                "format": fmt,
                "last_updated_at": metadata.get("lastUpdatedAt"),
                "coverage_start": metadata.get("coverageStart"),
                "coverage_end": metadata.get("coverageEnd"),
                "metadata_file": str(metadata_path.relative_to(ROOT)).replace("\\", "/"),
            })
            if not target.exists():
                base = f"{DOWNLOAD_ROOT}/{dataset_id}"
                if fmt == "csv":
                    api_json(f"{base}/initiate-download")
                for attempt in range(5):
                    poll = api_json(f"{base}/poll-download")
                    if poll.get("url"):
                        break
                    time.sleep(5)
                else:
                    raise RuntimeError("Download was not ready after five polls")
                download_file(poll["url"], target)
            raw = target.read_bytes()
            if fmt == "geojson":
                obj = json.loads(raw)
                if obj.get("type") != "FeatureCollection":
                    raise ValueError("GeoJSON is not a FeatureCollection")
                entry["feature_count"] = len(obj.get("features", []))
            elif b"," not in raw[:2048] and b";" not in raw[:2048]:
                raise ValueError("CSV header appears invalid")
            entry.update({
                "status": "downloaded",
                "file": str(target.relative_to(ROOT)).replace("\\", "/"),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })
        except Exception as exc:
            entry.update({"status": "failed", "error": str(exc)[:300]})
            print(f"  FAILED: {entry['error']}", flush=True)
        manifest["sources"].append(entry)
        (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    complete = sum(x["status"] == "downloaded" for x in manifest["sources"])
    print(f"Completed {complete}/{len(SOURCES)} datasets", flush=True)
    return 0 if complete == len(SOURCES) else 1


if __name__ == "__main__":
    sys.exit(main())
