#!/usr/bin/env python3
"""
Generate figures for §4 Results from aggregate_metrics.json.

This script creates publication-ready figures:
- Figure 1: E2E Latency Distribution (Violin Plot)
- Figure 2: Steps Distribution (Box Plot)
- Figure 3: Forest Plot (Delta + CI)
- Figure 4: Combined Summary (Forest + Violin)

Usage:
    python scripts/generate_figures.py

Output:
    docs/figures/figure_1_latency_violin.png
    docs/figures/figure_1_latency_violin.svg
    docs/figures/figure_2_steps_box.png
    docs/figures/figure_2_steps_box.svg
    docs/figures/figure_3_forest_plot.png
    docs/figures/figure_3_forest_plot.svg
    docs/figures/figure_4_combined_summary.png
    docs/figures/figure_4_combined_summary.svg
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
METRICS_FILE = PROJECT_ROOT / "data" / "output" / "aggregate_metrics.json"
FIGURES_DIR = PROJECT_ROOT / "docs" / "figures"

# Ensure figures directory exists
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def load_metrics() -> dict[str, Any]:
    """Load aggregate metrics from JSON file."""
    if not METRICS_FILE.exists():
        print(f"Error: {METRICS_FILE} not found", file=sys.stderr)
        sys.exit(1)
    
    with open(METRICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_latency_data(by_run: list[dict]) -> dict[str, list[float]]:
    """Extract E2E latency values for each strategy."""
    latency_data = {"react": [], "stategraph": []}
    
    for run in by_run:
        strategy = run["strategy"].lower()
        latency = run.get("latency", {})
        e2e_total = latency.get("e2e_total_ms", 0)
        if e2e_total > 0:
            latency_data[strategy].append(e2e_total)
    
    return latency_data


def extract_steps_data(by_run: list[dict]) -> dict[str, list[int]]:
    """Extract total steps for each strategy."""
    steps_data = {"react": [], "stategraph": []}
    
    for run in by_run:
        strategy = run["strategy"].lower()
        total_steps = run.get("total_steps", 0)
        if total_steps > 0:
            steps_data[strategy].append(total_steps)
    
    return steps_data


def extract_bootstrap_data(experiment_stats: dict) -> list[dict]:
    """Extract bootstrap delta and CI for forest plot."""
    bootstrap = experiment_stats.get("bootstrap", [])
    
    # Order metrics for display
    metric_order = [
        "latency",
        "message_latency",
        "simulator_latency",
        "orchestration_latency",
        "steps",
        "tokens",
        "coverage",
    ]
    
    # Sort bootstrap results by desired order
    ordered_bootstrap = []
    for metric in metric_order:
        for b in bootstrap:
            if b["metric"] == metric:
                ordered_bootstrap.append(b)
                break
    
    return ordered_bootstrap


def generate_violin_plot(latency_data: dict[str, list[float]], save_path: str):
    """Generate Figure 1: E2E Latency Distribution (Violin Plot)."""
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
    
    plt.style.use("seaborn-v0_8-whitegrid")
    sns.set_palette("husl")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Prepare data
    data_to_plot = [
        latency_data["react"],
        latency_data["stategraph"]
    ]
    
    # Create violin plot
    parts = ax.violinplot(
        data_to_plot,
        positions=[1, 2],
        widths=0.7,
        showmeans=True,
        showmedians=True,
        showextrema=True
    )
    
    # Customize colors
    colors = ["#3498db", "#e74c3c"]  # Blue for ReAct, Red for StateGraph
    for pc, color in zip(parts["bodies"], colors):
        pc.set_facecolor(color)
        pc.set_edgecolor("black")
        pc.set_alpha(0.7)
    
    # Customize mean/median lines
    for partname in ("cb_means", "cmedians"):
        if partname in parts:
            vp = parts[partname]
            vp.set_edgecolor("black")
            vp.set_linewidth(2)
    
    # Labels
    ax.set_xticks([1, 2])
    ax.set_xticklabels(["ReAct", "StateGraph"], fontsize=12, fontweight="bold")
    ax.set_xlabel("Strategy", fontsize=12, fontweight="bold")
    ax.set_ylabel("E2E Latency (ms)", fontsize=12, fontweight="bold")
    ax.set_title(
        "Figure 1: E2E Latency Distribution by Strategy",
        fontsize=14,
        fontweight="bold"
    )
    
    # Add statistics with sample sizes
    n_react = len(latency_data["react"])
    n_sg = len(latency_data["stategraph"])
    stats_text = (
        f"ReAct (n={n_react}): mean={np.mean(latency_data['react']):.0f}ms, "
        f"median={np.median(latency_data['react']):.0f}ms\n"
        f"StateGraph (n={n_sg}): mean={np.mean(latency_data['stategraph']):.0f}ms, "
        f"median={np.median(latency_data['stategraph']):.0f}ms"
    )
    if n_react != n_sg:
        stats_text += f"\n⚠️ {n_react - n_sg} StateGraph runs excluded (missing latency data)"
    
    ax.text(
        0.5, -0.18, stats_text,
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5)
    )
    
    plt.tight_layout()
    plt.savefig(save_path.replace(".svg", ""), dpi=300, bbox_inches="tight")
    plt.savefig(save_path.replace(".png", ".svg"), bbox_inches="tight")
    plt.close()
    
    print(f"Generated: {save_path}")


def generate_box_plot(steps_data: dict[str, list[int]], save_path: str):
    """Generate Figure 2: Steps Distribution (Box Plot)."""
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
    
    plt.style.use("seaborn-v0_8-whitegrid")
    sns.set_palette("husl")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Prepare data
    data_to_plot = [
        steps_data["react"],
        steps_data["stategraph"]
    ]
    
    # Create box plot
    colors = ["#3498db", "#e74c3c"]
    parts = ax.boxplot(
        data_to_plot,
        positions=[1, 2],
        widths=0.6,
        patch_artist=True,
        tick_labels=["ReAct", "StateGraph"],
        showmeans=True,
        showfliers=True,
        flierprops=dict(marker='o', markerfacecolor='red', markersize=6, linestyle='none')
    )
    
    # Color boxes
    for patch, color in zip(parts["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # Labels
    ax.set_ylabel("Total Steps per Dialogue", fontsize=12, fontweight="bold")
    ax.set_title(
        "Figure 2: Steps Distribution by Strategy\n"
        f"ReAct: n={len(steps_data['react'])}, "
        f"StateGraph: n={len(steps_data['stategraph'])}",
        fontsize=14,
        fontweight="bold"
    )
    
    # Add max_steps line
    ax.axhline(y=15, color="gray", linestyle="--", linewidth=2, alpha=0.7)
    ax.text(2.1, 15.2, "max_steps cap (15)", fontsize=9, color="gray")
    
    # Add statistics
    stats_text = (
        f"ReAct: mean={np.mean(steps_data['react']):.2f}, "
        f"median={np.median(steps_data['react']):.1f}\n"
        f"StateGraph: mean={np.mean(steps_data['stategraph']):.2f}, "
        f"median={np.median(steps_data['stategraph']):.1f}"
    )
    ax.text(
        0.5, -0.15, stats_text,
        transform=ax.transAxes,
        ha="center",
        fontsize=10,
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5)
    )
    
    plt.tight_layout()
    plt.savefig(save_path.replace(".svg", ""), dpi=300, bbox_inches="tight")
    plt.savefig(save_path.replace(".png", ".svg"), bbox_inches="tight")
    plt.close()
    
    print(f"Generated: {save_path}")


def generate_forest_plot(bootstrap_data: list[dict], save_path: str):
    """Generate Figure 3: Forest Plot (Delta + CI)."""
    import matplotlib.pyplot as plt
    import numpy as np
    
    plt.style.use("seaborn-v0_8-whitegrid")
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Prepare data
    n_metrics = len(bootstrap_data)
    y_positions = np.arange(n_metrics)
    
    # Metric labels (human-readable)
    metric_labels = {
        "latency": "E2E Latency (per dialogue)",
        "message_latency": "Message Latency (per step)",
        "simulator_latency": "Simulator Latency (per step)",
        "orchestration_latency": "Orchestration (per step)",
        "steps": "Steps (per dialogue)",
        "tokens": "Tokens (per dialogue)",
        "coverage": "Coverage Final"
    }
    
    labels = [metric_labels.get(b["metric"], b["metric"]) for b in bootstrap_data]
    deltas = [b["delta"] for b in bootstrap_data]
    ci_low = [b["ci_low"] for b in bootstrap_data]
    ci_high = [b["ci_high"] for b in bootstrap_data]
    
    # Plot each point individually with its own color
    for i, b in enumerate(bootstrap_data):
        delta = b["delta"]
        ci_l = b["ci_low"]
        ci_h = b["ci_high"]
        
        # Color based on significance
        if ci_l > 0 or ci_h < 0:
            color = "#e74c3c"  # Red: significant
        else:
            color = "#95a5a6"  # Gray: not significant
        
        # Plot error bar
        ax.errorbar(
            delta, i,
            xerr=[[delta - ci_l], [ci_h - delta]],
            fmt="o",
            ecolor="#7f8c8d",
            elinewidth=2,
            capsize=6,
            markersize=10,
            color=color,
            alpha=0.8
        )
        
        # Add delta label
        sig = "*" if (ci_l > 0 or ci_h < 0) else ""
        ax.text(delta + 150 if delta > 0 else delta - 150, i, f"{delta:.0f}{sig}",
                ha="right" if delta < 0 else "left", va="center", fontsize=9)
        
        # Add CI label (smaller, below the point)
        ci_text = f"[{ci_l:.0f}, {ci_h:.0f}]"
        ax.text(delta, i - 0.35, ci_text,
                ha="center", va="top", fontsize=7, color="#555555")
    
    # Vertical line at 0 (no difference)
    ax.axvline(x=0, color="black", linestyle="-", linewidth=2, alpha=0.5)
    ax.text(0.02, n_metrics - 0.5, "No difference", fontsize=10, rotation=90, alpha=0.7)
    
    # Labels
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, fontsize=11)
    ax.set_xlabel(
        "Delta (ReAct − StateGraph)\nNegative = ReAct is faster/lower",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_title(
        "Figure 3: Effect Sizes with 95% Confidence Intervals\n"
        "Red = Significant (CI excludes 0), Gray = Not Significant",
        fontsize=14,
        fontweight="bold"
    )
    
    # Grid
    ax.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    plt.savefig(save_path.replace(".svg", ""), dpi=300, bbox_inches="tight")
    plt.savefig(save_path.replace(".png", ".svg"), bbox_inches="tight")
    plt.close()
    
    print(f"Generated: {save_path}")


def generate_combined_summary(latency_data: dict[str, list[float]], 
                              bootstrap_data: list[dict], 
                              save_path: str):
    """Generate Figure 4: Combined Summary (Forest Plot + Violin)."""
    import matplotlib.pyplot as plt
    import numpy as np
    
    plt.style.use("seaborn-v0_8-whitegrid")
    
    fig = plt.figure(figsize=(14, 8))
    
    # Create grid: 60% forest plot, 40% violin
    gs = fig.add_gridspec(1, 2, width_ratios=[3, 2], wspace=0.3)
    
    ax_forest = fig.add_subplot(gs[0])
    ax_violin = fig.add_subplot(gs[1])
    
    # ========== LEFT: Forest Plot ==========
    n_metrics = len(bootstrap_data)
    y_positions = np.arange(n_metrics)
    
    metric_labels = {
        "latency": "E2E Latency",
        "message_latency": "Message Latency",
        "simulator_latency": "Simulator Latency",
        "orchestration_latency": "Orchestration",
        "steps": "Steps",
        "tokens": "Tokens",
        "coverage": "Coverage"
    }
    
    labels = [metric_labels.get(b["metric"], b["metric"]) for b in bootstrap_data]
    deltas = [b["delta"] for b in bootstrap_data]
    ci_low = [b["ci_low"] for b in bootstrap_data]
    ci_high = [b["ci_high"] for b in bootstrap_data]

    # Plot each point individually with its own color
    for i, b in enumerate(bootstrap_data):
        delta = b["delta"]
        ci_l = b["ci_low"]
        ci_h = b["ci_high"]
        
        if ci_l > 0 or ci_h < 0:
            color = "#e74c3c"
        else:
            color = "#95a5a6"
        
        ax_forest.errorbar(
            delta, i,
            xerr=[[delta - ci_l], [ci_h - delta]],
            fmt="o",
            ecolor="#7f8c8d",
            elinewidth=2,
            capsize=5,
            markersize=8,
            color=color,
            alpha=0.8
        )
        
        # Add delta label
        sig = "*" if (ci_l > 0 or ci_h < 0) else ""
        ax_forest.text(delta + 100 if delta > 0 else delta - 100, i, f"{delta:.0f}{sig}",
                      ha="right" if delta < 0 else "left", va="center", fontsize=8)

    ax_forest.axvline(x=0, color="black", linestyle="-", linewidth=2, alpha=0.5)
    ax_forest.set_yticks(y_positions)
    ax_forest.set_yticklabels(labels, fontsize=10)
    ax_forest.set_xlabel("Delta (ReAct − StateGraph)", fontsize=11, fontweight="bold")
    ax_forest.set_title("Summary: Effect Sizes + 95% CI", fontsize=12, fontweight="bold")
    ax_forest.grid(True, alpha=0.3)
    ax_forest.set_axisbelow(True)
    
    # ========== RIGHT: Latency Violin ==========
    data_to_plot = [latency_data["react"], latency_data["stategraph"]]
    
    parts = ax_violin.plot(
        [], [], "b"  # Placeholder, we'll use violinplot
    )
    
    parts = ax_violin.violinplot(
        data_to_plot,
        positions=[1, 2],
        widths=0.7,
        showmeans=True,
        showmedians=True,
        showextrema=True
    )
    
    colors_violin = ["#3498db", "#e74c3c"]
    for pc, color in zip(parts["bodies"], colors_violin):
        pc.set_facecolor(color)
        pc.set_edgecolor("black")
        pc.set_alpha(0.7)
    
    for partname in ("cb_means", "cmedians"):
        if partname in parts:
            vp = parts[partname]
            vp.set_edgecolor("black")
            vp.set_linewidth(2)
    
    ax_violin.set_xticks([1, 2])
    ax_violin.set_xticklabels(["ReAct", "StateGraph"], fontsize=11, fontweight="bold")
    ax_violin.set_ylabel("E2E Latency (ms)", fontsize=11, fontweight="bold")
    ax_violin.set_title("Latency Distribution", fontsize=12, fontweight="bold")
    
    # Add statistics
    import numpy as np
    stats_text = (
        f"ReAct: {np.mean(latency_data['react']):.0f}ms\n"
        f"StateGraph: {np.mean(latency_data['stategraph']):.0f}ms"
    )
    ax_violin.text(
        0.5, -0.2, stats_text,
        transform=ax_violin.transAxes,
        ha="center",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5)
    )
    
    # Overall title
    fig.suptitle(
        "Figure 4: Combined Summary — ReAct vs StateGraph",
        fontsize=14,
        fontweight="bold",
        y=1.02
    )
    
    plt.tight_layout()
    plt.savefig(save_path.replace(".svg", ""), dpi=300, bbox_inches="tight")
    plt.savefig(save_path.replace(".png", ".svg"), bbox_inches="tight")
    plt.close()
    
    print(f"Generated: {save_path}")


def main():
    """Main entry point."""
    print(f"Loading metrics from {METRICS_FILE}...", file=sys.stderr)
    metrics = load_metrics()
    
    by_run = metrics.get("by_run", [])
    experiment_stats = metrics.get("experiment_statistics", {})
    
    print("Extracting data...", file=sys.stderr)
    latency_data = extract_latency_data(by_run)
    steps_data = extract_steps_data(by_run)
    bootstrap_data = extract_bootstrap_data(experiment_stats)
    
    print(f"\nData summary:", file=sys.stderr)
    print(f"  ReAct runs: {len(latency_data['react'])}", file=sys.stderr)
    print(f"  StateGraph runs: {len(latency_data['stategraph'])}", file=sys.stderr)
    print(f"  Bootstrap metrics: {len(bootstrap_data)}", file=sys.stderr)
    
    print(f"\nGenerating figures in {FIGURES_DIR}...", file=sys.stderr)
    
    # Figure 1: Violin Plot
    generate_violin_plot(
        latency_data,
        str(FIGURES_DIR / "figure_1_latency_violin.png")
    )
    
    # Figure 2: Box Plot
    generate_box_plot(
        steps_data,
        str(FIGURES_DIR / "figure_2_steps_box.png")
    )
    
    # Figure 3: Forest Plot
    generate_forest_plot(
        bootstrap_data,
        str(FIGURES_DIR / "figure_3_forest_plot.png")
    )
    
    # Figure 4: Combined Summary
    generate_combined_summary(
        latency_data,
        bootstrap_data,
        str(FIGURES_DIR / "figure_4_combined_summary.png")
    )
    
    print(f"\n✅ All figures generated successfully!", file=sys.stderr)
    print(f"Output directory: {FIGURES_DIR}", file=sys.stderr)


if __name__ == "__main__":
    main()
