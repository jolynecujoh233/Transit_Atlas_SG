"""Compare one scenario with the 1,597-grid unweighted baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "output/scenarios/baseline_v1/grid_results_primary_1597.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario_dir", type=Path)
    args = parser.parse_args()
    scenario_dir = args.scenario_dir.resolve()
    if not scenario_dir.is_relative_to(ROOT / "output/scenarios"):
        raise ValueError("Scenario directory must be inside output/scenarios")
    scenario_path = scenario_dir / "grid_results_primary_1597.csv"
    baseline = pd.read_csv(BASELINE)
    scenario = pd.read_csv(scenario_path)
    if (len(baseline) != 1597 or len(scenario) != 1597 or
            baseline.grid_id.duplicated().any() or scenario.grid_id.duplicated().any() or
            set(baseline.grid_id) != set(scenario.grid_id)):
        raise ValueError("Comparison requires the same 1,597 unique grid IDs")

    fields = ["grid_id", "dominant_pa", "estimated_resident_population",
              "demand_score", "demand_level_1_4", "supply_deficit_score",
              "supply_deficit_level_1_4", "candidate_transit_desert"]
    joined = baseline[fields].merge(
        scenario[fields].drop(columns=["dominant_pa", "estimated_resident_population"]),
        on="grid_id", validate="one_to_one", suffixes=("_baseline", "_scenario"),
    )
    baseline_selected = joined.candidate_transit_desert_baseline.eq(1)
    scenario_selected = joined.candidate_transit_desert_scenario.eq(1)
    joined["candidate_change"] = "neither"
    joined.loc[baseline_selected & scenario_selected, "candidate_change"] = "retained"
    joined.loc[~baseline_selected & scenario_selected, "candidate_change"] = "entered"
    joined.loc[baseline_selected & ~scenario_selected, "candidate_change"] = "exited"
    joined.to_csv(scenario_dir / "baseline_comparison.csv", index=False,
                  encoding="utf-8-sig")
    changes_by_area = joined.loc[joined.candidate_change.isin(["entered", "exited"])]
    area = pd.crosstab(changes_by_area.dominant_pa,
                       changes_by_area.candidate_change).reindex(
                           columns=["entered", "exited"], fill_value=0)
    area["net_change"] = area.entered - area.exited
    area.sort_values(["entered", "net_change"], ascending=False).to_csv(
        scenario_dir / "candidate_changes_by_planning_area.csv",
        encoding="utf-8-sig")
    counts = joined.candidate_change.value_counts()
    audit = {
        "grid_count": len(joined),
        "baseline_candidates": int(baseline_selected.sum()),
        "scenario_candidates": int(scenario_selected.sum()),
        "retained": int(counts.get("retained", 0)),
        "entered": int(counts.get("entered", 0)),
        "exited": int(counts.get("exited", 0)),
        "neither": int(counts.get("neither", 0)),
        "demand_level_changed": int((joined.demand_level_1_4_baseline !=
                                     joined.demand_level_1_4_scenario).sum()),
        "supply_level_changed": int((joined.supply_deficit_level_1_4_baseline !=
                                     joined.supply_deficit_level_1_4_scenario).sum()),
        "entered_demand_level_changed": int((
            joined.candidate_change.eq("entered") &
            joined.demand_level_1_4_baseline.ne(joined.demand_level_1_4_scenario)).sum()),
        "entered_supply_level_changed": int((
            joined.candidate_change.eq("entered") &
            joined.supply_deficit_level_1_4_baseline.ne(
                joined.supply_deficit_level_1_4_scenario)).sum()),
        "note": "Weighted and unweighted score scales differ; compare classes and candidate membership, not raw score differences.",
    }
    (scenario_dir / "baseline_comparison_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
