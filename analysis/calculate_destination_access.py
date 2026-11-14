"""Calculate five 09:00 weekday destination indicators from one GTFS model.

The GTFS release is a frequency-based, third-party LTA-derived proxy. This
script expands its weekday frequency templates into a 09:00–10:00 connection
scan. Walking uses projected straight-line distance times a detour factor;
there is no pedestrian street graph. Results are model estimates, not observed
journey times or exact public-transport timetable outcomes.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
GTFS = ROOT / "data/supply/singapore_gtfs_v2026-07-12.zip"
ORIGINS = ROOT / "output/sg_grid/grid_demand_2020_95pct.csv"
JOBS = ROOT / "output/supply/workplace_income_land_proxy_400m.csv"
CLINICS = ROOT / "output/supply/chas_clinics_grid.csv"
CLINIC_GEOJSON = ROOT / "data/supply/d_548c33ea2d99e29ec63a7cc9edcccedc_2026-11-07.geojson"
SUPERMARKETS = ROOT / "output/supply/sfa_supermarkets_geocoded_2026-11-08.csv"
OUT = ROOT / "output/supply"
PREVIOUS = OUT / "grid_supply_three_ready_95pct.csv"

DEPART = 9 * 3600
LIMIT = 10 * 3600
INF = np.int32(1_000_000_000)
WALK_SPEED_MPS = 4.8 / 3.6
WALK_DETOUR = 1.3
ACCESS_EGRESS_RADIUS_M = 800
TRANSFER_RADIUS_M = 250
TRANSFER_MIN_SEC = 60
SAME_STOP_TRANSFER_MIN_SEC = 60


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def gtfs_csv(archive, name):
    with io.TextIOWrapper(archive.open(name), encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def seconds(hms):
    h, m, s = map(int, hms.split(":"))
    return h * 3600 + m * 60 + s


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def walking_seconds(distance_m, minimum=0):
    return np.maximum(minimum, np.ceil(
        np.asarray(distance_m) * WALK_DETOUR / WALK_SPEED_MPS
    ).astype(np.int32))


def load_destinations():
    destinations = []
    for row in read_csv(JOBS):
        destinations.append({
            "kind": "job_proxy", "destination_id": row["workplace_pa"] + "/" + row["grid_id"],
            "x": float(row["destination_x_svy21"]),
            "y": float(row["destination_y_svy21"]),
            "weight": float(row["allocated_income_below_3000"]),
            "spatial_flag": "area_proxy",
        })

    clinic_features = json.loads(CLINIC_GEOJSON.read_text(encoding="utf-8"))["features"]
    transform = Transformer.from_crs(4326, 3414, always_xy=True)
    seen_clinics = set()
    for row in read_csv(CLINICS):
        feature = clinic_features[int(row["source_row"]) - 1]
        lon, lat = feature["geometry"]["coordinates"][:2]
        key = row["hci_code"] or (round(lon, 7), round(lat, 7))
        if key in seen_clinics:
            continue
        seen_clinics.add(key)
        x, y = transform.transform(lon, lat)
        destinations.append({
            "kind": "chas_clinic", "destination_id": str(key),
            "x": x, "y": y, "weight": 1.0, "spatial_flag": "source_point",
        })

    seen_stores = set()
    for row in read_csv(SUPERMARKETS):
        if row["licence_number"] in seen_stores:
            continue
        seen_stores.add(row["licence_number"])
        if not row["longitude"] or not row["latitude"]:
            continue
        x, y = transform.transform(float(row["longitude"]),
                                   float(row["latitude"]))
        destinations.append({
            "kind": "supermarket", "destination_id": row["licence_number"],
            "x": x, "y": y, "weight": 1.0,
            "spatial_flag": row["geocoding_status"],
        })
    return destinations


def load_transit():
    with zipfile.ZipFile(GTFS) as archive:
        stops_raw = gtfs_csv(archive, "stops.txt")
        trips_raw = gtfs_csv(archive, "trips.txt")
        times_raw = gtfs_csv(archive, "stop_times.txt")
        freq_raw = gtfs_csv(archive, "frequencies.txt")
        transfers_raw = gtfs_csv(archive, "transfers.txt")

    transform = Transformer.from_crs(4326, 3414, always_xy=True)
    stops = [s for s in stops_raw if s.get("location_type", "0") in ("", "0")]
    stop_id = {s["stop_id"]: i for i, s in enumerate(stops)}
    xy = np.array([transform.transform(float(s["stop_lon"]),
                                       float(s["stop_lat"])) for s in stops])

    templates = defaultdict(list)
    for row in times_raw:
        if row["stop_id"] in stop_id:
            templates[row["trip_id"]].append((int(row["stop_sequence"]),
                seconds(row["arrival_time"]), seconds(row["departure_time"]),
                stop_id[row["stop_id"]]))
    for values in templates.values():
        values.sort()
    weekday = {t["trip_id"] for t in trips_raw if t["service_id"] == "WD"}

    connections = []
    departures_expanded = 0
    for row in freq_raw:
        trip = row["trip_id"]
        values = templates.get(trip)
        if trip not in weekday or not values or len(values) < 2:
            continue
        headway = int(row["headway_secs"])
        start, end = seconds(row["start_time"]), seconds(row["end_time"])
        base = values[0][2]
        max_offset = values[-2][2] - base
        first_k = max(0, math.ceil((DEPART - max_offset - start) / headway))
        last_k = min(math.ceil((LIMIT - start) / headway),
                     math.ceil((end - start) / headway))
        for k in range(first_k, last_k):
            trip_start = start + k * headway
            if trip_start >= end:
                break
            instance = departures_expanded
            departures_expanded += 1
            for earlier, later in zip(values[:-1], values[1:]):
                dep = trip_start + earlier[2] - base
                arr = trip_start + later[1] - base
                if DEPART <= dep <= LIMIT and arr <= LIMIT and arr >= dep:
                    connections.append((dep, arr, earlier[3], later[3], instance))
    connections.sort(key=lambda c: c[0])
    con = np.asarray(connections, dtype=np.int32)

    # Generic nearby-stop transfer plus any larger minimum in GTFS transfers.
    explicit = {}
    for row in transfers_raw:
        u, v = stop_id.get(row["from_stop_id"]), stop_id.get(row["to_stop_id"])
        if u is not None and v is not None and u != v:
            explicit[(u, v)] = max(30, int(row.get("min_transfer_time") or 0))
    tree = cKDTree(xy)
    transfer = []
    for u, near in enumerate(tree.query_ball_point(xy, TRANSFER_RADIUS_M)):
        edges = {}
        for v in near:
            if u == v:
                continue
            dist = float(np.linalg.norm(xy[u] - xy[v]))
            edges[v] = max(int(walking_seconds(dist, TRANSFER_MIN_SEC)),
                           explicit.get((u, v), 0))
        for (a, b), cost in explicit.items():
            if a == u:
                edges[b] = max(edges.get(b, 0), cost)
        transfer.append(list(edges.items()))
    return stops, xy, tree, con, transfer, departures_expanded


def scan_stop_arrivals(origin_xy, transit):
    stops, stop_xy, tree, con, transfer, expanded = transit
    n_origin, n_stop = len(origin_xy), len(stops)
    arrivals = np.full((n_origin, n_stop), INF, dtype=np.int32)
    access = tree.query_ball_point(origin_xy, ACCESS_EGRESS_RADIUS_M)
    for i, nearby in enumerate(access):
        if nearby:
            idx = np.asarray(nearby, dtype=np.int32)
            dist = np.linalg.norm(stop_xy[idx] - origin_xy[i], axis=1)
            arrivals[i, idx] = DEPART + walking_seconds(dist)

    # Earliest time a passenger is ready to board. Access walking permits
    # immediate boarding; after alighting, allow one minute at the same stop.
    ready = arrivals.copy()
    onboard = np.zeros((n_origin, expanded), dtype=np.bool_)

    improved = 0
    for dep, arr, u, v, instance in con:
        ride = onboard[:, instance] | (ready[:, u] <= dep)
        if not ride.any():
            continue
        onboard[ride, instance] = True
        change = ride & (arr < arrivals[:, v])
        if not change.any():
            continue
        arrivals[change, v] = arr
        boarding_ready = arr + SAME_STOP_TRANSFER_MIN_SEC
        ready[change, v] = np.minimum(ready[change, v], boarding_ready)
        improved += int(change.sum())
        for w, walk in transfer[v]:
            at_w = arr + walk
            walk_ready = change & (at_w < ready[:, w])
            if walk_ready.any():
                ready[walk_ready, w] = at_w
            walk_arrival = change & (at_w < arrivals[:, w])
            if walk_arrival.any():
                arrivals[walk_arrival, w] = at_w
    print(f"Scanned connections; {improved} stop-label improvements", flush=True)

    return arrivals, access


def destination_seconds(origin_xy, dest_xy, transit=None, arrivals=None):
    """Yield travel seconds to each destination, retaining the baseline model assumptions."""
    if transit is None:
        for xy in dest_xy:
            yield walking_seconds(np.linalg.norm(origin_xy - xy, axis=1))
        return
    _, stop_xy, tree, _, _, _ = transit
    egress = tree.query_ball_point(dest_xy, ACCESS_EGRESS_RADIUS_M)
    for j, nearby in enumerate(egress):
        direct = DEPART + walking_seconds(
            np.linalg.norm(origin_xy - dest_xy[j], axis=1))
        if nearby:
            idx = np.asarray(nearby, dtype=np.int32)
            walk = walking_seconds(np.linalg.norm(stop_xy[idx] - dest_xy[j], axis=1))
            by_transit = np.min(arrivals[:, idx] + walk, axis=1)
            arrival = np.minimum(direct, by_transit)
        else:
            arrival = direct
        yield arrival - DEPART


def calculate(max_origins=None):
    origins = read_csv(ORIGINS)
    if max_origins:
        origins = origins[:max_origins]
    origin_xy = np.array([(float(r["route_x"]), float(r["route_y"]))
                          for r in origins])
    dest = load_destinations()
    dest_xy = np.array([(d["x"], d["y"]) for d in dest])
    transit = load_transit()
    stops, _, _, con, _, expanded = transit
    n_origin, n_stop = len(origins), len(stops)
    print(f"Loaded {n_origin} origins, {len(dest)} destinations, "
          f"{n_stop} stops, {len(con)} connections", flush=True)

    arrivals, access = scan_stop_arrivals(origin_xy, transit)
    travel = np.empty((n_origin, len(dest)), dtype=np.uint16)
    for j, seconds_to_dest in enumerate(destination_seconds(origin_xy, dest_xy, transit, arrivals)):
        travel[:, j] = np.minimum(65535, seconds_to_dest).astype(np.uint16)

    kinds = np.array([d["kind"] for d in dest])
    jobs = kinds == "job_proxy"
    clinic = kinds == "chas_clinic"
    market = kinds == "supermarket"
    job_weight = np.array([d["weight"] for d in dest if d["kind"] == "job_proxy"])
    job_30 = (travel[:, jobs] <= 1800).astype(np.float64) @ job_weight
    job_60 = (travel[:, jobs] <= 3600).astype(np.float64) @ job_weight
    clinic_30 = np.count_nonzero(travel[:, clinic] <= 1800, axis=1)
    clinic_60 = np.count_nonzero(travel[:, clinic] <= 3600, axis=1)
    market_30 = np.count_nonzero(travel[:, market] <= 1800, axis=1)
    uncertain = np.array([d["spatial_flag"] == "ambiguous_campus_postal_over_500m"
                          for d in dest])
    market_30_without_uncertain = np.count_nonzero(
        travel[:, market & ~uncertain] <= 1800, axis=1)

    suffix = "_sample" if max_origins else ""
    result_file = OUT / f"grid_destination_access_0900_95pct{suffix}.csv"
    with result_file.open("w", encoding="utf-8-sig", newline="") as stream:
        fields = ["grid_id", "s_low_income_work_access_30m",
                  "s_low_income_work_access_60m", "s_chas_clinics_access_30m",
                  "s_chas_clinics_access_60m", "s_supermarkets_access_30m",
                  "s_supermarkets_access_30m_without_uncertain_ntu"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for i, origin in enumerate(origins):
            writer.writerow(dict(zip(fields, [origin["grid_id"], job_30[i],
                job_60[i], int(clinic_30[i]), int(clinic_60[i]),
                int(market_30[i]), int(market_30_without_uncertain[i])]
            )))

    if not max_origins:
        previous = read_csv(PREVIOUS)
        previous_by_id = {row["grid_id"]: row for row in previous}
        if len(previous_by_id) != n_origin or set(previous_by_id) != {
                row["grid_id"] for row in origins}:
            raise ValueError("Three-indicator grid IDs do not match destinations")
        combined_file = OUT / "grid_supply_eight_ready_95pct.csv"
        combined_fields = list(previous[0]) + fields[1:]
        new_rows = read_csv(result_file)
        with combined_file.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=combined_fields)
            writer.writeheader()
            for row in new_rows:
                writer.writerow(previous_by_id[row["grid_id"]] | {
                    k: v for k, v in row.items() if k != "grid_id"})

    index_file = OUT / f"destination_access_index_0900{suffix}.csv"
    with index_file.open("w", encoding="utf-8-sig", newline="") as stream:
        fields = ["destination_index", "kind", "destination_id", "weight",
                  "x_svy21", "y_svy21", "spatial_flag"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for j, d in enumerate(dest):
            writer.writerow({"destination_index": j, "kind": d["kind"],
                "destination_id": d["destination_id"], "weight": d["weight"],
                "x_svy21": d["x"], "y_svy21": d["y"],
                "spatial_flag": d["spatial_flag"]})
    matrix_file = OUT / f"destination_travel_seconds_0900{suffix}.npz"
    np.savez_compressed(matrix_file, travel_seconds=travel,
                        grid_ids=np.array([r["grid_id"] for r in origins]))

    audit = {
        "model": "frequency-expanded weekday GTFS connection scan, one-to-many from all grid origins",
        "departure_local_time": "weekday 09:00",
        "travel_threshold_seconds": [1800, 3600],
        "gtfs_release": "singapore-gtfs v2026-07-12, third-party LTA-derived frequency-based proxy",
        "gtfs_departures_expanded": expanded,
        "connections_0900_1000": len(con),
        "transit_stops": n_stop,
        "origins": n_origin,
        "destinations": {kind: int(np.count_nonzero(kinds == kind)) for kind in
                         ["job_proxy", "chas_clinic", "supermarket"]},
        "walking_speed_kmh": WALK_SPEED_MPS * 3.6,
        "euclidean_detour_factor": WALK_DETOUR,
        "access_egress_radius_m": ACCESS_EGRESS_RADIUS_M,
        "transfer_radius_m": TRANSFER_RADIUS_M,
        "generic_interstop_transfer_min_seconds": TRANSFER_MIN_SEC,
        "same_stop_transfer_min_seconds": SAME_STOP_TRANSFER_MIN_SEC,
        "trip_continuation": "same vehicle instance retained across consecutive GTFS stop-time connections",
        "direct_walking": "allowed, same speed and detour factor",
        "jobs_definition": "2020 low-income employed residents allocated to 2019 employment land, not individual jobs",
        "clinics_definition": "distinct CHAS HCI codes in source point file",
        "supermarkets_definition": "distinct currently licensed SFA records, dated 2026-11-08",
        "supermarket_ambiguous_record": "NTU postal 639798; alternative count excludes it",
        "cautions": ["Frequency-based GTFS is modelled, not an observed timetable",
                     "Walking uses straight-line distance times 1.3 and may cross barriers",
                     "No actual bus reliability or congestion delay",
                     "Source years differ"],
        "source_sha256": {path.name: sha256(path) for path in [
            GTFS, ORIGINS, JOBS, CLINICS, CLINIC_GEOJSON, SUPERMARKETS]},
        "checks": {
            "unique_grid_ids": len({r["grid_id"] for r in origins}) == n_origin,
            "unique_destination_ids_within_kind": len({
                (d["kind"], d["destination_id"]) for d in dest}) == len(dest),
            "all_30m_le_60m_jobs": bool(np.all(job_30 <= job_60 + 1e-8)),
            "all_30m_le_60m_clinics": bool(np.all(clinic_30 <= clinic_60)),
            "all_market_30m_minus_exclusion_at_most_one": bool(
                np.all((market_30 - market_30_without_uncertain) <= 1)),
            "jobs_60m_max_le_source_total": bool(np.all(job_60 <= 539046 + 1e-6)),
            "combined_grid_id_match": not max_origins,
        },
        "summary": {
            "jobs_30m_median": float(np.median(job_30)),
            "jobs_60m_median": float(np.median(job_60)),
            "clinics_30m_median": float(np.median(clinic_30)),
            "clinics_60m_median": float(np.median(clinic_60)),
            "supermarkets_30m_median": float(np.median(market_30)),
            "origins_with_zero_transit_access_stops": sum(not x for x in access),
            "supermarket_ambiguous_record_affected_grids": int(np.count_nonzero(
                market_30 != market_30_without_uncertain)),
        },
    }
    audit_file = OUT / f"destination_access_audit_0900{suffix}.json"
    audit_file.write_text(json.dumps(audit, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    print(f"Wrote {result_file}", flush=True)
    print(json.dumps(audit["checks"] | audit["summary"], indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--origins", type=int, default=None,
                        help="Limit origins for a smoke test")
    calculate(parser.parse_args().origins)
