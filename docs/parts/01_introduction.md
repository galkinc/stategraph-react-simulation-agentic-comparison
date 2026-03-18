# 1. Introduction

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