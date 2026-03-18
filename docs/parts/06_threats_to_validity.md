# 6. Threats to Validity

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
