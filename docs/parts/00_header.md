# LangGraph vs. ReAct: An Engineering Benchmark

## Stateful Orchestration in Short-Horizon Conversational Workflows

---

### Abstract

**Question:** Does orchestration architecture affect the performance of conversational agents?

**Method:** Paired comparison of two orchestration strategies — a ReAct-style cyclic loop and a LangGraph StateGraph — across **45 simulated dialogue scenarios**, each executed **three times per strategy** (N = 135 paired runs). All experimental conditions (model, prompts, tools, simulator) are held constant.

**Result (summary):**

- **Latency:** ReAct completes dialogues ~2 seconds faster on average (mean delta: −2023 ms; 95% CI: [−3847 ms, −757 ms]).
- **Outcome metrics:** task completion and entity coverage show **no statistically significant differences** between architectures.
- **Efficiency metrics:** steps and token usage are statistically indistinguishable.

**Interpretation:**  
For **short-horizon linear workflows**, orchestration architecture primarily affects **latency**, while outcome quality and efficiency remain comparable.

Findings are specific to short-horizon, constrained dialogue settings.

Full statistical analysis is presented in §4.

---

## Executive Summary

### Key Findings

| Metric | ReAct | StateGraph | Delta | 95% CI | p-value | Significant? |
| ------ | ----- | ---------- | ----- | ------ | ------- | ------------ |
| **E2E Latency (per dialogue)** | 14019ms | 15539ms | **−2023ms** | [−3847, −757] | 0.050 | ⚠️ Borderline |
| **Message Latency (per step)** | 963ms | 1553ms | **−568ms** | [−586, −550] | 8.2×10⁻²⁴ | ✅ Yes |
| **Simulator Latency (per step)** | 866ms | 1100ms | **−168ms** | [−201, −135] | 8.5×10⁻¹⁸ | ✅ Yes |
| **Orchestration (per step)** | 0.73ms | 3.22ms | **−2.28ms** | [−2.52, −2.11] | 5.7×10⁻²¹ | ✅ Yes |
| **Steps (per dialogue)** | 7.77 | 7.81 | **0.0** | [−1, +1] | 0.85 | ❌ No |
| **Tokens (per dialogue)** | 11,952 | 11,676 | **−126** | [−1666, +1437] | 0.99 | ❌ No |
| **Success Rate** | 83.0% | 80.0% | — | — | 0.52 (McNemar) | ❌ No |
| **Coverage Final** | 1.10 | 1.07 | **0.0** | [−0.18, +0.22] | 0.59 | ❌ No |

**Takeaway:** For linear slot-filling dialogues, ReAct shows lower latency without statistically significant differences in outcome quality or efficiency.

### Practical Recommendations

**Use ReAct when:**
✅ Linear workflows (A → B → C)
✅ Short horizon (<10 steps)
✅ Simple tool use (1-2 tools)
✅ Latency-critical UX
✅ Rapid prototyping

**Use StateGraph when:**
✅ Branching logic (if-else based on data)
✅ Long conversations (10-20+ steps)
✅ Complex state (track multiple variables)
✅ Tool orchestration (3+ tools with dependencies)
✅ Human handoffs (pause/resume, async workflows)

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Experimental Design](#2-experimental-design)
3. [Metrics](#3-metrics)
4. [Results](#4-results)
5. [Discussion](#5-discussion)
6. [Threats to Validity](#6-threats-to-validity)
7. [Conclusion](#7-conclusion)

---
