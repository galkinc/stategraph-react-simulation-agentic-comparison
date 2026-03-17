from pydantic import BaseModel

# Event model for incoming metrics data,
# which will be processed and stored in the database.

class MetricEvent(BaseModel):
    timestamp: float
    strategy: str
    scenario_id: str
    metric: str
    value: float | str | int
    step: int | None = None
    run_id: str
    batch_id: str | None = None


class StepMetrics(BaseModel):
    """StepMetrics"""

    step: int
    # latency
    ttft_ms: float | None = None
    message_ms: float| None = None
    e2e_latency_ms: float| None = None
    simulator_latency_ms: float| None = None
    # tokens
    input_tokens: int| None = None
    output_tokens: int| None = None
    # words
    message_word_count: int| None = None
    patient_message_word_count:int| None = None
    is_compliant: int | None = None
    # entitites
    coverage: float | None = None
    coverage_collected: int | None = None
    coverage_target: int | None = None
    # done flags
    agent_done: int | None = None
    final_done: int| None = None
    

class DialogRun(BaseModel):
    run_id: str
    strategy: str
    scenario_id: str
    batch_id: str | None = None
    # steps
    steps: dict[int, StepMetrics]
    # finalized at the end of the dialogue
    total_steps: int
    total_duration_sec: float
    termination_reason: str | None = None
    success: int| None

    def steps_excluding_init(self):
        return sorted(
            [s for s in self.steps.values() if s.step != 0],
            key=lambda s: s.step
        )

# Output model for aggregated dialogue metrics, 
# which will be returned by json serialization.

class Stats(BaseModel):

    mean: float
    median: float
    min: float
    max: float
    count: int
    p50: float
    p95: float
    p99: float


class LatencyMetrics(BaseModel):

    ttft: Stats | None
    message: Stats | None
    e2e_per_step: Stats | None
    simulator: Stats | None
    orchestration: Stats | None
    e2e_total_ms: float
    


class TokenMetrics(BaseModel):

    input_total: int
    output_total: int
    total: int

    total_per_step_mean: float
    input_per_step_mean: float
    output_per_step_mean: float


class MessageMetrics(BaseModel):

    word_count_mean: float
    patient_word_count_mean: float

    is_compliant_rate: float

class DecisionMetrics(BaseModel):

    decision_instability: int

class CoverageMetrics(BaseModel):

    coverage_final: float
    coverage_velocity: Stats | None

    coverage_per_step: float
    # entities discovered per token
    coverage_per_token: float

    coverage_instability: float


class ScenarioMetrics(BaseModel):
    """Run-level metrics"""

    scenario_id: str
    strategy: str
    run_id: str
    batch_id: str | None = None

    total_steps: int
    success: int | None

    latency: LatencyMetrics
    tokens: TokenMetrics
    messages: MessageMetrics
    decision: DecisionMetrics
    coverage: CoverageMetrics


class ScenarioAggregate(BaseModel):

    scenario_id: str
    strategy: str

    runs: int
    success_rate: float

    steps_mean: float
    latency_mean: float
    message_latency_mean: float
    simulator_latency_mean: float
    orchestration_latency_mean: float


class ScenarioComparison(BaseModel):

    scenario_id: str

    delta_success_rate: float
    delta_steps: float

    delta_latency_mean: float


# Static models

class StatisticalTest(BaseModel):

    metric: str
    test: str

    statistic: float | None
    p_value: float | None

class BootstrapCI(BaseModel):

    metric: str

    delta: float | None
    ci_low: float | None
    ci_high: float | None


class WinLoss(BaseModel):
    wins: int
    losses: int
    ties: int
    win_rate: float | None


class WinLossResult(BaseModel):
    metric: str
    win_loss: WinLoss
    rank_biserial: float | None


class ExperimentComparison(BaseModel):
    mcnemar: list[StatisticalTest]
    wilcoxon: list[StatisticalTest]
    bootstrap: list[BootstrapCI]
    win_loss: list[WinLossResult]


# Final output model

class ExportedMetrics(BaseModel):
    """Exported model for final output"""
    by_run: list[ScenarioMetrics]
    by_scenario: list[ScenarioAggregate]
    scenario_comparison: list[ScenarioComparison]
    experiment_statistics: ExperimentComparison
