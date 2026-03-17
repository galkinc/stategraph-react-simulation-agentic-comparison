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

# 01. Introduction

## 1.1 Motivation

Modern LLM agent frameworks increasingly rely on **orchestration layers** to manage multi-step workflows, tool calls, and conversational state.

Two widely used orchestration patterns are:

- **ReAct-style cyclic loops**, where the model iteratively reasons and acts within a simple control loop.
- **Graph-based orchestration frameworks** (e.g., LangGraph), which represent workflows as explicit state machines.

In practice, engineers frequently debate whether graph-based orchestration introduces unnecessary complexity and runtime overhead compared to simpler loop-based implementations.

However, **empirical comparisons isolating orchestration architecture as the only variable remain rare**. Most discussions conflate architecture with prompt design, tool configuration, or task structure.

This study attempts a **controlled comparison** between these two orchestration strategies while keeping all other experimental factors constant.

---

## 1.2 Research Questions

The study evaluates whether orchestration architecture affects conversational agent performance in **short-horizon information-extraction dialogues**.

**RQ1 — Outcome quality**  
Does orchestration architecture affect **task completion or information extraction coverage**?

**RQ2 — Efficiency**  
Does orchestration architecture affect **dialogue length, token usage, or runtime latency**?

**RQ3 — Stability**  
Does explicit state management affect **decision instability** during dialogue termination?

The corresponding statistical hypotheses are defined in §2.

---

## 1.3 Experimental Setup (Overview)

The experiment compares two implementations of the same conversational agent:

- **ReAct loop**
- **LangGraph StateGraph**

Both implementations share:

- identical **LLM model** (Claude 3 Haiku via AWS Bedrock)
- identical **prompts**
- identical **tool and infrastructure interface**
- identical **patient simulator**
- identical **task scenarios**
- identical **stopping criteria**

The only independent variable is **orchestration architecture**.

The dataset contains:

- **45 simulated dialogue scenarios**
- **3 runs per scenario per architecture**
- **135 paired runs**

Detailed experimental design is described in §2.

---

## 1.4 Scope and Boundaries

This study focuses on a **specific class of conversational workflows**.

### Covered

- **Task type:** information-extraction (slot-filling) dialogues  
- **Workflow structure:** primarily linear  
- **Dialogue horizon:** short (median ~6–7 steps)  
- **Model:** Claude 3 Haiku  
- **Metrics:** system-level performance (latency, tokens, steps, completion)

### Not Covered

The study does **not evaluate**:

- clinical correctness of extracted entities
- complex multi-branch workflows
- multi-model comparisons
- real human participants
- monetary cost analysis

**Data quality:** Four StateGraph runs (3% of total) have missing latency measurements due to execution errors. These runs are excluded from latency analysis but included in success and coverage metrics.

These limitations are discussed further in §6.

---

## 1.5 Key Definitions

| Term | Definition |
|-----|-----|
| **Step** | One agent turn and the corresponding simulator response |
| **ReAct** | Cyclic loop: `reason → act → observe → repeat` |
| **StateGraph** | Explicit state machine implementation using LangGraph |
| **Coverage** | Fraction of target entities extracted (`collected / target`). Values may exceed 1.0 when the agent extracts more entities than the target count. |
| **Success** | Dialogue where `agent_done = true` and coverage ≥ 0.2 |
| **Decision Instability** | Number of `agent_done` flag transitions during a dialogue |

Formal metric definitions are provided in §3.

---

## 1.6 Document Structure

| Section | Description |
|-------|-------|
| **§1 Introduction** | Motivation, research questions, scope |
| **§2 Experimental Design** | Hypotheses, variables, methodology |
| **§3 Metrics** | Metric definitions and formulas |
| **§4 Results** | Statistical analysis |
| **§5 Discussion** | Interpretation and implications |
| **§6 Threats to Validity** | Study limitations |
| **§7 Conclusion** | Summary and future work |
# 02. Experimental Design

## 2.1 Research Question

This study evaluates whether orchestration architecture influences the
behavior of conversational agents in short-horizon slot-filling workflows.

The comparison focuses on two strategies:

- **ReAct loop** — a cyclic reasoning–action pattern
- **LangGraph StateGraph** — an explicit state-machine orchestration

The goal is to determine whether architectural differences lead to measurable
changes in dialogue outcomes, efficiency, or latency.

---

## 2.2 Hypotheses

All hypotheses use a **paired design**, where each scenario is executed under
both orchestration strategies.

### Outcome Hypotheses

| # | Null Hypothesis | Test |
| --- | --- | --- |
| H1 | Success probability is equal between strategies | McNemar |
| H2 | Final entity coverage is equal | Wilcoxon signed-rank |

### Efficiency Hypotheses

| # | Null Hypothesis | Test |
| --- | --- | --- |
| H3 | Dialogue length (steps) is equal | Wilcoxon |
| H4 | Token consumption is equal | Wilcoxon |
| H5 | End-to-end latency is equal | Wilcoxon |
| H6 | Decision instability is equal | Wilcoxon |

### Latency Hypothesis

| # | Null Hypothesis | Test |
| --- | --- | --- |
| H7 | Time-to-first-token distributions are equal | Wilcoxon |

---

## 2.3 Experimental Setup

The independent variable is **orchestration architecture**.

Two implementations are evaluated:

- **ReAct:** cyclic reasoning loop
- **StateGraph:** explicit state machine implemented in LangGraph

All other conditions remain fixed:

- identical LLM model
- identical prompts and tool schemas
- identical scenario set
- identical patient simulator
- identical stopping criteria

This design ensures that any measured differences arise from
orchestration architecture rather than model or prompt variations.

---

## 2.4 Paired Execution Design

Each scenario is executed once under each orchestration strategy,
forming a paired observation.

`scenario_i → run(ReAct)`
`scenario_i → run(StateGraph)`


This design reduces variance caused by scenario difficulty and
enables within-scenario comparisons.

The experiment consists of:

- **45 unique scenarios**
- **3 execution batches**

Total:

- **135 paired observations**
- **270 dialogue runs**

Batching is used to reduce temporal variance in infrastructure load.

---

## 2.5 Scenario Construction

Scenarios are derived from **real doctor–patient dialogue transcripts**.

Transcripts are processed with **AWS Comprehend Medical** to extract
clinical entities and construct structured patient profiles.

Each scenario includes:

1. **Patient profile**
   - symptoms
   - medical history
   - medications
   - relevant conditions

2. **Behavioral constraints**
   - topics the patient may discuss
   - facts that cannot be asserted

The agent's task is a **slot-filling dialogue** where information must be
collected to produce a structured action payload.

Target entities are determined from the transcript analysis.

---

## 2.6 Patient Simulator

User responses are generated by an **LLM-based patient simulator**
grounded in the structured patient profile.

The simulator receives:

- the agent’s question
- the patient profile

and produces a short response constrained by the scenario specification.

Simulator responses are restricted to facts contained in the profile.
Out-of-scope questions produce a fallback response.

### Simulator Limitations

The patient simulator:

- follows structured profiles with limited ambiguity  
- does not introduce adversarial or inconsistent responses  
- does not model user interruptions or corrections  

This may favor simpler cyclic strategies in latency-sensitive settings.

---

## 2.7 Dialogue Termination

A dialogue terminates when either condition is met:

### Definition of Done

`agent_done = true AND coverage ≥ dod_threshold`

### Step Limit

`steps ≥ max_steps`

### Coverage Override

The system verifies the `done` signal against the measured coverage.
`should_stop = output.done AND coverage.threshold_met`

---

## 2.8 Coverage Calculation

Runtime coverage is calculated using a **count-based metric**:
`coverage = collected_entities / target_entities`

where:

- collected_entities = non-empty fields in the action payload
- target_entities = entities extracted from the reference transcript

This approach ensures deterministic evaluation without semantic
matching thresholds.

Coverage values may exceed **1.0** if more entities are extracted
than present in the original transcript.

Semantic entity matching is performed separately for analysis and
does not influence runtime termination.

---

## 2.9 Step Definition

A **step** is defined as one full dialogue exchange:
`step = agent turn + patient response`

Internal orchestration operations (routing, reasoning traces,
state updates) are excluded.

This definition aligns the metric with the observable dialogue flow.

---

## 2.10 Statistical Analysis

Binary outcomes (success) are compared using the **McNemar test**.

Continuous paired metrics (steps, tokens, latency, coverage,
decision instability) are analyzed using the
**Wilcoxon signed-rank test**.

Confidence intervals for median differences are estimated using
**bootstrap resampling (5000 iterations)**.

Effect size is reported using **rank-biserial correlation**.

---

## 2.11 Data Availability

Scenario generation procedures and analysis code are publicly
available in the repository.

Aggregate experiment metrics are included in
`data/output/aggregate_metrics.json`.

Raw dialogue transcripts cannot be fully distributed due to
dataset licensing constraints but are available upon request.

---

This experimental design prioritizes **internal validity**
(controlled comparison) over external generalization.
Limitations are discussed in §06 Threats to Validity.
# 03. Metrics

## 3.1 Overview

The experiment records metrics at multiple aggregation levels:

```text
Step → Dialogue Run → Scenario → Experiment
```

A **step** corresponds to one agent turn: a model response followed by a simulator reply (if the dialogue continues).
All step-level metrics are recorded during execution and later aggregated into run-, scenario-, and experiment-level statistics.

Metrics are collected **externally to the agent state** and do not affect strategy execution.
Instrumentation records events during runtime but does not pass metrics through the agent graph or prompt context.

Some metrics are collected **during streaming generation** (e.g., time-to-first-token), while others become available **after the model response completes** (e.g., token usage).

All reported statistics are computed over **135 experimental runs** (45 scenarios × 3 batches).

---

## 3.2 Step-Level Metrics

Step-level metrics capture latency, token usage, message properties, and information extraction at each dialogue turn.

### Latency Metrics

| Metric                 | Unit | Definition                                            | Purpose                                         |
| ---------------------- | ---- | ----------------------------------------------------- | ----------------------------------------------- |
| `ttft_ms`              | ms   | Time to first token during model streaming            | Proxy for perceived responsiveness              |
| `message_ms`           | ms   | Duration of the model response generation             | Measures LLM inference time                     |
| `simulator_latency_ms` | ms   | Duration of the patient simulator call                | Measures simulator processing                   |
| `e2e_per_step_ms`      | ms   | End-to-end latency for the step                       | Total runtime cost per turn                     |
| `orchestration_ms`     | ms   | `e2e_per_step_ms − message_ms − simulator_latency_ms` | Residual runtime after model and simulator time |

`orchestration_ms` represents the remaining latency after subtracting model and simulator time from the end-to-end step latency.

---

### Token Metrics

| Metric          | Unit   | Definition                     | Purpose           |
| --------------- | ------ | ------------------------------ | ----------------- |
| `input_tokens`  | tokens | Tokens sent to the model       | Input cost        |
| `output_tokens` | tokens | Tokens generated by the model  | Generation cost   |
| `total_tokens`  | tokens | `input_tokens + output_tokens` | Total token usage |

Token counts are obtained from the model provider after the response completes.

---

### Message Metrics

| Metric               | Unit  | Definition                                               | Purpose                             |
| -------------------- | ----- | -------------------------------------------------------- | ----------------------------------- |
| `message_word_count` | words | Word count of the agent question                         | Measures prompt length              |
| `patient_word_count` | words | Word count of simulator reply                            | Dialogue verbosity                  |
| `is_compliant`       | {0,1} | Whether agent message satisfies the 5–12 word constraint | Checks adherence to dialogue policy |

---

### Coverage Metrics

| Metric               | Range   | Definition                                 | Purpose                        |
| -------------------- | ------- | ------------------------------------------ | ------------------------------ |
| `coverage`           | [0,∞)   | `collected_entities / target_entities`     | Measures information extracted |
| `coverage_collected` | integer | Count of extracted entities                | Extraction volume              |
| `coverage_target`    | integer | Count of entities in the reference profile | Target information size        |

Coverage is **count-based** rather than content-based.
Values may exceed 1.0 if more entities are extracted than present in the reference profile.

---

### Decision Metrics

| Metric       | Definition                            | Purpose                        |
| ------------ | ------------------------------------- | ------------------------------ |
| `agent_done` | LLM-generated completion flag         | Indicates model intent to stop |
| `final_done` | `agent_done AND coverage ≥ threshold` | Final termination condition    |

---

## 3.3 Run-Level Metrics

Run-level metrics aggregate step metrics for a single dialogue execution.

### Outcome Metric

| Metric    | Definition                                                        |
| --------- | ----------------------------------------------------------------- |
| `success` | Dialogue ends with `coverage ≥ threshold` and a non-empty payload |

### Dialogue Efficiency

| Metric               | Definition                      |
| -------------------- | ------------------------------- |
| `total_steps`        | Number of dialogue turns        |
| `coverage_final`     | Coverage at the final step      |
| `coverage_per_step`  | `coverage_final / total_steps`  |
| `coverage_per_token` | `coverage_final / total_tokens` |

### Stability

| Metric                 | Definition                                                         |
| ---------------------- | ------------------------------------------------------------------ |
| `decision_instability` | Number of transitions between 0 and 1 in the `agent_done` sequence |

---

## 3.4 Scenario-Level Aggregates

Scenario-level statistics average run-level metrics across all runs of the same scenario and strategy.

| Metric                       | Definition                       |
| ---------------------------- | -------------------------------- |
| `success_rate`               | Mean success over runs           |
| `steps_mean`                 | Mean number of dialogue steps    |
| `latency_mean`               | Mean end-to-end dialogue latency |
| `message_latency_mean`       | Mean model response latency      |
| `simulator_latency_mean`     | Mean simulator latency           |
| `orchestration_latency_mean` | Mean residual latency            |

---

## 3.5 Experiment-Level Comparison

Each scenario is executed with both strategies.
Comparisons are performed using paired metrics:

```
delta = metric_react − metric_stategraph
```

Negative values indicate lower values for ReAct; positive values indicate lower values for StateGraph.

---

## 3.6 Statistical Analysis

The following statistical tests are used to evaluate differences between strategies.

| Test                           | Metric Type                 | Purpose                                        |
| ------------------------------ | --------------------------- | ---------------------------------------------- |
| McNemar test                   | Binary outcomes (`success`) | Tests paired differences in success rate       |
| Wilcoxon signed-rank           | Continuous metrics          | Tests paired median differences                |
| Bootstrap confidence intervals | Delta estimates             | Quantifies uncertainty of median differences   |
| Rank-biserial correlation      | Effect size                 | Measures win–loss imbalance between strategies |

---

## 3.7 Hypothesis–Metric Mapping

| Hypothesis                | Metric                 | Test     |
| ------------------------- | ---------------------- | -------- |
| H1 Outcome                | `success`              | McNemar  |
| H2 Information extraction | `coverage_final`       | Wilcoxon |
| H3 Dialogue efficiency    | `total_steps`          | Wilcoxon |
| H4 Token usage            | `total_tokens`         | Wilcoxon |
| H5 Latency                | `e2e_total_ms`         | Wilcoxon |
| H6 Stability              | `decision_instability` | Wilcoxon |
| H7 UX responsiveness      | `ttft_ms`              | Wilcoxon |

---

## 3.8 Implementation Details

For detailed formulas, data flow diagrams, and calculation examples, see the source code:
`metrics_aggregator/run_metrics.py` and `src/strategies/`.
# 04. Results

*Delta = ReAct − StateGraph (negative value indicates ReAct is faster or lower).*

---

## 4.1 Key Findings

This section reports empirical results of the controlled comparison between `ReAct` and `StateGraph` architectures across `45` simulated dialogue scenarios (`135` paired runs).

**Experimental Scope:**

- 45 scenarios
- 3 batches
- 135 paired runs
- same prompts and done conditions
- same simulator
- same LLM

### Summary Statistics

| Metric | ReAct Mean | ReAct Median | StateGraph Mean | StateGraph Median | Delta | 95% CI | p-value | Effect Size |
| ------ | --------- | ----------- | --------------- | ----------------- | ----- | ------ | ------- | ----------- |
| **E2E Latency (per dialogue)** | 14019.29ms | 12482.30ms | 15538.67ms | 14366.77ms | **-2023ms** | [-3847, -757] | 0.05 | -0.21 (small) |
| **Message Latency (per step)** | 963.18ms | 925.94ms | 1553.15ms | 1491.50ms | **-568ms** | [-586, -550] | 8.21e-24 | -0.96 (large) |
| **Simulator Latency (per step)** | 866.00ms | 964.18ms | 1100.32ms | 1121.64ms | **-168ms** | [-201, -135] | 8.48e-18 | -0.78 (large) |
| **Orchestration (per step)** | 0.73ms | 0.54ms | 3.22ms | 2.76ms | **-2ms** | [-3, -2] | 5.66e-21 | -0.98 (large) |
| **Steps (per dialogue)** | 7.77 | 6 | 7.81 | 7 | **0** | [-1, 1] | 0.85 | -0.11 (small) |
| **Tokens (per dialogue)** | 11952 | 8435 | 11676 | 9375 | **-126** | [-1666, 1437] | 0.99 | -0.05 (negligible) |
| **Success Rate** | 83.0% | — | 80% | — | — | — | 0.52 (McNemar) | — |
| **Coverage Final** | 1.10 | 1 | 1.07 | 1 | **0** | [-0.18, +0.22] | 0.59 | -0.01 (negligible) |

**Notes:**

- Values shown: Mean (arithmetic average). For full distributions, see §4.2–4.4.
- All statistics computed over N = 135 paired runs (45 scenarios × 3 batches).
- Effect size (rank-biserial): |r| < 0.1 (negligible), 0.1–0.3 (small), 0.3–0.5 (medium), ≥ 0.5 (large).
- Statistical tests: Wilcoxon signed-rank for continuous metrics, McNemar for success rate.
- 95% CI: If confidence interval includes 0, we cannot reject the null hypothesis (no difference) at 95% confidence level.

**Key Observations:**

1. **ReAct shows ~2s lower E2E latency per dialogue** - driven primarily by differences in message and simulator latency (`~600ms per step` combined), while pure orchestration overhead remains negligible (`~2–3ms` per step). Although ReAct shows lower mean latency, StateGraph wins more individual runs (61%). This pattern is consistent with a right-skewed latency distribution where StateGraph has a longer tail of slow outliers, which increases the mean despite similar medians.
2. **No statistically significant difference in quality** - success rate and coverage are statistically indistinguishable
3. **Same efficiency** - steps and tokens distributions are statistically indistinguishable
4. **Message and simulator latency measurements differ significantly between strategies, though part of the difference may be attributable to measurement boundaries within the orchestration implementation.**

> Note: Latency Overhead is architectural, not from business logic (orchestration ~2ms). For more details see §5.2.

---

## 4.2 Primary Outcome: Latency

### E2E Total Latency per Dialogue

**Delta: −2023ms (95% CI: [−3847, −757])**

ReAct completes dialogues **~2 seconds faster** than StateGraph on average.

| Strategy | Mean (ms) | Median (ms) |
| -------- | --------- | ----------- |
| ReAct | 14019 | 12482 |
| StateGraph | 15539 | 14367 |

**Wilcoxon signed-rank test:** W = 3698.0, p = 0.050 (borderline; interpretation should be treated with caution)

**Win rate:** ReAct wins 53/135 (39%), StateGraph wins 82/135 (61%)

**Rank-biserial correlation:** −0.21 (small effect size, favors ReAct)

**Interpretation:** ReAct shows a small but measurable advantage in end-to-end dialogue completion time. See §5.2 for breakdown of latency components.

---

### Latency Breakdown by Component

#### Message Latency (LLM Call)

**Delta: −568ms per step (95% CI: [−586, −550])**

| Strategy | Mean (ms) | Median (ms) |
| --- | --- | --- |
| ReAct | 963.18 | 925.94 |
| StateGraph | 1553.15 | 1491.50 |

**Wilcoxon signed-rank test:** W = 9.0, p = 8.2×10⁻²⁴ (highly significant)

**Win rate:** ReAct wins 3/135 (2%), StateGraph wins 132/135 (98%)

**Rank-biserial:** −0.96 (very large effect size)

> **Note:** This difference includes both LLM call time and implementation artifacts (validation timing differs between strategies). Latency was measured end-to-end within each step to capture real orchestration overhead, not just pure LLM computation time. See Discussion §5.3 for detailed analysis.

---

#### Simulator Latency (Patient Response)

**Delta: −168ms per step (95% CI: [−201, −135])**

| Strategy | Mean (ms) | Median (ms) |
| --- | --- | --- |
| ReAct | 866.00 | 964.18 |
| StateGraph | 1100.32 | 1121.64 |

**Wilcoxon signed-rank test:** W = 450.0, p = 8.5×10⁻¹⁸ (highly significant)

**Win rate:** ReAct wins 14/135 (11%), StateGraph wins 111/135 (89%)

**Rank-biserial:** −0.78 (large effect size)

> **Note:** Simulator is identical code in both strategies (see §2.6). The observed latency difference likely results from timing measurement boundaries within the LangGraph orchestration layer, rather than simulator computation itself. StateGraph's async queue and state serialization add overhead that affects when the timer starts/stops. See Discussion §5.2 for detailed analysis.

---

#### Orchestration Overhead

**Delta: −2.28ms per step (95% CI: [−2.52, −2.11])**

| Strategy | Mean (ms) | Median (ms) |
| --- | --- | --- |
| ReAct | 0.73 | 0.54 |
| StateGraph | 3.22 | 2.76 |

**Wilcoxon signed-rank test:** W = 124.0, p = 5.7×10⁻²¹ (highly significant)

**Win rate:** ReAct wins 1/135 (0.8%), StateGraph wins 124/135 (99%)

**Rank-biserial:** −0.98 (very large effect size)

> **Interpretation:** Business logic overhead (validation, termination check, metric recording) is minimal in both strategies (~0.5–3ms). This confirms that latency difference comes from **infrastructure** (LLM call + async queue), not business logic. See §3.1 for metric definition.

---

## 4.3 Efficiency: Steps & Tokens

### Dialogue Length (Steps)

**Delta: 0.0 steps (95% CI: [−1, +1])**

| Strategy | Mean | Median | Min | Max |
| --- | --- | --- | --- | --- |
| ReAct | 7.77 | 6 | 1 | 15 |
| StateGraph | 7.81 | 7 | 1 | 15 |

*Note: Max steps capped at 15 (see §2.7 for termination criteria).*

**Wilcoxon signed-rank test:** W = 2519.5, p = 0.85 (no significant difference)

**Win rate:** ReAct 45/135 (33%), StateGraph 56/135 (41%), Ties 34/135 (25%)

**Rank-biserial:** −0.11 (small effect size)

> **Conclusion:** Both strategies require the **same number of steps** to complete dialogues. Architecture does not affect dialogue length.

---

### Token Consumption

**Delta: −126 tokens (95% CI: [−1666, +1437])**

| Strategy | Mean (total/dialogue) | Mean (per step) |
| -------- | ---------------------------- | ---------------------- |
| ReAct | 11952 | 1538 |
| StateGraph | 11676 | 1494 |

**Wilcoxon signed-rank test:** W = 4382.0, p = 0.99 (no significant difference)

**Win rate:** ReAct 63/135 (48%), StateGraph 69/135 (52%), Ties 3/135

**Rank-biserial:** −0.05 (negligible effect size)

> **Conclusion:** StateGraph does **not consume more tokens** despite additional `evaluate_stop` node. This node uses pure logic (no LLM call), so token usage remains identical. See §5.4 for detailed analysis.

---

## 4.4 Quality: Success & Coverage

### Dialogue Success Rate

**McNemar test:** χ² = 9.0, p = 0.52 (no significant difference)

| Strategy | Success Rate |
| --- | --- |
| ReAct | 83.0% |
| StateGraph | 80% |

> **Note:** Success defined as `agent_done=true AND coverage >= dod_threshold (0.2)`. Both strategies achieve success rates ≥80% with no statistically significant difference. See §2.7 for termination criteria definition.

---

### Information Extraction (Coverage)

**Delta: 0.0 (95% CI: [−0.18, +0.22])**

| Strategy | Mean Final Coverage |
| --- | --- |
| ReAct | 1.10 |
| StateGraph | 1.07 |

**Wilcoxon signed-rank test:** W = 1468.5, p = 0.59 (no significant difference)

**Win rate:** ReAct 39/135 (49%), StateGraph 40/135 (50%), Ties 56/135

**Rank-biserial:** −0.01 (negligible effect size)

> **Note:** Coverage is count-based (entities collected / entities target), not content-based. Values may exceed 1.0 when the agent extracts more entities than the target count from the original transcript. See §2.8 and §3.2 for definition. Post-hoc embedding-based quality analysis is performed separately.

---

## 4.5 Stability: Decision Instability

### Agent Mind-Changing

**Metric:** Count of `agent_done` flag flips (0→1 or 1→0) during dialogue.

| Strategy | Mean | Median |
| --- | --- | --- |
| ReAct | 0.91 | 1 |
| StateGraph | 0.87 | 1 |

> **Observation:** Decision instability is common — most dialogues (89%) show exactly one `agent_done` flag flip. This reflects the normal termination pattern: agent says `done=false` during dialogue, then `done=true` at completion. The metric captures this single expected flip, not erratic behavior. See §5.5 for interpretation.

---

## 4.6 Derived Metrics

*Derived metrics are diagnostic and not part of primary hypotheses. See §3.5 for formulas and interpretation.*

### Coverage per Step

**Information acquired per dialogue turn:**

| Strategy | Mean Coverage/Step |
| --- | --- |
| ReAct | 0.219 |
| StateGraph | 0.208 |

> **Interpretation:** Both strategies acquire information at the same rate per step.

---

### Coverage per Token

**Information acquired per token spent:**

| Strategy | Mean Coverage/Token |
| --- | --- |
| ReAct | 0.00018 |
| StateGraph | 0.00017 |

> **Interpretation:** Token efficiency is identical between strategies.

---

### Coverage Velocity

**Rate of information acquisition (step-to-step change):**

| Strategy | Mean Velocity |
| --- | --- |
| ReAct | 0.141 |
| StateGraph | 0.120 |

> **Note:** Velocity varies significantly across scenarios (some require rapid extraction, others gradual). See §3.5 for formula: `velocity[i] = coverage[i] − coverage[i−1]`.

---

## 4.7 Per-Scenario Analysis

*Per-scenario delta analysis (|delta| > 1000ms) and qualitative dialogue excerpts are provided in Discussion §5.6.*

**Aggregate finding:** Per-scenario variation exists but shows no systematic pattern favoring either architecture for outcome metrics (success, coverage). Latency delta is consistent across scenarios (~600ms/step overhead for StateGraph).

> **Note:** Full per-scenario data available in `data/output/aggregate_metrics.json` under `by_scenario` and `scenario_comparison` keys.

---

## 4.8 Summary of Statistical Tests

### McNemar Test (Success Rate)

| Metric | χ² | p-value | Significant (α=0.05)? |
| ------ | --- | ------- | -------------------- |
| Success | 9.0 | 0.52 | ❌ No |

*Note: McNemar test computed with exact method (statsmodels). χ²=9.0 with p=0.52 occurs when discordant pairs are balanced (b≈c), indicating no systematic difference between strategies.*

---

### Wilcoxon Signed-Rank Test (Continuous Metrics)

| Metric | W | p-value | Significant? | Effect Size |
| ------ | --- | ------- | ------------ | ----------- |
| Steps | 2519.5 | 0.85 | ❌ No | −0.11 (small) |
| Tokens | 4382.0 | 0.99 | ❌ No | −0.05 (negligible) |
| Latency | 3698.0 | 0.050 | ⚠️ Borderline | −0.21 (small) |
| Message Latency | 9.0 | 8.2×10⁻²⁴ | ✅ Yes | −0.96 (large) |
| Simulator Latency | 450.0 | 8.5×10⁻¹⁸ | ✅ Yes | −0.78 (large) |
| Orchestration | 124.0 | 5.7×10⁻²¹ | ✅ Yes | −0.98 (large) |
| Coverage | 1468.5 | 0.59 | ❌ No | −0.01 (negligible) |

---

### Bootstrap Confidence Intervals (Delta = ReAct − StateGraph)

| Metric | Delta | 95% CI Low | 95% CI High | CI Includes 0? |
| ------ | ----- | ---------- | ----------- | -------------- |
| Steps | 0.0 | −1.0 | 1.0 | ✅ Yes |
| Tokens | −126 | −1666 | 1437 | ✅ Yes |
| Latency | −2023 | −3847 | −757 | ❌ No |
| Message Latency | −568 | −586 | −550 | ❌ No |
| Simulator Latency | −168 | −201 | −135 | ❌ No |
| Orchestration | −2.28 | −2.52 | −2.11 | ❌ No |
| Coverage | 0.0 | −0.18 | 0.22 | ✅ Yes |

*Note: 95% CI computed via bootstrap (5000 resamples). If CI includes 0, we cannot reject the null hypothesis (no difference) at 95% confidence level.*

---

### Win/Loss Statistics

| Metric | Wins (ReAct) | Losses (ReAct) | Ties | Win Rate | Rank-Biserial |
| ------ | ------------ | -------------- | ---- | -------- | ------------- |
| Steps | 45 | 56 | 34 | 0.45 | −0.11 |
| Tokens | 63 | 69 | 3 | 0.48 | −0.05 |
| Latency | 53 | 82 | 0 | 0.39 | −0.21 |
| Message Latency | 3 | 132 | 0 | 0.02 | −0.96 |
| Simulator Latency | 14 | 111 | 0 | 0.11 | −0.78 |
| Orchestration | 1 | 124 | 0 | 0.01 | −0.98 |
| Coverage | 39 | 40 | 56 | 0.49 | −0.01 |

*Note: Win = ReAct is lower (for latency/steps) or higher (for success/coverage). Rank-biserial = (wins − losses) / (wins + losses).*

---

## 4.9 Visual Summary

### Figure 1: E2E Latency Distribution (Violin Plot)

![Figure 1: E2E Latency Distribution](../figures/figure_1_latency_violin.png)

**Purpose:** Shows the full distribution of E2E latency for both strategies.

**Key observations:**

- ReAct distribution is shifted left (faster) compared to StateGraph
- Both distributions show right skew (some dialogues take longer)
- Overlap indicates many dialogues have similar latency, but StateGraph has longer tail

---

### Figure 2: Steps Distribution (Box Plot)

![Figure 2: Steps Distribution](../figures/figure_2_steps_box.png)

**Purpose:** Shows the spread of dialogue lengths (steps) for both strategies.

**Key observations:**

- Median steps are similar (ReAct: 6, StateGraph: 7)
- Max steps (15) are outliers — loop protection working correctly
- IQR overlap confirms no significant difference in dialogue length

---

### Figure 3: Forest Plot (Effect Sizes + 95% CI)

![Figure 3: Forest Plot](../figures/figure_3_forest_plot.png)

**Purpose:** Visualizes effect sizes (delta) with confidence intervals for all metrics.

**Key observations:**

- **Red points** = Significant effect (CI excludes 0)
- **Gray points** = Not significant (CI includes 0)
- Latency metrics show significant negative delta (ReAct faster)
- Steps, tokens, coverage show no significant difference

---

### Figure 4: Combined Summary

![Figure 4: Combined Summary](../figures/figure_4_combined_summary.png)

**Purpose:** Single-figure summary combining forest plot (left) and latency distribution (right).

**Use case:** Quick executive summary — one glance shows both effect sizes and distribution shape.

---

**Figure generation:** All figures generated by `scripts/generate_figures.py`. PNG (300 DPI) and SVG formats available in `docs/figures/`.

---

## 4.10 Data Availability

**Source:** `data/output/aggregate_metrics.json` (135 runs, 45 scenarios, 2 strategies)

**Reproducibility:** Script to generate tables from raw data: `scripts/generate_results_tables.py`

---

*For metric definitions and formulas, see §3 Metrics. For interpretation and discussion, see §5 Discussion.*

# 05. Discussion

## 5.1 Main Result

The experiment shows **no outcome difference between the two architectures for this task**.

Across 135 paired runs:

- success rate is statistically indistinguishable
- coverage metrics are statistically indistinguishable ¹
- dialogue length (steps) is identical
- token consumption is identical ²

Both strategies therefore reach **the same task outcomes with the same efficiency**.

This result is notable because the comparison isolates **orchestration architecture only**.  
LLM, prompts, tools, simulator, and termination logic are identical in both implementations.

In this experimental setting — a short linear dialogue task — orchestration architecture **does not affect task performance**.

¹ Coverage values may exceed 1.0 when agents extract more entities than the target count from the original transcript (§4.4).

² Latency metrics differ between strategies and are discussed separately in §5.2.

---

## 5.2 Latency Overhead

While outcome metrics are identical, **latency consistently differs**.

All latency measurements show higher values for the StateGraph implementation (Negative = StateGraph slower):

| Metric | Delta (ReAct − StateGraph) |
| ---- | ---- |
| E2E dialogue latency | −2023 ms |
| Message latency | −568 ms / step |
| Simulator latency | −168 ms / step |
| Orchestration latency | −2.28 ms / step |

The effect is cumulative.

With a mean dialogue length of ~7.8 steps, the difference results in an average **~2 second longer dialogue completion time** for the StateGraph architecture.

This overhead does **not affect token usage or task outcomes**, but it consistently affects execution time.

The result reflects a common engineering trade-off:  
the observed latency difference suggests that additional orchestration abstractions may introduce runtime overhead in this implementation.

---

## 5.3 Interpreting the Latency Difference

The measured per-step latency differences do not sum directly to the observed end-to-end delta.

This occurs because:

- some dialogue steps do not call the simulator
- dialogue lengths vary across scenarios
- statistics are computed on paired distributions rather than deterministic step counts

As a result, the effective dialogue-level difference (~2 seconds) is smaller than the simple sum of per-step deltas (~5.7 seconds if summed naively).

The important observation is not the exact breakdown but the **consistent directional effect**:  
every latency component is slower in the StateGraph implementation.

---

## 5.4 Measurement Considerations

A small part of the message latency difference is explained by **measurement boundaries**.

In the ReAct implementation, validation and logging occur inside the measured step window, while in the StateGraph implementation they occur slightly later in the execution flow.

This affects a fraction of the measured message latency difference but **does not affect end-to-end latency**, which captures the full execution time in both strategies.

---

## 5.5 Token Usage

Despite additional orchestration nodes, **token consumption is identical**.

The StateGraph implementation includes an extra `evaluate_stop` node, but this node contains deterministic logic and does not invoke the LLM.

Both strategies therefore perform exactly **one LLM call per dialogue step**, which explains the identical token statistics observed in the results.

---

## 5.6 Decision Instability

Both strategies exhibit similar levels of `agent_done` flag changes during dialogue execution.

In the vast majority of runs (~89%), exactly one flag transition is observed, corresponding to the expected termination pattern: the agent signals `done=false` during the dialogue and `done=true` at completion.

Mean values (ReAct: 0.91, StateGraph: 0.87) reflect minor variation around this dominant pattern rather than meaningful behavioral differences.

Because both architectures use identical completion logic, the observed instability reflects **model behavior rather than orchestration differences**.

---

## 5.7 Fair Comparison of Architectures

Many agent architecture comparisons mix multiple variables at once — for example different prompting strategies, tool routing logic, or termination policies.

This experiment avoids those confounders.

Both implementations share:

- identical prompts
- identical tools
- identical simulator
- identical completion criteria
- identical model

Metric logging is also implemented at **equivalent execution points in both architectures**.

Timing measurements are recorded within the agent execution step rather than propagated through state transitions.  
This design was chosen deliberately to avoid measuring additional node-transition overhead as part of the agent response time, allowing the experiment to isolate orchestration costs separately.

The only controlled difference is therefore **the orchestration mechanism (loop vs. graph)**.

This design allows the experiment to isolate the effect of orchestration architecture itself.

---

## 5.8 Limitations

Several limitations affect the scope of these conclusions.

**Single task type**:

The experiment evaluates a structured information-gathering dialogue task.  
Results may differ for other workloads such as open-ended reasoning or complex planning.

**Short dialogue horizon**:

Median dialogue length is 6–7 steps.  
Longer multi-stage workflows may produce different orchestration dynamics.

**Single model**:

All experiments use the same LLM.  
Different models may interact differently with orchestration structures.

**Simulated users**:

User responses are generated by a simulator.  
Real users may introduce additional variability in conversation flow.

**Coverage metric**:

Coverage measures entity extraction counts rather than semantic correctness.

**Prompt simplicity**:

The prompt used in the experiment was intentionally simple and was not optimized for either architecture.  
Architecture-specific prompt engineering or orchestration-aware prompting strategies may improve performance metrics and were not explored in this study.

**Missing data**:

Four StateGraph runs (3%) have missing latency measurements due to execution errors.  
This is unlikely to affect the results but is noted for transparency.

---

## 5.9 Future Work

Several extensions could further evaluate these findings:

- experiments with longer multi-stage workflows
- tasks involving branching logic or tool orchestration
- comparisons across different LLM models
- experiments with real user interactions

The experimental framework and datasets used in this study are available in the repository to enable further investigation.
# 06. Threats to Validity

This section discusses potential threats to the validity of the study's conclusions using the standard taxonomy: **internal**, **external**, **construct**, and **statistical conclusion** validity.

---

## 6.1 Internal Validity

Internal validity concerns whether the observed effects can be attributed to the orchestration architecture rather than implementation artifacts or confounding factors.

The experiment was designed to minimize such confounders:

- both strategies use the same LLM, prompts, tools, simulator, and completion criteria
- each scenario is evaluated by both architectures (paired design)
- both implementations inherit from the same base scenario class
- LLM calls are executed through the same custom Bedrock client
- metric logging is implemented using shared instrumentation

As a result, both strategies share identical infrastructure for model invocation, network access, and metric collection.

The only intentional difference between the implementations is the orchestration mechanism (loop vs. graph).

A remaining threat is that framework-level execution overhead may depend on the specific implementation of the orchestration library (e.g., LangGraph).  
Future versions of the framework could therefore exhibit different performance characteristics.

---

## 6.2 External Validity

External validity concerns the generalizability of the findings.

The experiment evaluates a **single task type**: structured information-gathering dialogues with short interaction horizons (median ~6–7 steps).  
The conclusions therefore apply specifically to **short, linear workflows**.

Results may differ in other settings, including:

- longer multi-stage workflows
- tasks requiring branching or planning
- workflows involving multiple tools
- domains with different dialogue structures

The experiments also use a **single LLM (Claude 3 Haiku)** and **simulated users** rather than real human participants.  
Different models or real user behavior may lead to different interaction dynamics and latency patterns.

The dataset was additionally filtered to remove dialogues where the doctor interacted with relatives rather than the patient directly.  
Both successful and problematic patient cases remain represented in the final scenarios.

These limitations restrict the scope of generalization but do not affect the internal comparison between architectures.

---

## 6.3 Construct Validity

Construct validity concerns whether the operational metrics represent the intended concepts.

The runtime **coverage metric** measures the proportion of collected entities relative to the target set.  
In this study, entity collection serves primarily as a **deterministic signal for task progression and completion**, rather than an evaluation of semantic correctness.

The experiment therefore does not assess the correctness of extracted entities.  
Entities function as structured placeholders that allow the dialogue workflow to reach a measurable termination condition.

Another design decision concerns the definition of a **dialogue step**, defined as one agent message followed by one simulator response.  
Internal framework operations are not treated as steps, as the metric is intended to reflect the observable dialogue progression.

---

## 6.4 Statistical Conclusion Validity

Statistical conclusion validity concerns whether the statistical methods support the inferences drawn from the data.

The study uses a **paired experimental design**, where each scenario is evaluated by both architectures.  
Experiments were executed in **three separate batches**, with runs separated by several days in order to reduce potential cache or warm-start effects.

Statistical analysis includes:

- Wilcoxon signed-rank tests for paired metric comparisons
- McNemar’s test for paired success outcomes
- bootstrap confidence intervals for metric differences
- win/loss comparisons across paired runs
- rank-biserial correlation as an effect size estimate

These methods do not assume normality and are appropriate for paired experimental data.

Multiple metrics are analyzed, which increases the theoretical risk of Type I error.  
However, the primary conclusions rely on a small set of core outcomes (success rate, coverage, and latency), while other metrics are interpreted descriptively.

---

## 6.5 Summary

The main limitation of this study concerns **external validity**.

The results are derived from a controlled experimental task with short dialogue horizons and a single model.  
Within this scope, the experimental design isolates orchestration architecture as the primary varying factor, enabling a focused comparison of its impact on task outcomes and execution latency.

Results may be influenced by simulator simplicity and lack of adversarial behavior.

# 07. Conclusion

This study compared two agent orchestration strategies — a **ReAct-style cyclic loop** and a **LangGraph StateGraph** — across **135 paired experimental runs** (45 scenarios × 3 batches, both strategies applied) of simulated doctor–patient dialogues.

Across all experiments, no statistically significant differences were observed in task outcomes.
Task completion, information coverage, dialogue length, and token usage showed **no statistically significant differences** between strategies.

The only consistent difference observed in the experiments was **execution latency**.
StateGraph shows approximately **~2 seconds longer per dialogue on average** (mean delta: −2023ms, 95% CI: [−3847, −757]).
However, part of the per-step latency difference may be influenced by measurement boundaries within the orchestration implementations (see §5.4).

These results indicate that for **short-horizon, structured information-gathering dialogues**, the orchestration architecture itself does not materially affect task outcomes within the evaluated setting.
Both approaches reached comparable results while differing only in runtime characteristics.
The measured latency overhead (~2s per dialogue) represents a consistent runtime cost while leaving task success and token consumption unchanged.

---

## Answers to Research Questions

| Research Question | Answer | Evidence |
| ----------------- | ------- | ------- |
| **RQ1. Does orchestration architecture affect task outcomes?** | No statistically significant difference observed. | McNemar p=0.52; coverage CI includes 0 |
| **RQ2. Does architecture affect efficiency?** | No statistically significant difference in steps or token usage. | Steps p=0.85; Tokens p=0.99 |
| **RQ3. Does architecture affect runtime latency?** | Yes. StateGraph executions are slower on average. | Mean delta −2023ms; CI excludes 0 |
| **RQ4. Does explicit state reduce instability?** | No clear difference observed between strategies. | Instability p=0.59 |

---

## Scope of the Findings

The results should be interpreted within the scope of the experiment:

* a structured **slot-filling dialogue task**
* **short interaction horizon** (median 6–7 turns)
* a **single LLM model**
* a **simulated user environment**

Within this setting, the experiments show that different orchestration architectures can produce **comparable agent behavior** while differing primarily in runtime overhead.

Future work may extend the comparison to longer workflows, additional task types, and multiple LLM models to evaluate whether these observations hold in more complex agent settings.

---

## Availability

The implementation, experimental configuration, and aggregated metrics are available in the project repository at [repository URL]

Raw dialogue logs can be shared for replication and further analysis by request.

---

## Data & Reproducibility

### Dataset

- **45 scenarios** derived from real doctor-patient dialogues
- **135 runs** (3 batches × 45 scenarios × 2 strategies)
- **Grounded simulation:** Patient simulator constrained by structured profiles (AWS Comprehend Medical)

---

### Data Files

| File | Content |
| ---- | ------- |
| `data/output/aggregate_metrics.json` | Full aggregated metrics (by_run, by_scenario, experiment_statistics) |
| `data/output/research_metrics.jsonl` | Raw event-level metrics |
| `data/output/dialogues/` | Dialogue transcripts |

### Configuration

| Parameter | Value |
| --------- | ----- |
| Model | Anthropic Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`) |
| Max steps | 15 |
| Coverage threshold | 0.2 |
| Response length | 5-12 words |

### Scripts

| Script | Purpose |
| ------ | ------- |
| `scripts/generate_results_tables.py` | Generate Markdown tables from raw data |
| `scripts/generate_figures.py` | Generate figures (PNG + SVG) |

---

## Citation

```bibtex
@misc{stategraph-react-benchmark-2026,
  title={LangGraph vs. ReAct: An Engineering Benchmark for Conversational Agents},
  author={[Your Name]},
  year={2026},
  url={https://github.com/[your-username]/stategraph-react-simulation-agentic-comparison}
}
```

---

## License

MIT License — see [LICENSE](../LICENSE) for details.

---

## Acknowledgments

- Real dialogue corpora for scenario generation
- AWS Comprehend Medical for entity extraction
- Anthropic Claude 3 Haiku (Bedrock) for LLM

---

*For raw data, see `data/output/aggregate_metrics.json`. For figure files, see `docs/figures/`.*
