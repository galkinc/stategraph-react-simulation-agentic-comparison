import numpy as np
from collections import defaultdict
from metrics_agregator.models import (
    ScenarioMetrics,
    ScenarioAggregate,
    Stats,
    LatencyMetrics,
    TokenMetrics,
    MessageMetrics,
    DecisionMetrics,
    CoverageMetrics
)

def stats(values):

    if not values:
        return None

    arr = np.array(values)
    
    return Stats(
        mean=float(arr.mean()),
        median=float(np.median(arr)),
        min=float(arr.min()),
        max=float(arr.max()),
        count=int(len(arr)),
        p50=float(np.percentile(arr, 50)),
        p95=float(np.percentile(arr, 95)),
        p99=float(np.percentile(arr, 99)),
    )

def count_done_switches(steps):

    values = [s.agent_done for s in steps if s.agent_done is not None]

    switches = 0

    for i in range(1, len(values)):
        if values[i] != values[i-1]:
            switches += 1

    return switches

def compute_run_metrics(run) -> ScenarioMetrics:

    steps = run.steps_excluding_init()

    ttft = [s.ttft_ms for s in steps if s.ttft_ms is not None]
    msg = [s.message_ms for s in steps if s.message_ms is not None]
    e2e = [s.e2e_latency_ms for s in steps if s.e2e_latency_ms is not None]
    sim = [s.simulator_latency_ms for s in steps if s.simulator_latency_ms is not None]

    orch = []
    for s in steps:
        if (
            s.e2e_latency_ms is not None
            and s.message_ms is not None
            and s.simulator_latency_ms is not None
        ):
            orch.append(
                s.e2e_latency_ms - s.message_ms - s.simulator_latency_ms
            )

    word_count_vals = [s.message_word_count for s in steps if s.message_word_count is not None]
    word_count_mean = float(np.mean(word_count_vals)) if word_count_vals else 0
    patient_word_count_vals = [s.patient_message_word_count for s in steps if s.patient_message_word_count is not None]
    patient_word_count_mean = float(np.mean(patient_word_count_vals)) if patient_word_count_vals else 0
    is_compliant_vals = [s.is_compliant for s in steps if s.is_compliant is not None]
    is_compliant_rate = float(sum(is_compliant_vals) / len(is_compliant_vals)) if is_compliant_vals else 0

    input_total = sum(s.input_tokens or 0 for s in steps)
    output_total = sum(s.output_tokens or 0 for s in steps)
    total_tokens = input_total + output_total
    input_per_step_vals = [s.input_tokens for s in steps if s.input_tokens is not None]
    input_per_step_mean = float(np.mean(input_per_step_vals)) if input_per_step_vals else 0
    output_per_step_vals = [s.output_tokens for s in steps if s.output_tokens is not None]
    output_per_step_mean = float(np.mean(output_per_step_vals)) if output_per_step_vals else 0

    coverages = [s.coverage for s in steps if s.coverage is not None]
    coverage_final = coverages[-1] if coverages else 0

    velocity = []
    instability = 0
    prev = coverages[0]
    for c in coverages[1:]:
        velocity.append(c - prev)
        if c < prev:
            instability += prev - c
        prev = c
    
    coverage_per_step = coverage_final / len(steps) if steps else 0
    coverage_per_token = coverage_final / total_tokens if total_tokens > 0 else 0


    return ScenarioMetrics(

        scenario_id=run.scenario_id,
        strategy=run.strategy,
        run_id=run.run_id,
        batch_id=run.batch_id,

        total_steps=len(steps),
        success=run.success,

        latency=LatencyMetrics(
            ttft=stats(ttft),
            message=stats(msg),
            e2e_per_step=stats(e2e),
            e2e_total_ms=sum(e2e),
            orchestration=stats(orch),
            simulator=stats(sim),
        ),
        tokens=TokenMetrics(
            input_total=input_total,
            output_total=output_total,
            total=total_tokens,
            total_per_step_mean=float(total_tokens) / len(steps) if steps else 0,
            input_per_step_mean=input_per_step_mean,
            output_per_step_mean=output_per_step_mean,
        ),
        messages=MessageMetrics(
            word_count_mean=word_count_mean,
            patient_word_count_mean=patient_word_count_mean,
            is_compliant_rate=is_compliant_rate,
        ),
        decision=DecisionMetrics(
            decision_instability=count_done_switches(steps)
        ),
        coverage=CoverageMetrics(
            coverage_final=coverage_final,
            coverage_velocity=stats(velocity),
            coverage_per_step=coverage_per_step,
            coverage_per_token=coverage_per_token,
            coverage_instability=instability,
        )
    )

def aggregate_by_scenario(run_metrics: list[ScenarioMetrics]) -> list[ScenarioAggregate]:
    groups = defaultdict(list)
    
    for r in run_metrics:
        groups[(r.scenario_id, r.strategy)].append(r)
    
    result = []
    
    for (scenario, strategy), runs in groups.items():
        successes = []
        steps_vals = []
        latency_vals = []
        message_vals = []
        sim_vals = []
        orchestration_vals = []
        
        for r in runs:
            if r.success is not None:
                successes.append(r.success)
            
            if r.total_steps is not None:
                steps_vals.append(r.total_steps)
            
            if r.latency:
                if r.latency.e2e_total_ms is not None:
                    latency_vals.append(r.latency.e2e_total_ms)
                    
                    # orchestration latency
                    if r.latency.orchestration and r.latency.orchestration.mean is not None:
                        orchestration_vals.append(r.latency.orchestration.mean)
                
                if r.latency.message and r.latency.message.mean is not None:
                    message_vals.append(r.latency.message.mean)
                
                if r.latency.simulator and r.latency.simulator.mean is not None:
                    sim_vals.append(r.latency.simulator.mean)
        
        result.append(
            ScenarioAggregate(
                scenario_id=scenario,
                strategy=strategy,
                runs=len(runs),
                success_rate=sum(successes) / len(successes) if successes else 0.0,
                steps_mean=float(np.mean(steps_vals)) if steps_vals else None,
                latency_mean=float(np.mean(latency_vals)) if latency_vals else None,
                message_latency_mean=float(np.mean(message_vals)) if message_vals else None,
                simulator_latency_mean=float(np.mean(sim_vals)) if sim_vals else None,
                orchestration_latency_mean=float(np.mean(orchestration_vals)) if orchestration_vals else None
            )
        )
    
    return result
