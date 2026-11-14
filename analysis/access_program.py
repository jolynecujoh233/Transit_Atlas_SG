"""Interpret a model-written accessibility expression over local grid origins and point destinations."""
import ast

import numpy as np
import pandas as pd

import calculate_destination_access as routing


GUIDE = (
    "对于新的点目的地可达性指标，operation 选 access_program，在 analysis_code 中生成一个 Python 表达式。"
    "count_within(travel, minutes) 按时间阈值数目的地记录；"
    "decayed_access(travel, half_life, cutoff) 计算阈值内按出行时间半衰期加权的目的地总数。"
    "travel 用 walk_minutes() 或 weekday_0900_minutes()；前者按距离乘1.3、4.8公里/小时步行，"
    "后者采用工作日09:00班表模型并允许步行。参数为1至60的整数分钟。例：count_within(weekday_0900_minutes(), 45)。"
    "仅适用于每条记录代表一个目的地的点数据。填 side=supply、factor=destinations、direction=higher_is_better，"
    "无需数值字段。说明时段、出行方式、阈值、重复点及模型局限。"
    "不能用工作日网络代表周末。其他操作的 analysis_code 填空字符串。"
)


def parse_access(code):
    if not isinstance(code, str) or len(code) > 200:
        raise ValueError("需要简短的可达性分析表达式")
    try:
        call = ast.parse(code.strip(), mode="eval").body
    except (SyntaxError, ValueError) as exc:
        raise ValueError("可达性表达式语法无效") from exc
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.keywords:
        raise ValueError("只支持直接调用已接入的可达性函数")
    metric = call.func.id
    arity = {"count_within": 2, "decayed_access": 3}
    if len(call.args) != arity.get(metric):
        raise ValueError("可达性函数名称或参数个数无效")
    travel = call.args[0]
    if (not isinstance(travel, ast.Call) or not isinstance(travel.func, ast.Name) or
            travel.args or travel.keywords or travel.func.id not in {"walk_minutes", "weekday_0900_minutes"}):
        raise ValueError("请选择步行或工作日09:00公交与步行模型")
    minutes = []
    for node in call.args[1:]:
        if not isinstance(node, ast.Constant) or type(node.value) is not int or not 1 <= node.value <= 60:
            raise ValueError("时间参数须为1至60的整数分钟")
        minutes.append(node.value)
    return metric, travel.func.id, minutes


def analyse_points(points, grid_ids, code):
    metric, mode, minutes = parse_access(code)
    if points.empty or not points.geometry.geom_type.eq("Point").all():
        raise ValueError("每个目的地必须是一条有效的点记录")
    origins = pd.read_csv(routing.ORIGINS).set_index("grid_id", verify_integrity=True)
    origin_xy = origins.loc[grid_ids, ["route_x", "route_y"]].to_numpy(dtype=float)
    dest_xy = np.column_stack((points.geometry.x, points.geometry.y))
    if not np.isfinite(origin_xy).all() or not np.isfinite(dest_xy).all():
        raise ValueError("存在无效的出发点或目的地坐标")
    transit = arrivals = None
    audit = {"analysis_code": code, "origin_sha256": routing.sha256(routing.ORIGINS),
             "destination_records": len(points), "walk_detour": routing.WALK_DETOUR,
             "walk_speed_kmh": routing.WALK_SPEED_MPS * 3.6}
    if mode == "weekday_0900_minutes":
        transit = routing.load_transit()
        arrivals, _ = routing.scan_stop_arrivals(origin_xy, transit)
        audit.update(gtfs_sha256=routing.sha256(routing.GTFS), departure="weekday 09:00")
    values = np.zeros(len(grid_ids), dtype=float)
    for seconds in routing.destination_seconds(origin_xy, dest_xy, transit, arrivals):
        reachable = seconds <= minutes[-1] * 60
        if metric == "count_within":
            values += reachable
        else:
            values[reachable] += np.exp2(-seconds[reachable] / (60 * minutes[0]))
    return pd.Series(values, index=grid_ids), audit
