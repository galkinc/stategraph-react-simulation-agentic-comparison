# 7. Conclusion

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
