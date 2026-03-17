## Generated Tables

### Summary Statistics
| Metric | ReAct Mean | ReAct Median | StateGraph Mean | StateGraph Median | Delta | 95% CI | p-value | Effect Size |
| ------ | --------- | ----------- | --------------- | ----------------- | ----- | ------ | ------- | ----------- |
| **E2E Latency (per dialogue)** | 14019.29ms | 12482.30ms | 15538.67ms | 14366.77ms | **-2023ms** | [-3847, -757] | 0.05 | -0.21 (small) |
| **Message Latency (per step)** | 963.18ms | 925.94ms | 1553.15ms | 1491.50ms | **-568ms** | [-586, -550] | 8.21e-24 | -0.96 (large) |
| **Simulator Latency (per step)** | 866.00ms | 964.18ms | 1100.32ms | 1121.64ms | **-168ms** | [-201, -135] | 8.48e-18 | -0.78 (large) |
| **Orchestration (per step)** | 0.73ms | 0.54ms | 3.22ms | 2.76ms | **-2ms** | [-3, -2] | 5.66e-21 | -0.98 (large) |
| **Steps (per dialogue)** | 7.77 | 6 | 7.81 | 7 | **0** | [-1, 1] | 0.85 | -0.11 (small) |
| **Tokens (per dialogue)** | 11952 | 8435 | 11676 | 9375 | **-126** | [-1666, 1437] | 0.99 | -0.05 (negligible) |
| **Success Rate** | 83.0% | 83.0% | 80% | 80% | — | — | 0.52 (McNemar) | — |
| **Coverage Final** | 1.10 | 1 | 1.07 | 1 | **0** | [-0, 0] | 0.59 | -0.01 (negligible) |

### Latency Tables (for §4.2)


### Message Latency (LLM Call)

| Strategy | Mean (ms) | Median (ms) |
|---|---|---|
| ReAct | 963.18 | 925.94 |
| StateGraph | 1553.15 | 1491.50 |

### Simulator Latency (Patient Response)

| Strategy | Mean (ms) | Median (ms) |
|---|---|---|
| ReAct | 866.00 | 964.18 |
| StateGraph | 1100.32 | 1121.64 |

### Orchestration Overhead

| Strategy | Mean (ms) | Median (ms) |
|---|---|---|
| ReAct | 0.73 | 0.54 |
| StateGraph | 3.22 | 2.76 |

### Efficiency Tables (for §4.3)


### Dialogue Length (Steps)

| Strategy | Mean | Median | Min | Max |
|---|---|---|---|---|
| ReAct | 7.77 | 6 | 1 | 15 |
| StateGraph | 7.81 | 7 | 1 | 15 |

### Token Consumption

| Strategy | Mean (total/dialogue) | Mean (per step) |
|---|---|---|
| ReAct | 11952 | 1538 |
| StateGraph | 11676 | 1494 |

### Outcome Tables (for §4.4)


### Dialogue Success Rate

| Strategy | Success Rate |
|---|---|
| ReAct | 83.0% |
| StateGraph | 80% |

### Information Extraction (Coverage)

| Strategy | Mean Final Coverage |
|---|---|
| ReAct | 1.10 |
| StateGraph | 1.07 |

### Stability Table (for §4.5)


### Decision Instability

| Strategy | Mean | Median |
|---|---|---|
| ReAct | 0.91 | 1 |
| StateGraph | 0.87 | 1 |

### Derived Metrics Tables (for §4.6)


### Coverage per Step

| Strategy | Mean Coverage/Step |
|---|---|
| ReAct | 0.219 |
| StateGraph | 0.208 |

### Coverage per Token

| Strategy | Mean Coverage/Token |
|---|---|
| ReAct | 0.00018 |
| StateGraph | 0.00017 |

### Coverage Velocity

| Strategy | Mean Velocity |
|---|---|
| ReAct | 0.141 |
| StateGraph | 0.120 |

