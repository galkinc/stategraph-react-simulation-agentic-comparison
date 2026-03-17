from metrics_agregator.models import ScenarioMetrics, ScenarioComparison, StatisticalTest, BootstrapCI, ExperimentComparison, WinLoss, WinLossResult
from metrics_agregator.statistics import wilcoxon_test, bootstrap_delta, mcnemar_success

def compare_strategies(aggregated) -> list[ScenarioComparison]:
    """react vs stategraph comparison based on success rate delta"""

    scenarios = {}

    for row in aggregated:
        scenarios.setdefault(row.scenario_id, {})[row.strategy] = row

    comparisons = []

    for sid, data in scenarios.items():

        if "react" not in data or "stategraph" not in data:
            continue

        react = data["react"]
        sg = data["stategraph"]

        comparisons.append(
                ScenarioComparison(
                    scenario_id=sid,
                    delta_success_rate=react.success_rate - sg.success_rate,
                    delta_steps=react.steps_mean - sg.steps_mean,
                    delta_latency_mean=react.latency_mean - sg.latency_mean,
                )
        )

    return comparisons

def build_pairs(runs):

    grouped = {}

    for r in runs:
        if r.batch_id is None:
            raise ValueError("batch_id required for pairing")

        key = (r.scenario_id, r.batch_id)
        grouped.setdefault(key, {})[r.strategy] = r

    pairs = []

    for pair in grouped.values():
        if "react" in pair and "stategraph" in pair:
            pairs.append((pair["react"], pair["stategraph"]))

    return pairs

def extract_metric(pairs, getter):

    a = []
    b = []

    for react, sg in pairs:

        av = getter(react)
        bv = getter(sg)

        if av is None or bv is None:
            continue

        a.append(av)
        b.append(bv)

    return a, b

def run_all_tests(runs: list[ScenarioMetrics]) -> ExperimentComparison:
    if not isinstance(runs[0], ScenarioMetrics):
        raise TypeError("run_all_tests expects ScenarioMetrics")
    
    pairs = build_pairs(runs)

    wilcoxon_results = []
    bootstrap_results = []
    win_loss_results = []

    metrics = {
        "steps": get_steps,
        "tokens": get_tokens,
        "latency": get_latency,
        "message_latency": get_message_latency,
        "simulator_latency": get_simulator_latency,
        "orchestration_latency": get_orchestration_latency,
        "coverage": get_coverage,
    }

    for name, getter in metrics.items():
        a, b = extract_metric(pairs, getter)
        if len(a) == 0 or len(b) == 0:
            continue

        # Wilcoxon
        stat, p = wilcoxon_test(a, b)
        wilcoxon_results.append(
            StatisticalTest(
                metric=name,
                test="wilcoxon",
                statistic=stat,
                p_value=p
            )
        )

        # Bootstrap CI
        delta, low, high = bootstrap_delta(a, b)
        bootstrap_results.append(
            BootstrapCI(
                metric=name,
                delta=delta,
                ci_low=low,
                ci_high=high
            )
        )

        # Win/Loss + Rank-biserial
        wl = win_loss(pairs, getter)
        rb = rank_biserial(wl.wins, wl.losses)
        win_loss_results.append(WinLossResult(metric=name, win_loss=wl, rank_biserial=rb))

    # McNemar for success
    stat, p = mcnemar_success(pairs)
    mcnemar_results = [
        StatisticalTest(
            metric="success",
            test="mcnemar",
            statistic=stat,
            p_value=p
        )
    ]

    print("pairs used for statistics:", len(pairs))

    return ExperimentComparison(
        mcnemar=mcnemar_results,
        wilcoxon=wilcoxon_results,
        bootstrap=bootstrap_results,
        win_loss=win_loss_results
    )

def win_loss(pairs, getter):

    wins = 0
    losses = 0
    ties = 0

    for react, sg in pairs:

        a = getter(react)
        b = getter(sg)

        if a is None or b is None:
            continue
        
        if b < a:
            wins += 1
        elif b > a:
            losses += 1
        else:
            ties += 1

    return WinLoss(
        wins=wins,
        losses=losses,
        ties=ties,
        win_rate=wins / (wins + losses) if wins + losses else None
    )

def rank_biserial(wins, losses):
    if wins + losses == 0:
        return None
    return (wins - losses) / (wins + losses)

# Getters

def get_steps(run):
    return run.total_steps

def get_tokens(run):
    return run.tokens.total

def get_latency(run):
    return run.latency.e2e_total_ms

def get_coverage(run):
    return run.coverage.coverage_final

def get_message_latency(run):
    if run.latency and run.latency.message:
        return run.latency.message.mean
    return None

def get_simulator_latency(run):
    if run.latency and run.latency.simulator:
        return run.latency.simulator.mean
    return None

def get_orchestration_latency(run):
    if run.latency and run.latency.orchestration:
        return run.latency.orchestration.mean
    return None