"""
Batch runner for research scenarios.

Runs all patient profiles from data/processed/patient_profiles.jsonl
with both strategies (react, stategraph) and collects metrics.

Usage:
    python run_batch.py --strategy react
    python run_batch.py --strategy stategraph
    python run_batch.py --strategy all  # runs both
"""
import asyncio
import logging
import argparse
import json
import datetime
from pathlib import Path

from config import settings
from src.strategies.react_strategy import ReactStrategy
from src.strategies.stategraph_strategy import StateGraphStrategy
from src.research.scenario import ResearchScenario
from src.research.metrics_sink import JSONLMetricsSink
from src.aws_client import bedrock_manager


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else settings.logging_level
    logging.basicConfig(
        level=level,
        format=settings.logging_format,
        force=True
    )
    # Silence noisy libs
    if not settings.boto3_debug_logging:
        logging.getLogger("botocore").setLevel(logging.WARNING)
        logging.getLogger("boto3").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def load_profiles(profiles_path: Path) -> list[dict]:
    """Load patient profiles from JSONL file."""
    profiles = []
    with open(profiles_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                profiles.append(json.loads(line))
    return profiles


async def run_scenario(
    profile: dict,
    strategy_name: str,
    max_steps: int,
    metrics_sink: JSONLMetricsSink,
    logger: logging.Logger,
    batch_id: str
) -> dict | None:
    """Run a single scenario with the specified strategy."""
    dialogue_id = profile.get("dialogue_id")

    # Create scenario
    scenario = ResearchScenario(
        id=dialogue_id,
        profile_id=dialogue_id,
        user_goal="symptom elicitation",
        tier="T1",
        expected_fields={"conditions", "anatomy", "medications", "treatments"}
    )

    # Create strategy (run_id will be set from scenario.run() call)
    if strategy_name == "react":
        strategy = ReactStrategy(
            client=None,
            max_steps=max_steps,
            dialogue_id=dialogue_id,
            metrics_sink=metrics_sink,
            batch_id=batch_id
        )
    elif strategy_name == "stategraph":
        strategy = StateGraphStrategy(
            client=None,
            max_steps=max_steps,
            dialogue_id=dialogue_id,
            metrics_sink=metrics_sink,
            batch_id=batch_id
        )
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    try:
        result = await strategy.run(scenario)
        return {
            "dialogue_id": dialogue_id,
            "strategy": strategy_name,
            "run_id": scenario.run_id,
            "batch_id": batch_id,
            "success": result is not None
        }
    except Exception as e:
        logger.error("Error running scenario %s with %s: %s", dialogue_id, strategy_name, e)
        return {
            "dialogue_id": dialogue_id,
            "strategy": strategy_name,
            "run_id": scenario.run_id,
            "batch_id": batch_id,
            "success": False,
            "error": str(e)
        }


async def main(
    strategy: str,
    max_steps: int,
    debug: bool,
    start_index: int | None = None,
    end_index: int | None = None
):
    # 1. Initialize Bedrock
    bedrock_manager.initialize(
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    # 2. Generate batch_id (one for all strategies in this run)
    batch_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # 3. Load profiles
    profiles_path = Path(settings.data.profiles_path)
    if not profiles_path.is_absolute():
        profiles_path = Path.cwd() / profiles_path
    profiles = load_profiles(profiles_path)
    logger.info("Loaded %d profiles from %s", len(profiles), profiles_path)

    # 4. Apply index filters (for partial runs)
    if start_index is not None or end_index is not None:
        start = start_index or 0
        end = end_index or len(profiles)
        profiles = profiles[start:end]
        logger.info("Running profiles [%d:%d] (%d profiles)", start, end, len(profiles))

    # 5. Determine strategies to run
    strategies = ["react", "stategraph"] if strategy == "all" else [strategy]

    # 6. Run batch
    results = []
    for strat in strategies:
        logger.info("=" * 60)
        logger.info("Starting batch run with strategy: %s (batch_id=%s)", strat.upper(), batch_id)
        logger.info("=" * 60)

        metrics_sink = JSONLMetricsSink(
            buffer_size=30,
            output_dir=settings.data.metrics_output_path
        )

        for i, profile in enumerate(profiles, 1):
            logger.info("[%d/%d] Running profile %s with %s", i, len(profiles), profile.get("dialogue_id"), strat)

            result = await run_scenario(
                profile=profile,
                strategy_name=strat,
                max_steps=max_steps,
                metrics_sink=metrics_sink,
                logger=logger,
                batch_id=batch_id
            )
            results.append(result)

            if result and result.get("success"):
                logger.info("Completed: %s", result.get("run_id"))
            else:
                logger.warning("Failed: %s", profile.get("dialogue_id"))

        # Flush metrics after each strategy
        metrics_sink.flush()

    # 7. Save batch summary
    summary_path = Path(settings.data.metrics_output_path) / "batch_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "batch_id": batch_id,
            "strategy": strategy,
            "total_profiles": len(profiles),
            "strategies_run": strategies,
            "results": results
        }, f, indent=2)

    logger.info("Batch summary saved to %s", summary_path)

    # 8. Print summary
    success_count = sum(1 for r in results if r.get("success"))
    logger.info("Batch complete: %d/%d successful", success_count, len(results))

    await bedrock_manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch run research scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_batch.py --strategy react
  python run_batch.py --strategy stategraph
  python run_batch.py --strategy all
  python run_batch.py --strategy react --max-steps 15
  python run_batch.py --strategy react --start-index 0 --end-index 10
        """
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="react",
        choices=["react", "stategraph", "all"],
        help="Strategy to use (default: react)"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=10,
        help="Maximum number of dialogue steps (default: 10)"
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=None,
        help="Start index for partial runs (default: None)"
    )
    parser.add_argument(
        "--end-index",
        type=int,
        default=None,
        help="End index for partial runs (default: None)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    args = parser.parse_args()

    logger = logging.getLogger(__name__)
    setup_logging(debug=args.debug)

    logger.info(
        "Starting batch run: strategy=%s, max_steps=%d, profiles=%s",
        args.strategy,
        args.max_steps,
        f"[{args.start_index}:{args.end_index}]" if args.start_index or args.end_index else "all"
    )

    asyncio.run(main(
        strategy=args.strategy,
        max_steps=args.max_steps,
        debug=args.debug,
        start_index=args.start_index,
        end_index=args.end_index
    ))
