"""Convert a local structured raw dataset into one 1,597-grid indicator.

Supported inputs: CSV, TSV, XLSX, GeoJSON, and GeoPackage. Supported mappings:
grid_id tables, point count/sum/mean, and polygon area-weighted mean,
prorated sum, or union coverage share. The mapping is explicit and audited;
unsupported source structures fail rather than producing invented values.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio

from run_scenario import ROOT, sha256, source_path


from access_program import analyse_points, parse_access

GRID_FILE = ROOT / "output/sg_grid/grid_demand_2020_95pct.gpkg"
BASELINE_FILE = ROOT / "output/scenarios/baseline_v1/grid_results_primary_1597.csv"
ALLOWED_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".geojson", ".gpkg"}
OPERATIONS = {
    "grid_sum", "grid_mean", "point_count", "point_sum", "point_mean",
    "polygon_area_weighted_mean", "polygon_prorated_sum",
    "polygon_coverage_share", "access_program",
}
POINT_OPERATIONS = {"point_count", "point_sum", "point_mean"}
POLYGON_OPERATIONS = {
    "polygon_area_weighted_mean", "polygon_prorated_sum",
    "polygon_coverage_share",
}
VALUE_OPERATIONS = OPERATIONS - {"point_count", "polygon_coverage_share", "access_program"}


def load_grids() -> gpd.GeoDataFrame:
    ids = pd.read_csv(BASELINE_FILE, usecols=["grid_id"]).grid_id
    grids = gpd.read_file(GRID_FILE)[["grid_id", "geometry"]]
    if (len(ids) != 1597 or ids.duplicated().any() or
            grids.crs is None or grids.crs.to_epsg() != 3414 or
            grids.grid_id.duplicated().any() or
            not set(ids) <= set(grids.grid_id)):
        raise ValueError("Study-grid identity or CRS check failed")
    grids = grids.set_index("grid_id").loc[ids].reset_index()
    if (grids.geometry.isna().any() or grids.geometry.is_empty.any() or
            not grids.geometry.is_valid.all()):
        raise ValueError("Study-grid geometry is missing, empty or invalid")
    return grids


def checked_source(relative: str) -> Path:
    path = source_path(relative)
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported raw format: {path.suffix}")
    if path.stat().st_size > 250_000_000:
        raise ValueError("Raw file exceeds 250 MB; stage a scoped extract")
    return path


def read_source(path: Path, layer: str | None = None,
                sheet: str | None = None) -> pd.DataFrame | gpd.GeoDataFrame:
    suffix = path.suffix.lower()
    if suffix == ".gpkg":
        layers = [str(item[0]) for item in pyogrio.list_layers(path)]
        if layer is None and len(layers) != 1:
            raise ValueError(f"GeoPackage layer required; available: {layers}")
        if layer is not None and layer not in layers:
            raise ValueError(f"Unknown GeoPackage layer: {layer}")
        return gpd.read_file(path, layer=layer or layers[0])
    if suffix == ".geojson":
        if layer:
            raise ValueError("GeoJSON does not accept a layer name")
        return gpd.read_file(path)
    if layer:
        raise ValueError("Layer is only valid for GeoPackage")
    if suffix == ".xlsx":
        if sheet is None:
            sheets = pd.ExcelFile(path).sheet_names
            if len(sheets) != 1:
                raise ValueError(f"Excel sheet required; available: {sheets}")
            sheet = sheets[0]
        return pd.read_excel(path, sheet_name=sheet)
    if sheet:
        raise ValueError("Sheet is only valid for XLSX")
    return pd.read_csv(path, sep="\t" if suffix == ".tsv" else ",")


def profile(path: Path, layer: str | None = None,
            sheet: str | None = None) -> dict:
    frame = read_source(path, layer, sheet)
    geometry_type = None
    crs = None
    if isinstance(frame, gpd.GeoDataFrame):
        geometry_type = sorted(frame.geom_type.dropna().unique().tolist())
        crs = str(frame.crs) if frame.crs is not None else None
    return {
        "source_file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256(path),
        "format": path.suffix.lower(), "row_count": len(frame),
        "columns": [{"name": str(name), "dtype": str(dtype)}
                    for name, dtype in frame.dtypes.items() if name != "geometry"],
        "geometry_types": geometry_type, "crs": crs,
        "layer": layer, "sheet": sheet,
    }


def validate_spec(spec: dict, source_profile: dict) -> None:
    required = {"id", "side", "source_file", "source", "source_year",
                "description", "unit", "direction", "factor", "operation",
                "value_field", "x_field", "y_field", "source_crs", "layer",
                "sheet", "missing_policy", "where"}
    if spec.get("operation") == "access_program":
        required.add("analysis_code")
        parse_access(spec.get("analysis_code"))
        if spec.get("side") != "supply" or spec.get("factor") != "destinations" or spec.get("direction") != "higher_is_better":
            raise ValueError("可达目的地指标应归入供给侧目的地类别，数值越高可达性越好")
    if set(spec) != required:
        raise ValueError(f"Ingestion spec fields must be exactly: {sorted(required)}")
    if not isinstance(spec["id"], str) or not re.fullmatch(r"[a-z][a-z0-9_]*", spec["id"]):
        raise ValueError("Invalid indicator ID")
    if spec["side"] not in ("demand", "supply") or spec["operation"] not in OPERATIONS:
        raise ValueError("Unsupported side or operation")
    if spec["side"] == "demand":
        if spec["direction"] not in ("higher_is_higher_demand",
                                      "lower_is_higher_demand") or spec["factor"] is not None:
            raise ValueError("Invalid demand direction or factor")
    elif spec["direction"] not in ("higher_is_better", "lower_is_better") or spec["factor"] not in (
            "network", "destinations", "frequency", "flexibility_time"):
        raise ValueError("Invalid supply direction or factor")
    for key in ("source", "source_year", "description", "unit"):
        if not isinstance(spec[key], str) or not spec[key].strip():
            raise ValueError(f"Missing provenance field: {key}")
    if spec["source_file"] != source_profile["source_file"]:
        raise ValueError("Spec source differs from profiled source")
    if spec["layer"] != source_profile["layer"] or spec["sheet"] != source_profile["sheet"]:
        raise ValueError("Spec layer/sheet differs from profiled source")
    columns = {item["name"] for item in source_profile["columns"]}
    if spec["operation"] in VALUE_OPERATIONS and spec["value_field"] not in columns:
        raise ValueError("Value field is missing from source")
    if spec["operation"] not in VALUE_OPERATIONS and spec["value_field"] is not None:
        raise ValueError("This operation does not use a value field")
    if spec["operation"].startswith("grid_") and "grid_id" not in columns:
        raise ValueError("Grid operation requires grid_id column")
    if spec["missing_policy"] not in ("error", "zero"):
        raise ValueError("Missing policy must be error or zero")
    if not isinstance(spec["where"], list) or len(spec["where"]) > 10:
        raise ValueError("where must be a short filter list")
    for item in spec["where"]:
        if (not isinstance(item, dict) or set(item) != {"field", "operator", "value"}
                or item["field"] not in columns or item["operator"] not in
                ("eq", "ne", "gt", "gte", "lt", "lte")):
            raise ValueError("Invalid filter")
        if not isinstance(item["value"], (str, int, float, bool)):
            raise ValueError("Filter value must be scalar")
    if spec["operation"] in POINT_OPERATIONS | POLYGON_OPERATIONS | {"access_program"}:
        if source_profile["geometry_types"] is None:
            if spec["operation"] in POLYGON_OPERATIONS:
                raise ValueError("Polygon operation requires vector geometry")
            if not all(spec[key] in columns for key in ("x_field", "y_field")):
                raise ValueError("Tabular points require x/y columns")
            if not isinstance(spec["source_crs"], str) or not spec["source_crs"]:
                raise ValueError("Tabular points require an explicit source CRS")
        else:
            expected = {"Point", "MultiPoint"} if spec["operation"] in POINT_OPERATIONS else {
                "Polygon", "MultiPolygon"}
            if spec["operation"] == "access_program":
                expected = {"Point"}
            if not set(source_profile["geometry_types"]) <= expected:
                raise ValueError("Source geometry does not match operation")
            if not source_profile["crs"]:
                raise ValueError("Vector source has no CRS")


def apply_filters(frame: pd.DataFrame, filters: list[dict]) -> pd.DataFrame:
    for item in filters:
        series = frame[item["field"]]
        value = item["value"]
        if item["operator"] in ("gt", "gte", "lt", "lte"):
            series = pd.to_numeric(series, errors="raise")
            value = float(value)
        mask = {
            "eq": lambda: series.eq(value), "ne": lambda: series.ne(value),
            "gt": lambda: series.gt(value), "gte": lambda: series.ge(value),
            "lt": lambda: series.lt(value), "lte": lambda: series.le(value),
        }[item["operator"]]()
        frame = frame.loc[mask.fillna(False)].copy()
    return frame


def make_geometry(frame: pd.DataFrame | gpd.GeoDataFrame,
                  spec: dict) -> gpd.GeoDataFrame:
    if isinstance(frame, gpd.GeoDataFrame):
        if frame.crs is None:
            raise ValueError("Source CRS is missing")
        spatial = frame
    else:
        x = pd.to_numeric(frame[spec["x_field"]], errors="raise")
        y = pd.to_numeric(frame[spec["y_field"]], errors="raise")
        if not np.isfinite(x).all() or not np.isfinite(y).all():
            raise ValueError("Nonfinite coordinates")
        spatial = gpd.GeoDataFrame(frame.copy(), geometry=gpd.points_from_xy(x, y),
                                   crs=spec["source_crs"])
    if spatial.geometry.isna().any() or spatial.geometry.is_empty.any() or not spatial.geometry.is_valid.all():
        raise ValueError("Source geometry is missing, empty or invalid")
    return spatial.to_crs(3414)


def numeric_values(frame: pd.DataFrame, field: str) -> pd.Series:
    values = pd.to_numeric(frame[field], errors="raise")
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError(f"Nonfinite values in {field}")
    return values.astype(float)


def aggregate(frame: pd.DataFrame | gpd.GeoDataFrame, spec: dict,
              grids: gpd.GeoDataFrame) -> tuple[pd.Series, dict]:
    op, field = spec["operation"], spec["value_field"]
    grid_ids = pd.Index(grids.grid_id, name="grid_id")
    audit = {"source_rows_after_filter": len(frame), "matched_source_rows": None,
             "unmatched_source_rows": None, "boundary_multiple_matches": 0}
    if op.startswith("grid_"):
        values = numeric_values(frame, field)
        table = pd.DataFrame({"grid_id": frame.grid_id.astype(str), "value": values})
        matching = table.grid_id.isin(grid_ids)
        audit["matched_source_rows"] = int(matching.sum())
        audit["unmatched_source_rows"] = int((~matching).sum())
        grouped = table.loc[matching].groupby("grid_id").value.agg(
            "sum" if op == "grid_sum" else "mean")
    elif op == "access_program":
        grouped, access_audit = analyse_points(make_geometry(frame, spec), grid_ids, spec["analysis_code"])
        audit.update(access_audit)
    elif op in POINT_OPERATIONS:
        spatial = make_geometry(frame, spec)
        spatial = spatial.reset_index(drop=True)
        spatial["_raw_row_id"] = np.arange(len(spatial))
        columns = ["_raw_row_id", "geometry"]
        if field:
            spatial["_value"] = numeric_values(spatial, field)
            columns.append("_value")
        joined = gpd.sjoin(spatial[columns], grids[["grid_id", "geometry"]],
                           how="left", predicate="intersects")
        multiple = joined.loc[joined.grid_id.notna()].groupby("_raw_row_id").size()
        audit["boundary_multiple_matches"] = int((multiple > 1).sum())
        matched = joined.loc[joined.grid_id.notna()].sort_values(
            ["_raw_row_id", "grid_id"]).drop_duplicates("_raw_row_id")
        audit["matched_source_rows"] = len(matched)
        audit["unmatched_source_rows"] = len(spatial) - len(matched)
        if op == "point_count":
            grouped = matched.groupby("grid_id").size()
        else:
            grouped = matched.groupby("grid_id")._value.agg(
                "sum" if op == "point_sum" else "mean")
        audit["source_crs"] = str(frame.crs) if isinstance(frame, gpd.GeoDataFrame) else spec["source_crs"]
    else:
        spatial = make_geometry(frame, spec)
        spatial = spatial.reset_index(drop=True)
        if spatial.geometry.area.le(0).any():
            raise ValueError("Polygon source has zero-area geometry")
        audit["source_crs"] = str(frame.crs)
        if op == "polygon_coverage_share":
            union = spatial.geometry.union_all()
            shares = grids.geometry.intersection(union).area / grids.geometry.area
            grouped = pd.Series(shares.to_numpy(), index=grid_ids)
            audit["matched_source_rows"] = None
            audit["unmatched_source_rows"] = None
        else:
            spatial["_raw_row_id"] = np.arange(len(spatial))
            spatial["_source_area"] = spatial.geometry.area
            spatial["_value"] = numeric_values(spatial, field)
            intersections = gpd.overlay(spatial[["_raw_row_id", "_source_area", "_value", "geometry"]],
                grids[["grid_id", "geometry"]], how="intersection", keep_geom_type=True)
            intersections["_overlap_area"] = intersections.geometry.area
            intersections = intersections.loc[intersections._overlap_area.gt(0)]
            audit["matched_source_rows"] = int(intersections._raw_row_id.nunique())
            audit["unmatched_source_rows"] = len(spatial) - audit["matched_source_rows"]
            if op == "polygon_prorated_sum":
                contribution = intersections._value * (
                    intersections._overlap_area / intersections._source_area)
                grouped = contribution.groupby(intersections.grid_id).sum()
            else:
                numerator = (intersections._value * intersections._overlap_area).groupby(
                    intersections.grid_id).sum()
                denominator = intersections._overlap_area.groupby(intersections.grid_id).sum()
                grouped = numerator / denominator
    values = grouped.reindex(grid_ids)
    missing = int(values.isna().sum())
    audit["grids_without_source_observation"] = missing
    if missing:
        if spec["missing_policy"] == "error":
            raise ValueError(f"{missing} grids lack a source observation")
        values = values.fillna(0)
    if not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError("Derived grid indicator contains nonfinite values")
    return values.astype(float), audit


def ingest(spec: dict, out_dir: Path,
           expected_source_sha256: str | None = None) -> dict:
    path = checked_source(spec["source_file"])
    source_profile = profile(path, spec["layer"], spec["sheet"])
    if (expected_source_sha256 is not None and
            expected_source_sha256 != source_profile["source_sha256"]):
        raise ValueError("Raw source changed after profiling")
    validate_spec(spec, source_profile)
    frame = read_source(path, spec["layer"], spec["sheet"])
    frame = apply_filters(frame, spec["where"])
    if frame.empty:
        raise ValueError("Filters removed all source rows")
    grids = load_grids()
    values, aggregation_audit = aggregate(frame, spec, grids)
    field = spec["id"] + "_value"
    output = pd.DataFrame({"grid_id": grids.grid_id, field: values.to_numpy()})
    if len(output) != 1597 or output.grid_id.duplicated().any():
        raise ValueError("Derived grid output identity check failed")
    out_dir = out_dir.resolve()
    if not out_dir.is_relative_to(ROOT):
        raise ValueError("Output must stay inside the project")
    out_dir.mkdir(parents=True, exist_ok=False)
    csv_path = out_dir / f"{spec['id']}_1597.csv"
    output.to_csv(csv_path, index=False, encoding="utf-8-sig")
    reopened = pd.read_csv(csv_path)
    if len(reopened) != 1597 or set(reopened.grid_id) != set(grids.grid_id):
        raise ValueError("Derived output failed reopen check")
    manifest = {
        "id": spec["id"], "side": spec["side"], "field": field,
        "source_csv": str(csv_path.relative_to(ROOT)).replace("\\", "/"),
        "source_year": spec["source_year"], "source": spec["source"],
        "description": spec["description"], "unit": spec["unit"],
        "direction": spec["direction"],
        "method": f"{spec['operation']} from {spec['source_file']}; filters={spec['where']}",
    }
    if spec["operation"] == "access_program":
        manifest["method"] += " | " + spec["analysis_code"]
    if spec["side"] == "supply":
        manifest["factor"] = spec["factor"]
    manifest_path = out_dir / "indicator_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    audit = {"status": "derived", "source_profile": source_profile,
             "spec": spec, "grid_source_sha256": sha256(GRID_FILE),
             "baseline_grid_ids_sha256": sha256(BASELINE_FILE),
             "aggregation": aggregation_audit, "output_csv": str(csv_path),
             "output_sha256": sha256(csv_path),
             "value_summary": {"min": float(values.min()), "max": float(values.max()),
                               "mean": float(values.mean()),
                               "zero_grids": int(values.eq(0).sum())}}
    (out_dir / "ingestion_audit.json").write_text(json.dumps(audit,
        ensure_ascii=False, indent=2), encoding="utf-8")
    return {"csv": str(csv_path), "manifest": str(manifest_path),
            "audit": str(out_dir / "ingestion_audit.json"),
            "source_rows": len(frame), "grid_rows": len(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--profile-only", action="store_true")
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    path = checked_source(spec["source_file"])
    if args.profile_only:
        print(json.dumps(profile(path, spec.get("layer"), spec.get("sheet")),
                         ensure_ascii=False, indent=2))
        return
    out_dir = args.out_dir or ROOT / "output/raw_indicators" / spec["id"]
    print(json.dumps(ingest(spec, out_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
