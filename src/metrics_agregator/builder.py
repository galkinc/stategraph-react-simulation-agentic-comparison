from collections import defaultdict
from metrics_agregator.models import StepMetrics, DialogRun, MetricEvent
from typing import Iterable

def build_runs(events: Iterable[MetricEvent]) -> list[DialogRun]:

    runs = {}

    for e in events:
        run = runs.setdefault(
            e.run_id,
            {
                "strategy": e.strategy,
                "scenario_id": e.scenario_id,
                "batch_id": e.batch_id,
                "steps": defaultdict(lambda: StepMetrics(step=-1)),
                "meta": {},
            },
        )

        if e.step is not None:

            step = run["steps"][e.step]
            step.step = e.step

            if e.metric in StepMetrics.model_fields:
                setattr(step, e.metric, e.value)
        else:
            run["meta"][e.metric] = e.value

    result = []

    for run_id, data in runs.items():

        result.append(
            DialogRun(
                run_id=run_id,
                strategy=data["strategy"],
                scenario_id=data["scenario_id"],
                batch_id=data["batch_id"],
                steps=dict(data["steps"]),
                **data["meta"],
            )
        )

    return result
