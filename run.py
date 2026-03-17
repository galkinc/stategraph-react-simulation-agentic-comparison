import asyncio
import logging
import argparse
import datetime

from config import settings
from src.aws_client import bedrock_manager
from src.strategies.react_strategy import ReactStrategy
from src.strategies.stategraph_strategy import StateGraphStrategy
from src.research.scenario import ResearchScenario
from src.research.metrics_sink import JSONLMetricsSink


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else settings.logging_level
    logging.basicConfig(level=level, format=settings.logging_format, force=True)

    # Silence noisy libs
    if not settings.boto3_debug_logging:
        logging.getLogger("botocore").setLevel(logging.WARNING)
        logging.getLogger("boto3").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


async def main(
    dialogue_id: str | None = None,
    strategy_name: str = "react",
    max_steps: int = 10,
    debug: bool = False
):
    # 1. Initialize the Bedrock client
    bedrock_manager.initialize(
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    # 2. Generate batch_id (for consistency with run_batch.py)
    batch_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    metrics_sink = JSONLMetricsSink(
        buffer_size=30,
        output_dir=settings.data.metrics_output_path
    )

    try:
        # 3. Create a ResearchScenario
        scenario = ResearchScenario(
            id=dialogue_id or f"default_{strategy_name}_run",
            profile_id=dialogue_id,
            user_goal="symptom elicitation",
            tier="T1",
            expected_fields={"conditions", "anatomy", "medications"}
        )

        # 4. Select strategy
        if strategy_name.lower() == "react":
            strategy = ReactStrategy(
                client=None,
                max_steps=max_steps,
                dialogue_id=dialogue_id,
                metrics_sink=metrics_sink,
                batch_id=batch_id
            )
            logger.info("Using ReAct strategy (batch_id=%s)", batch_id)
        elif strategy_name.lower() == "stategraph":
            strategy = StateGraphStrategy(
                client=None,
                max_steps=max_steps,
                dialogue_id=dialogue_id,
                metrics_sink=metrics_sink,
                batch_id=batch_id
            )
            logger.info("Using StateGraph strategy (batch_id=%s)", batch_id)
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}. Use 'react' or 'stategraph'.")

        # 5. Run the strategy
        result = await strategy.run(scenario)

        # 6. Output the result
        if result:
            logger.info("Collected payload: %s", result)
            logger.info("Run ID: %s, Batch ID: %s", scenario.run_id, batch_id)
        else:
            logger.warning("❌ No data collected")

    finally:
        if metrics_sink:
            metrics_sink.flush()

        # 7. Graceful shutdown
        await bedrock_manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run medical symptom elicitation dialogue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --profile-id 24 --strategy react
  python run.py --profile-id 24 --strategy stategraph --max-steps 5
  python run.py --strategy react --debug
        """
    )
    parser.add_argument(
        "--profile-id",
        type=str,
        default=None,
        help="Dialogue ID to load patient profile"
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="react",
        choices=["react", "stategraph"],
        help="Strategy to use (default: react)"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=10,
        help="Maximum number of dialogue steps (default: 10)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    args = parser.parse_args()

    logger = logging.getLogger(__name__)
    setup_logging(debug=args.debug)
    
    logger.info("Starting dialogue with strategy=%s, profile_id=%s, max_steps=%d",
                args.strategy, args.profile_id, args.max_steps)
    
    asyncio.run(main(
        dialogue_id=args.profile_id,
        strategy_name=args.strategy,
        max_steps=args.max_steps,
        debug=args.debug
    ))
