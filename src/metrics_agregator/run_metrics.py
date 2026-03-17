from pathlib import Path

from metrics_agregator.io import load_events
from metrics_agregator.builder import build_runs
from metrics_agregator.scenario_aggregation import compute_run_metrics, aggregate_by_scenario
from metrics_agregator.comparison import compare_strategies, run_all_tests
from metrics_agregator.io import save_json

from metrics_agregator.models import ExportedMetrics
from config import settings

DATA_DIR = Path(settings.data.metrics_output_path)
INPUT_FILE = DATA_DIR / settings.data.research_metrics_file
OUTPUT_FILE = DATA_DIR / settings.data.agregate_metrics_file

if __name__ == "__main__":
    events = load_events(INPUT_FILE)

    runs = build_runs(events)
    run_metrics = [compute_run_metrics(r) for r in runs]
    scenario_metrics = aggregate_by_scenario(run_metrics)
    comparison = compare_strategies(scenario_metrics)
    experiment_stats = run_all_tests(run_metrics)

    metrics_data = ExportedMetrics(
        by_run=run_metrics,
        by_scenario=scenario_metrics,
        scenario_comparison=comparison,
        experiment_statistics=experiment_stats
    )

    save_json(metrics_data, OUTPUT_FILE)
