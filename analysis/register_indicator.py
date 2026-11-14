"""Validate and register one prepared 1,597-grid indicator for agent scenarios.

The input manifest must name a project-local CSV with grid_id and one numeric
field. Registration records the CSV hash; it does not infer an indicator from
raw sources or modify the published baseline.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from run_scenario import FACTORS, REGISTRY, ROOT, sha256, source_path


def validate_manifest(manifest: dict) -> tuple[Path, dict]:
    required = {"id", "side", "field", "source_csv", "source_year",
                "source", "description", "unit", "direction", "method"}
    if not required <= set(manifest):
        raise ValueError(f"Manifest missing: {sorted(required - set(manifest))}")
    if manifest["side"] not in ("demand", "supply"):
        raise ValueError("side must be demand or supply")
    if any(not isinstance(manifest[key], str) or not manifest[key].strip()
           for key in required):
        raise ValueError("All required manifest fields must be nonempty strings")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", manifest["id"]):
        raise ValueError("Invalid indicator ID")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", manifest["field"]):
        raise ValueError("Invalid indicator field")
    baseline_config = json.loads((ROOT / "config/scenarios/baseline_v1.json").read_text(
        encoding="utf-8"))
    baseline_supply = json.loads((ROOT / "output/supply/supply_indicator_dictionary.json").read_text(
        encoding="utf-8"))
    if (manifest["id"] in baseline_config["demand"]["weights"] or
            manifest["id"] in baseline_config["supply"]["weights"] or
            manifest["id"] in {item["id"] for item in baseline_supply["indicators"]}):
        raise ValueError("Indicator ID conflicts with the baseline")
    if manifest["side"] == "demand":
        if manifest["direction"] not in ("higher_is_higher_demand",
                                          "lower_is_higher_demand"):
            raise ValueError("Invalid demand direction")
    else:
        if manifest["direction"] not in ("higher_is_better", "lower_is_better"):
            raise ValueError("Invalid supply direction")
        if manifest.get("factor") not in FACTORS:
            raise ValueError(f"Supply factor must be one of {FACTORS}")
    path = source_path(manifest["source_csv"])
    data = pd.read_csv(path)
    field = manifest["field"]
    if field not in data or "grid_id" not in data or data.grid_id.duplicated().any():
        raise ValueError("CSV requires unique grid_id and the declared numeric field")
    baseline = pd.read_csv(ROOT /
        "output/scenarios/baseline_v1/grid_results_primary_1597.csv", usecols=["grid_id"])
    if len(data) != 1597 or set(data.grid_id) != set(baseline.grid_id):
        raise ValueError("CSV must cover exactly the baseline's 1,597 grid IDs")
    values = data[field].to_numpy(dtype=float)
    if not np.isfinite(values).all() or np.ptp(values) == 0:
        raise ValueError("Indicator values must be finite and nonconstant")
    registered = {key: value for key, value in manifest.items() if key != "source_sha256"}
    registered["source_sha256"] = sha256(path)
    return path, registered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    path, registered = validate_manifest(manifest)
    REGISTRY.mkdir(parents=True, exist_ok=True)
    target = REGISTRY / f"{registered['id']}.json"
    if target.exists():
        raise ValueError(f"Indicator already registered: {registered['id']}")
    target.write_text(json.dumps(registered, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(json.dumps({"registered": registered["id"],
                      "source_csv": str(path), "manifest": str(target),
                      "source_sha256": registered["source_sha256"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
