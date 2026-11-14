"""Render a deterministic, human-readable report for one research agent run."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def render(run_id: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,63}", run_id):
        raise ValueError("Invalid run ID")
    run_dir = ROOT / "output/agent_runs" / run_id
    report = json.loads((run_dir / "agent_report.json").read_text(encoding="utf-8"))
    plan = json.loads((run_dir / "plan.json").read_text(encoding="utf-8"))
    lines = ["# 研究情景 Agent 运行报告", "", f"**研究问题：** {report['question']}", "",
             "**分析范围：** 1,597 个正估计人口网格。", ""]
    if report["status"] == "needs_data":
        lines.extend(["## 所需数据", ""])
        lines.extend(f"- {item}" for item in report["data_needed"])
        lines.extend(["", "未进行情景计算。", ""])
    elif report["status"] == "awaiting_review":
        lines.extend(["## 情景方案（待审核）", "", plan["rationale"], "",
                      "| 类别 | 指标 | 建议权重 | 理由 |", "|---|---|---:|---|"])
        for side, label in (("demand", "需求"), ("supply", "供给")):
            for change in plan[f"{side}_changes"]:
                lines.append(f"| {label} | {change['indicator_id']} | {change['weight']} | {change['reason']} |")
        lines.extend(["", "## 数据与解释范围", "", *plan["limitations"], "",
                      "批准后按网格 ID 与原基线的 148 个候选比较。"])
        if (run_dir / "evidence.md").exists():
            lines.extend(["", "[文献依据与指标核对](evidence.md)"])
    elif report["status"] == "completed":
        lines.extend(["## 筛选结果", "",
            f"- 基线候选网格：**{report['baseline_candidate_count']}**",
            f"- 情景候选网格：**{report['candidate_count']}**",
            f"- 新增：**{report['entered']}**；退出：**{report['exited']}**；"
            f"保持入选：**{report['retained']}**", ""])
        scenario_dir = ROOT / "output/scenarios" / run_id
        audit = json.loads((scenario_dir / "baseline_comparison_audit.json").read_text(
            encoding="utf-8"))
        lines.extend([f"需求等级变化：{audit['demand_level_changed']} 个网格；"
                      f"供给不足等级变化：{audit['supply_level_changed']} 个网格。",
                      "", "## 权重调整", "",
                      "| 侧面 | 指标 | 权重 | 理由 |",
                      "|---|---|---:|---|"])
        for side in ("demand", "supply"):
            for change in plan[f"{side}_changes"]:
                lines.append(f"| {'需求' if side == 'demand' else '供给'} | `{change['indicator_id']}` | "
                    f"{change['weight']} | {change['reason'].replace('|', '/')} |")
        if not plan["demand_changes"] and not plan["supply_changes"]:
            lines.append("| 两侧 | 无调整 | 1 | 保留基线权重 |")
        lines.extend(["", "## 新增与退出网格所在规划区", "",
                      "| 规划区 | 新增 | 退出 |",
                      "|---|---:|---:|"])
        with (scenario_dir / "candidate_changes_by_planning_area.csv").open(
                encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                lines.append(f"| {row['dominant_pa']} | {row['entered']} | {row['exited']} |")
        lines.extend(["", "## 解释范围", "",
            "权重是探索性设定。候选身份变化只表示同一组 1,597 个网格在新权重下"
            "的分类变化，不能代表实测出行缺口或因果效应。",
            "需求数量是由较粗的 2020 年统计地理单元分配到网格的估计值；"
            "部分供给指标使用模型化出行时间或预期公交到站次数。",
            "", "逐网格变化见 `baseline_comparison.csv`；输入哈希、阈值和分级数量"
            "见 `scenario_audit.json`。", ""])
    else:
        lines.extend(["## 状态", "", f"{report['status']}: {report.get('error', '')}", ""])
    target = run_dir / "report.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    args = parser.parse_args()
    print(render(args.run_id))


if __name__ == "__main__":
    main()
