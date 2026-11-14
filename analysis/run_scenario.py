"""Score prepared grid indicators using a validated research scenario config.

The baseline config reproduces the published 1,597-grid result as the sole
primary result.
This runner starts from prepared grid indicators; it does not update raw data.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import re
import statistics
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config/indicators"
BASE_DEMAND_FIELDS = {
    "n_low_income_households_lt3000", "n_non_car_commuters",
    "n_unemployed_residents", "n_low_education_residents_15plus",
    "n_youth_residents_10_19", "n_older_residents_65plus",
    "n_one_person_households", "n_mobility_difficulty_residents_5plus",
    "n_public_transit_users_work_school_sum",
}
FACTORS = ("network", "destinations", "frequency", "flexibility_time")
DEMAND_LABELS = {1: "Q4_low", 2: "Q3_moderately_low",
                 3: "Q2_moderately_high", 4: "Q1_high"}
SUPPLY_LABELS = {1: "1_no_low_supply_flags", 2: "2_lower_deficit",
                 3: "3_moderate_deficit", 4: "4_higher_deficit"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f"Input is not a project file: {relative}")
    return path


def load_extensions(config: dict, demand: pd.DataFrame, supply: pd.DataFrame,
                    dictionary: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    """Join registered 1,597-grid indicators and return their directions/audit."""
    directions = {}
    audit = {}
    for indicator_id in config.get("extensions", []):
        if not isinstance(indicator_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", indicator_id):
            raise ValueError("Invalid extension ID")
        manifest_path = REGISTRY / f"{indicator_id}.json"
        if not manifest_path.is_file():
            raise ValueError(f"Unregistered indicator: {indicator_id}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["id"] != indicator_id or manifest["side"] not in ("demand", "supply"):
            raise ValueError(f"Invalid indicator manifest: {indicator_id}")
        if indicator_id in {item["id"] for item in dictionary["indicators"]}:
            raise ValueError(f"Repeated supply indicator ID: {indicator_id}")
        field = manifest["field"]
        if not isinstance(field, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", field):
            raise ValueError(f"Invalid indicator field: {indicator_id}")
        path = source_path(manifest["source_csv"])
        if sha256(path) != manifest["source_sha256"]:
            raise ValueError(f"Indicator source changed: {indicator_id}")
        data = pd.read_csv(path)
        if field not in data or "grid_id" not in data or data.grid_id.duplicated().any():
            raise ValueError(f"Invalid grid indicator CSV: {indicator_id}")
        if len(data) != 1597 or set(data.grid_id) != set(demand.grid_id):
            raise ValueError(f"Extension must match all 1,597 grid IDs: {indicator_id}")
        if not np.isfinite(data[field].to_numpy(dtype=float)).all():
            raise ValueError(f"Nonfinite extension values: {indicator_id}")
        if manifest["side"] == "demand":
            if field in demand or field in directions:
                raise ValueError(f"Repeated demand field: {field}")
            if manifest["direction"] not in ("higher_is_higher_demand",
                                              "lower_is_higher_demand"):
                raise ValueError(f"Invalid demand direction: {indicator_id}")
            demand = demand.merge(data[["grid_id", field]], on="grid_id", validate="one_to_one")
            directions[field] = manifest["direction"]
        else:
            if field in supply or manifest["direction"] not in ("higher_is_better",
                                                               "lower_is_better"):
                raise ValueError(f"Invalid supply field or direction: {indicator_id}")
            if manifest["factor"] not in FACTORS:
                raise ValueError(f"Invalid supply factor: {indicator_id}")
            supply = supply.merge(data[["grid_id", field]], on="grid_id", validate="one_to_one")
            dictionary["indicators"].append({
                "id": indicator_id, "factor": manifest["factor"],
                "unit": manifest["unit"], "direction": manifest["direction"],
                "output_field": field,
            })
        audit[indicator_id] = {"manifest_sha256": sha256(manifest_path),
                               "source_sha256": sha256(path),
                               "side": manifest["side"], "field": field,
                               "source_year": manifest["source_year"],
                               "method": manifest["method"]}
    return demand, supply, directions, audit


def validate(config: dict, dictionary: dict, demand: pd.DataFrame,
             supply: pd.DataFrame, demand_directions: dict) -> None:
    if not config["id"].replace("_", "").replace("-", "").isalnum():
        raise ValueError("Scenario id must contain letters, numbers, _ or -")
    if config["universe"] != {"name": "primary_1597",
                              "filter": "positive_estimated_population"}:
        raise ValueError("The only supported universe is primary_1597")
    if config["demand"]["method"] != "weighted_population_z_score_of_estimated_counts":
        raise ValueError("Unknown demand method")
    if config["demand"]["higher_score_means"] != "higher_demand":
        raise ValueError("Unknown demand score direction")
    if config["supply"]["method"] != "weighted_low_supply_indicator_flags":
        raise ValueError("Unknown supply method")
    if config["supply"]["tie_rule"] != "whole_value_group_nearest_target":
        raise ValueError("Unknown low-supply tie rule")
    if config["supply"]["classes"] != "zero_then_three_positive_groups_minimum_size_imbalance":
        raise ValueError("Unknown supply class rule")
    if config["demand"]["quartiles"] != "linear_25_50_75_percentiles_with_ties_kept_together":
        raise ValueError("Unknown demand class rule")
    if len(demand) != 1597 or len(supply) != 1597:
        raise ValueError("Scoring inputs must contain 1,597 grids")
    if demand.grid_id.duplicated().any() or supply.grid_id.duplicated().any():
        raise ValueError("Duplicate grid ID")
    if set(demand.grid_id) != set(supply.grid_id):
        raise ValueError("Demand and supply grid IDs differ")
    demand_fields = list(config["demand"]["weights"])
    supply_items = dictionary["indicators"]
    supply_ids = [item["id"] for item in supply_items]
    if (not BASE_DEMAND_FIELDS <= set(demand_fields) or
            set(demand_fields) != BASE_DEMAND_FIELDS | set(demand_directions) or
            not set(demand_fields) <= set(demand)):
        raise ValueError("Demand weights must cover baseline and registered indicators")
    if len(supply_items) < 11 or set(config["supply"]["weights"]) != set(supply_ids):
        raise ValueError("Supply weights must cover baseline and registered indicators")
    if set(item["factor"] for item in supply_items) != set(FACTORS):
        raise ValueError("Unexpected supply factors")
    if any(item["direction"] not in ("higher_is_better", "lower_is_better") or
           item["output_field"] not in supply for item in supply_items):
        raise ValueError("Supply field or direction invalid")
    for side in ("demand", "supply"):
        weights = list(config[side]["weights"].values())
        if any(not isinstance(w, (int, float)) or not math.isfinite(w) or w < 0
               for w in weights) or not any(w > 0 for w in weights):
            raise ValueError(f"{side} weights must be finite, nonnegative, and nonzero")
    share = config["supply"]["low_supply_share"]
    if not isinstance(share, (int, float)) or not 0 < share < 1:
        raise ValueError("Low-supply share must be between zero and one")
    rule = config["candidate_rule"]
    if any(rule[k] not in (1, 2, 3, 4) for k in
           ("minimum_demand_level", "minimum_supply_deficit_level")):
        raise ValueError("Candidate level must be 1-4")
    for frame, fields in ((demand, demand_fields),
                          (supply, [item["output_field"] for item in supply_items])):
        if not np.isfinite(frame[fields].to_numpy(dtype=float)).all():
            raise ValueError("Indicator values must be finite")


def quartile_cutpoints(scores: list[float]) -> list[float]:
    values = sorted(scores)
    def pct(q: float) -> float:
        position = (len(values) - 1) * q
        lower, upper = math.floor(position), math.ceil(position)
        return values[lower] + (position - lower) * (values[upper] - values[lower])
    return [pct(q) for q in (.25, .5, .75)]


def supply_classes(total: pd.Series) -> tuple[pd.Series, dict]:
    groups = total[total > 0].value_counts().sort_index()
    values, counts = groups.index.to_list(), groups.to_numpy()
    if len(values) < 3:
        raise ValueError("At least three positive supply scores are required")
    prefix = np.r_[0, np.cumsum(counts)]
    target = int(prefix[-1]) / 3
    best = None
    for first, second in itertools.combinations(range(1, len(values)), 2):
        sizes = (int(prefix[first]), int(prefix[second] - prefix[first]),
                 int(prefix[-1] - prefix[second]))
        key = (sum((size - target) ** 2 for size in sizes), (first, second))
        if best is None or key < best[0]:
            best = (key, first, second, sizes)
    _, first, second, sizes = best
    bounds = [float(values[first - 1]), float(values[second - 1])]
    classes = pd.Series(np.select(
        [total.eq(0), total.le(bounds[0]), total.le(bounds[1])],
        [1, 2, 3], default=4), index=total.index)
    return classes, {"positive_score_upper_bounds": bounds,
                     "class_counts": [int(total.eq(0).sum()), *sizes]}


def score_universe(name: str, demand: pd.DataFrame, supply: pd.DataFrame,
                   config: dict, indicators: list[dict],
                   demand_directions: dict) -> tuple[pd.DataFrame, dict]:
    weights = config["demand"]["weights"]
    result = demand[["grid_id", "dominant_pa", "estimated_resident_population"]].copy()
    score = np.zeros(len(demand), dtype=float)
    demand_parameters = {}
    for field, weight in weights.items():
        values = demand[field].astype(float).tolist()
        mean, sd = statistics.fmean(values), statistics.pstdev(values)
        if sd <= 0:
            raise ValueError(f"Constant demand indicator: {field}")
        z = (demand[field].to_numpy(dtype=float) - mean) / sd
        result["z_" + field.removeprefix("n_")] = z
        sign = -1 if demand_directions.get(field) == "lower_is_higher_demand" else 1
        score += sign * weight * z
        demand_parameters[field] = {"mean": mean, "population_sd": sd}
    cutpoints = quartile_cutpoints(score.tolist())
    result["demand_score"] = score
    result["demand_level_1_4"] = np.select(
        [score <= cutpoints[0], score <= cutpoints[1], score <= cutpoints[2]],
        [1, 2, 3], default=4)
    result["demand_class"] = result.demand_level_1_4.map(DEMAND_LABELS)

    aligned = supply.set_index("grid_id").loc[demand.grid_id].reset_index()
    factor_scores = {factor: np.zeros(len(result), dtype=float) for factor in FACTORS}
    threshold_audit = {}
    share = config["supply"]["low_supply_share"]
    for item in indicators:
        field, indicator_id = item["output_field"], item["id"]
        groups = aligned[field].value_counts().sort_index()
        cumulative = groups.cumsum().to_numpy()
        if item["direction"] == "higher_is_better":
            cutoff_pos = int(np.argmin(np.abs(cumulative - len(aligned) * share)))
        else:
            top_cumulative = groups.iloc[::-1].cumsum().to_numpy()
            cutoff_pos = len(groups) - 1 - int(np.argmin(
                np.abs(top_cumulative - len(aligned) * share)))
        cutoff = groups.index[cutoff_pos]
        flagged = (aligned[field] <= cutoff if item["direction"] == "higher_is_better"
                   else aligned[field] >= cutoff)
        flag = flagged.astype(np.int8).to_numpy()
        result["cpta_flag_" + indicator_id] = flag
        factor_scores[item["factor"]] += config["supply"]["weights"][indicator_id] * flag
        threshold_audit[indicator_id] = {"cutoff_inclusive": float(cutoff),
            "flagged_count": int(flag.sum()), "ties_at_cutoff": int(groups.iloc[cutoff_pos])}
    for factor in FACTORS:
        result["supply_factor_" + factor] = factor_scores[factor]
    total = sum(factor_scores.values())
    result["supply_deficit_score"] = total
    result["supply_deficit_level_1_4"], supply_class_audit = supply_classes(
        result.supply_deficit_score)
    result["supply_class"] = result.supply_deficit_level_1_4.map(SUPPLY_LABELS)
    rule = config["candidate_rule"]
    result["candidate_transit_desert"] = (
        result.demand_level_1_4.ge(rule["minimum_demand_level"]) &
        result.supply_deficit_level_1_4.ge(rule["minimum_supply_deficit_level"])
    ).astype(np.int8)
    matrix = pd.crosstab(result.demand_level_1_4,
                         result.supply_deficit_level_1_4).reindex(
                             index=range(1, 5), columns=range(1, 5), fill_value=0)
    audit = {"universe": name, "grid_count": len(result),
             "candidate_count": int(result.candidate_transit_desert.sum()),
             "demand_cutpoints": cutpoints, "demand_z_parameters": demand_parameters,
             "supply_thresholds": threshold_audit, "supply_classes": supply_class_audit,
             "cross_tab": {str(d): {str(s): int(matrix.loc[d, s]) for s in range(1, 5)}
                           for d in range(1, 5)}}
    return result, audit


def verify_baseline(result: pd.DataFrame, config: dict) -> dict:
    if config["id"] != "baseline_v1" or config.get("extensions") or any(
            weight != 1 for side in ("demand", "supply")
            for weight in config[side]["weights"].values()):
        return {"status": "not_baseline_config"}
    actual = result.set_index("grid_id")
    demand = pd.read_csv(ROOT /
        "output/sg_grid/grid_demand_count_score_2020_95pct_estimated.csv").set_index(
            "grid_id").loc[actual.index]
    supply = pd.read_csv(ROOT /
        "output/supply/grid_cpta_supply_1597_sensitivity.csv").set_index(
            "grid_id").loc[actual.index]
    reference_candidates = set(pd.read_csv(ROOT /
        "output/comparison/candidate_transit_desert_grids_1597_sensitivity.csv").grid_id)
    actual_candidates = set(actual.index[actual.candidate_transit_desert.eq(1)])
    max_demand_difference = float((actual.demand_score - demand.score_residential_only).abs().max())
    checks = {
        "grid_ids": len(actual) == 1597 and set(actual.index) == set(supply.index),
        "demand_score_within_1e-9": max_demand_difference <= 1e-9,
        "demand_classes": actual.demand_class.equals(demand.quartile_residential_only),
        "supply_scores": np.allclose(actual.supply_deficit_score,
                                     supply.cpta_total_0_11, rtol=0, atol=1e-12),
        "supply_classes": actual.supply_class.equals(supply.cpta_supply_level_1_4),
        "candidate_ids": actual_candidates == reference_candidates,
    }
    return {"status": "matched" if all(checks.values()) else "mismatch",
            "checks": checks, "max_demand_score_difference": max_demand_difference,
            "candidate_count": len(actual_candidates)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", nargs="?", type=Path,
                        default=ROOT / "config/scenarios/baseline_v1.json")
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    inputs = {key: source_path(relative) for key, relative in config["inputs"].items()}
    demand = pd.read_csv(inputs["demand_counts"])
    supply = pd.read_csv(inputs["supply_indicators"])
    dictionary = json.loads(inputs["supply_dictionary"].read_text(encoding="utf-8"))
    if (len(demand) != 1959 or len(supply) != 1959 or
            demand.grid_id.duplicated().any() or supply.grid_id.duplicated().any() or
            set(demand.grid_id) != set(supply.grid_id)):
        raise ValueError("Prepared base inputs must have the same 1,959 grid IDs")
    scoped_demand = demand.loc[
        demand.estimated_resident_population.gt(0)].reset_index(drop=True)
    scoped_supply = supply.set_index("grid_id").loc[scoped_demand.grid_id].reset_index()
    scoped_demand, scoped_supply, demand_directions, extension_audit = load_extensions(
        config, scoped_demand, scoped_supply, dictionary)
    validate(config, dictionary, scoped_demand, scoped_supply, demand_directions)
    out_dir = (args.out_dir or ROOT / "output/scenarios" / config["id"]).resolve()
    if not out_dir.is_relative_to(ROOT):
        raise ValueError("Scenario output must be inside the project")
    out_dir.mkdir(parents=True, exist_ok=False)
    result, result_audit = score_universe("primary_1597", scoped_demand,
        scoped_supply, config, dictionary["indicators"], demand_directions)
    result.to_csv(out_dir / "grid_results_primary_1597.csv", index=False,
                  encoding="utf-8-sig")
    verification = verify_baseline(result, config)
    audit = {"scenario_id": config["id"], "config_sha256": sha256(config_path),
             "input_sha256": {key: sha256(path) for key, path in inputs.items()},
             "universe": result_audit, "extensions": extension_audit,
             "baseline_verification": verification,
             "limitations": [
                 "Demand grid counts are allocated estimates, not observed grid census counts.",
                 "Supply includes modelled travel times and expected rather than observed bus arrivals.",
                 "Positive estimated population is a model-based scope criterion.",
             ]}
    (out_dir / "scenario_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out_dir": str(out_dir),
                      "candidate_count": result_audit["candidate_count"],
                      "baseline_verification": verification["status"]},
                     ensure_ascii=False, indent=2))
    return 0 if verification["status"] != "mismatch" else 1


if __name__ == "__main__":
    raise SystemExit(main())
