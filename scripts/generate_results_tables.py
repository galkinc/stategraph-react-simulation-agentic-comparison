#!/usr/bin/env python3
"""
Generate results tables for §4 Results from aggregate_metrics.json.
"""

import json
import sys
from pathlib import Path
from typing import Any, List, Tuple
import statistics

PROJECT_ROOT = Path(__file__).parent.parent
METRICS_FILE = PROJECT_ROOT / "data" / "output" / "aggregate_metrics.json"
OUTPUT_FILE = PROJECT_ROOT / "docs" / "parts" / "04_results_generated.md"


def load_metrics() -> dict[str, Any]:
    if not METRICS_FILE.exists():
        print(f"Error: {METRICS_FILE} not found", file=sys.stderr)
        sys.exit(1)
    with open(METRICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_run_stats(metrics: dict[str, Any]) -> dict[str, dict[str, float]]:
    by_run = metrics.get("by_run", [])
    stats = {"react": {"runs": 0}, "stategraph": {"runs": 0}}

    for run in by_run:
        strategy = run["strategy"]
        if strategy not in stats:
            stats[strategy] = {"runs": 0}
        stats[strategy]["runs"] += 1

        latency = run.get("latency", {})
        stats[strategy].setdefault("latency_values", []).append(latency.get("e2e_total_ms", 0))

        msg = latency.get("message")
        stats[strategy].setdefault("message_latency_values", []).append(msg.get("mean", 0) if msg else 0)

        sim = latency.get("simulator")
        stats[strategy].setdefault("simulator_latency_values", []).append(sim.get("mean", 0) if sim else 0)

        orch = latency.get("orchestration")
        stats[strategy].setdefault("orchestration_latency_values", []).append(orch.get("mean", 0) if orch else 0)

        stats[strategy].setdefault("steps_values", []).append(run.get("total_steps", 0))

        tokens = run.get("tokens", {})
        stats[strategy].setdefault("tokens_values", []).append(tokens.get("total", 0))

        stats[strategy].setdefault("success_values", []).append(run.get("success", 0))

        cov = run.get("coverage", {})
        stats[strategy].setdefault("coverage_values", []).append(cov.get("coverage_final", 0))

        dec = run.get("decision", {})
        stats[strategy].setdefault("instability_values", []).append(dec.get("decision_instability", 0))

        stats[strategy].setdefault("cov_per_step_values", []).append(cov.get("coverage_per_step", 0))
        stats[strategy].setdefault("cov_per_token_values", []).append(cov.get("coverage_per_token", 0))
        cov_vel = cov.get("coverage_velocity")
        stats[strategy].setdefault("cov_vel_values", []).append(cov_vel.get("mean", 0) if cov_vel else 0)

    result = {}
    for strategy, data in stats.items():
        if data["runs"] == 0:
            continue
        result[strategy] = {
            "runs": data["runs"],
            # mean/median helpers
            "latency_mean": statistics.mean(data["latency_values"]),
            "latency_median": statistics.median(data["latency_values"]),
            "message_latency_mean": statistics.mean(data["message_latency_values"]),
            "message_latency_median": statistics.median(data["message_latency_values"]),
            "simulator_latency_mean": statistics.mean(data["simulator_latency_values"]),
            "simulator_latency_median": statistics.median(data["simulator_latency_values"]),
            "orchestration_latency_mean": statistics.mean(data["orchestration_latency_values"]),
            "orchestration_latency_median": statistics.median(data["orchestration_latency_values"]),
            "steps_mean": statistics.mean(data["steps_values"]),
            "steps_median": statistics.median(data["steps_values"]),
            "steps_min": min(data["steps_values"]),
            "steps_max": max(data["steps_values"]),
            "tokens_mean": statistics.mean(data["tokens_values"]),
            "tokens_median": statistics.median(data["tokens_values"]),
            "success_rate": statistics.mean(data["success_values"]),
            "coverage_mean": statistics.mean(data["coverage_values"]),
            "coverage_median": statistics.median(data["coverage_values"]),
            "instability_mean": statistics.mean(data["instability_values"]),
            "instability_median": statistics.median(data["instability_values"]),
            "cov_per_step_mean": statistics.mean(data["cov_per_step_values"]),
            "cov_per_token_mean": statistics.mean(data["cov_per_token_values"]),
            "cov_vel_mean": statistics.mean(data["cov_vel_values"]),
        }
    return result


def fmt(value: float, decimals: int = 2) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.{decimals}f}"


def effect_size_label(rb: float) -> str:
    a = abs(rb)
    if a < 0.1:
        return "negligible"
    if a < 0.3:
        return "small"
    if a < 0.5:
        return "medium"
    return "large"


# --- Универсальная функция для простых таблиц ---
def simple_table(title: str, headers: List[str], rows: List[List[str]]) -> str:
    lines = [f"\n### {title}\n", "| " + " | ".join(headers) + " |",
             "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


# --- Генераторы таблиц ---
def key_findings_table(stats: dict, exp_stats: dict) -> str:
    boot = {b["metric"]: b for b in exp_stats.get("bootstrap", [])}
    wilcox = {w["metric"]: w for w in exp_stats.get("wilcoxon", [])}
    winloss = {w["metric"]: w for w in exp_stats.get("win_loss", [])}
    mcnemar = exp_stats.get("mcnemar", [{}])[0].get("p_value", 0.52)

    r = stats["react"]
    s = stats["stategraph"]

    def row(name, key, unit="", prec=2):
        b = boot.get(key, {})
        w = wilcox.get(key, {})
        wl = winloss.get(key, {}).get("rank_biserial", 0)
        delta = b.get("delta", 0)
        ci_low = b.get("ci_low", 0)
        ci_high = b.get("ci_high", 0)
        p = w.get("p_value", 0)
        p_str = f"{p:.2e}" if p < 0.01 else f"{p:.2f}"
        return (
            f"| **{name}** | {fmt(r[f'{key}_mean'], prec)}{unit} | {fmt(r[f'{key}_median'], prec)}{unit} | "
            f"{fmt(s[f'{key}_mean'], prec)}{unit} | {fmt(s[f'{key}_median'], prec)}{unit} | "
            f"**{fmt(delta, 0)}{unit}** | [{fmt(ci_low, 0)}, {fmt(ci_high, 0)}] | "
            f"{p_str} | {wl:.2f} ({effect_size_label(wl)}) |"
        )

    lines = ["### Summary Statistics",
             "| Metric | ReAct Mean | ReAct Median | StateGraph Mean | StateGraph Median | Delta | 95% CI | p-value | Effect Size |",
             "| ------ | --------- | ----------- | --------------- | ----------------- | ----- | ------ | ------- | ----------- |"]
    lines.append(row("E2E Latency (per dialogue)", "latency", "ms"))
    lines.append(row("Message Latency (per step)", "message_latency", "ms"))
    lines.append(row("Simulator Latency (per step)", "simulator_latency", "ms"))
    lines.append(row("Orchestration (per step)", "orchestration_latency", "ms"))
    lines.append(row("Steps (per dialogue)", "steps", "", 2))
    lines.append(row("Tokens (per dialogue)", "tokens", "", 0))

    lines.append(
        f"| **Success Rate** | {fmt(r['success_rate']*100,1)}% | {fmt(r['success_rate']*100,1)}% | "
        f"{fmt(s['success_rate']*100,1)}% | {fmt(s['success_rate']*100,1)}% | — | — | "
        f"{mcnemar:.2f} (McNemar) | — |"
    )
    lines.append(row("Coverage Final", "coverage", "", 2))
    return "\n".join(lines)


def latency_tables(stats: dict) -> str:
    blocks = []
    for title, key in [("Message Latency (LLM Call)", "message_latency"),
                       ("Simulator Latency (Patient Response)", "simulator_latency"),
                       ("Orchestration Overhead", "orchestration_latency")]:
        rows = [
            ["ReAct", fmt(stats["react"][f"{key}_mean"]), fmt(stats["react"][f"{key}_median"])],
            ["StateGraph", fmt(stats["stategraph"][f"{key}_mean"]), fmt(stats["stategraph"][f"{key}_median"])]
        ]
        blocks.append(simple_table(title, ["Strategy", "Mean (ms)", "Median (ms)"], rows))
    return "\n".join(blocks)


def efficiency_tables(stats: dict) -> str:
    # Steps
    steps_rows = [
        ["ReAct", fmt(stats["react"]["steps_mean"],2), fmt(stats["react"]["steps_median"],1),
         str(stats["react"]["steps_min"]), str(stats["react"]["steps_max"])],
        ["StateGraph", fmt(stats["stategraph"]["steps_mean"],2), fmt(stats["stategraph"]["steps_median"],1),
         str(stats["stategraph"]["steps_min"]), str(stats["stategraph"]["steps_max"])]
    ]
    steps_table = simple_table("Dialogue Length (Steps)",
                               ["Strategy", "Mean", "Median", "Min", "Max"], steps_rows)

    # Tokens
    token_rows = [
        ["ReAct", fmt(stats["react"]["tokens_mean"],0),
         fmt(stats["react"]["tokens_mean"] / stats["react"]["steps_mean"],0)],
        ["StateGraph", fmt(stats["stategraph"]["tokens_mean"],0),
         fmt(stats["stategraph"]["tokens_mean"] / stats["stategraph"]["steps_mean"],0)]
    ]
    token_table = simple_table("Token Consumption",
                               ["Strategy", "Mean (total/dialogue)", "Mean (per step)"], token_rows)
    return steps_table + "\n" + token_table


def outcome_tables(stats: dict) -> str:
    # Success
    succ_rows = [
        ["ReAct", fmt(stats["react"]["success_rate"]*100,1) + "%"],
        ["StateGraph", fmt(stats["stategraph"]["success_rate"]*100,1) + "%"]
    ]
    succ_table = simple_table("Dialogue Success Rate", ["Strategy", "Success Rate"], succ_rows)

    # Coverage final
    cov_rows = [
        ["ReAct", fmt(stats["react"]["coverage_mean"],2)],
        ["StateGraph", fmt(stats["stategraph"]["coverage_mean"],2)]
    ]
    cov_table = simple_table("Information Extraction (Coverage)", ["Strategy", "Mean Final Coverage"], cov_rows)
    return succ_table + "\n" + cov_table


def stability_table(stats: dict) -> str:
    rows = [
        ["ReAct", fmt(stats["react"]["instability_mean"],2), fmt(stats["react"]["instability_median"],1)],
        ["StateGraph", fmt(stats["stategraph"]["instability_mean"],2), fmt(stats["stategraph"]["instability_median"],1)]
    ]
    return simple_table("Decision Instability", ["Strategy", "Mean", "Median"], rows)


def derived_metrics_tables(stats: dict) -> str:
    # Three separate tables, as in the old output
    per_step = simple_table("Coverage per Step", ["Strategy", "Mean Coverage/Step"], [
        ["ReAct", fmt(stats["react"]["cov_per_step_mean"],3)],
        ["StateGraph", fmt(stats["stategraph"]["cov_per_step_mean"],3)]
    ])
    per_token = simple_table("Coverage per Token", ["Strategy", "Mean Coverage/Token"], [
        ["ReAct", fmt(stats["react"]["cov_per_token_mean"],5)],
        ["StateGraph", fmt(stats["stategraph"]["cov_per_token_mean"],5)]
    ])
    velocity = simple_table("Coverage Velocity", ["Strategy", "Mean Velocity"], [
        ["ReAct", fmt(stats["react"]["cov_vel_mean"],3)],
        ["StateGraph", fmt(stats["stategraph"]["cov_vel_mean"],3)]
    ])
    return per_step + "\n" + per_token + "\n" + velocity


def main():
    metrics = load_metrics()
    stats = compute_run_stats(metrics)
    exp_stats = metrics.get("experiment_statistics", {})

    tables = [
        "## Generated Tables\n",
        key_findings_table(stats, exp_stats),
        "\n### Latency Tables (for §4.2)\n",
        latency_tables(stats),
        "\n### Efficiency Tables (for §4.3)\n",
        efficiency_tables(stats),
        "\n### Outcome Tables (for §4.4)\n",
        outcome_tables(stats),
        "\n### Stability Table (for §4.5)\n",
        stability_table(stats),
        "\n### Derived Metrics Tables (for §4.6)\n",
        derived_metrics_tables(stats),
        "\n"
    ]

    output = "\n".join(tables)
    print(output)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(output, encoding="utf-8")
    print(f"\nTables written to {OUTPUT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()