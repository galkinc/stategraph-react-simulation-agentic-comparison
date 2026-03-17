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