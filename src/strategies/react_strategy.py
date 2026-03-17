import time
import logging
import json
from pydantic import ValidationError

from config import settings
from src.aws_client import BedrockClientManager
from src.domain.coverage import check_coverage, CoverageRule
from src.research.metrics_sink import MetricsSink
from src.simulator.patient_simulator import PatientSimulator
from src.research.metrics_helpers import count_words, count_latency_ms, is_compliant

from src.domain.strategy_models import (
    ConversationTurn,
    AgentStepOutput,
    StrategyContext,
)

from src.strategies.base import (
    BaseStrategy,
    StrategyError,
    GENERAL_SYSTEM_PROMPT,
    ReactStep,
)
from src.research.scenario import ResearchScenario
from src.utils.retry import retry_with_exponential_backoff

logger = logging.getLogger(__name__)

# --- Strategy ---

class ReactStrategy(BaseStrategy):
    """
    ReAct-style cyclic strategy for symptom elicitation.
    """

    def __init__(
        self,
        client: BedrockClientManager | None = None,
        max_steps: int = settings.max_steps,
        simulator: PatientSimulator | None = None,
        profiles_path: str = settings.data.profiles_path,
        dialogue_id: str | None = None,
        fallback_text: str | None = None,
        dod_threshold: float = None,
        metrics_sink: MetricsSink | None = None,
        **kwargs
    ):
        # Call parent for common init (includes schema init, profile loading, etc.)
        super().__init__(
            client=client,
            max_steps=max_steps,
            fallback_text=fallback_text,
            metrics_sink=metrics_sink,
            profiles_path=profiles_path,
            simulator=simulator,
            dialogue_id=dialogue_id,
            dod_threshold=dod_threshold,
            **kwargs
        )

    async def _run_impl(self, scenario: ResearchScenario) -> dict | None:
        start_time = time.perf_counter()
        self._record_metric("started", 1)

        self._current_scenario_id = scenario.id

        # Setup initial context using domain models
        ctx = await self._setup_initial_context(scenario)

        try:
            async with self.llm_client.get_client() as client:
                for step_num in range(1, self.max_steps + 1):
                    ctx = await self._execute_step(ctx, step_num, client)
                    if self._should_terminate(ctx):
                        break
            return self._finalize(ctx, start_time)

        except StrategyError as e:
            logger.error("Strategy error: %s", e)
            self._record_metric("error", 1)
            raise
        except Exception as e:
            logger.exception("Unexpected error")
            self._record_metric("critical_error", 1)
            raise StrategyError(f"Execution failed: {e}") from e

    async def _setup_initial_context(self, scenario: ResearchScenario) -> StrategyContext:
        """Initialize conversation — seed message as 'user' for Bedrock API."""
        step_start = time.perf_counter()
        if scenario.profile_id and not self.current_profile:
            self._load_profile_sync(scenario.profile_id)

        tech_seed = "Hi"    
        hi_turn = ConversationTurn(
            role="user", # Bedrock requires user first and can't be blank
            content=[{"text": tech_seed}]
        )
        self.dialogue_recorder.record_turn(
            role="patient", 
            text=tech_seed, 
            step=0, 
            metadata={"type": "seed"}
        )

        if self.current_profile and self.current_profile.doctor_utterances:
            seed_message = self.current_profile.doctor_utterances[0]
        else:
            seed_message = self.fallback_text
            logger.warning("Using fallback seed: %s", seed_message)

        seed_turn = ConversationTurn(
            role="assistant",
            content=[{"text": seed_message}]
        )
        self.dialogue_recorder.record_turn(
            role="doctor", 
            text=seed_message, 
            step=0, 
            metadata={"type": "seed"}
        )
        
        message_latency_ms = count_latency_ms(step_start)

        sim_start = time.perf_counter()
        patient_reply = await self._generate_user_response(seed_message)
        sim_latency_ms = count_latency_ms(sim_start)

        
        self.dialogue_recorder.record_turn(
            role="patient", 
            text=patient_reply, 
            step=0
        )

        if self.current_profile:
            logger.info("\n Using profile ID: %s, gender: %s", 
                self.current_profile.dialogue_id, 
                self.current_profile.gender)
            
        logger.info("Step=0, DoctorQuestion=%s, UserAnswer=%s, Done=False cov_pct=0%%", seed_message, patient_reply)

        patient_turn = ConversationTurn(
            role="user",
            content=[{"text": patient_reply}]
        )
        
        self._record_batch_seed_metrics(
            step_num=0,
            message_word_count=count_words(seed_message),
            message_ms=message_latency_ms,
            simulator_latency_ms=sim_latency_ms,
            patient_message_word_count=count_words(patient_reply),
            e2e_latency_ms= count_latency_ms(step_start),
        )

        return StrategyContext(
            step_number=0,
            history=(hi_turn, seed_turn, patient_turn),
            scenario_id=scenario.id,
            is_terminal=False
        )

    async def _execute_step(
        self, 
        ctx: StrategyContext, 
        step_num: int, 
        client
    ) -> StrategyContext:
        """Single ReAct iteration: call LLM -> parse -> evaluate -> record."""
        step_start = time.perf_counter()

        # Prepare messages for Bedrock
        messages = [self._turn_to_bedrock_msg(t) for t in ctx.history]
        tool_config = {
            "tools": [self._react_json_schema],
            "toolChoice": {"tool": {"name": "react_step"}}
        }
        
        # Call LLM + parse stream (extracted for testability)
        try:
            raw_output, tool_use_id, ttft_ms, usage = await self._parse_bedrock_stream(
                client, messages, tool_config, step_num
            )
        except Exception as e:
            logger.error("LLM call failed at step %d: %s", step_num, e)
            raise StrategyError(f"LLM interaction failed at step {step_num}", 
                                context={"step": step_num, "scenario_id": ctx.scenario_id}) from e

        # Pydantic validation
        try:
            validated_step = ReactStep(**raw_output)

            self.dialogue_recorder.record_turn(
                role="doctor",
                text=validated_step.question,
                step=step_num,
                metadata={
                    "thought": validated_step.thought,
                    "done": validated_step.done,
                    "tool_use_id": tool_use_id
                }
            )
            agent_output = AgentStepOutput(
                thought=validated_step.thought,
                question=validated_step.question,
                done=validated_step.done,
                payload=validated_step.entities
            )

            # metrics from API
            output_tokens = usage.get("outputTokens", 0)
            input_tokens = usage.get("inputTokens", 0)

        except ValidationError as e:
            logger.error("Validation failed: %s", e)
            raise StrategyError("Agent output invalid") from e
        
        message_latency_ms = count_latency_ms(step_start)

        # Generate user response (simulator) — skip if question is None (done=True)
        sim_start = time.perf_counter()
        if validated_step.question:
            user_text = await self._generate_user_response(agent_output.question)
            # Validate simulator response — ensure non-empty text for Bedrock API
            if not user_text or not user_text.strip():
                logger.warning("Simulator returned empty response at step %d, using fallback", step_num)
                user_text = self.fallback_text
        else:
            user_text = ""  # No question, no answer — will not add user turn to history
        self._record_metric("patient_message_word_count",count_words(user_text), step=step_num)

        # Only record patient turn if there's actual content
        if user_text and user_text.strip():
            self.dialogue_recorder.record_turn(
                role="patient",
                text=user_text,
                step=step_num
            )
        sim_latency_ms = count_latency_ms(sim_start)

        # Evaluate termination (business logic - extracted)
        should_stop, eval_meta = self._evaluate_termination(agent_output, user_text)
        self._record_metric("agent_done", int(eval_meta.get("agent_requested_stop", False)), step=step_num)
        self._record_metric("final_done", int(should_stop), step=step_num)

        self._log_step(step_num, agent_output, user_text, eval_meta)

        e2e_latency_ms = count_latency_ms(step_start)
        word_count = count_words(validated_step.question)
        self._record_batch_agent_metrics(
            step_num=step_num,
            ttft_ms=ttft_ms,
            output_tokens=usage.get("outputTokens", 0),
            input_tokens=usage.get("inputTokens", 0),
            message_ms=message_latency_ms,
            message_word_count=word_count,
            is_compliant=is_compliant(word_count, settings.min_words, settings.max_words)
        )
        self._record_metric("coverage", eval_meta.get("coverage", 0), step=step_num)
        self._record_metric("coverage_collected", eval_meta.get("collected", 0), step=step_num)
        self._record_metric("coverage_target", eval_meta.get("target", 0), step=step_num)
        self._record_metric("simulator_latency_ms", sim_latency_ms, step=step_num)
        self._record_metric("e2e_latency_ms", e2e_latency_ms, step=step_num)

        # Update history (immutable pattern)
        new_history = list(ctx.history)
        new_history.extend(self._turns_for_step(user_text, validated_step, tool_use_id))

        # Prepare final payload if terminating
        final_payload = None
        if should_stop:
            final_payload = agent_output.payload.model_dump()

        return StrategyContext(
            step_number=step_num,
            history=tuple(new_history),
            current_payload=final_payload,
            scenario_id=ctx.scenario_id,
            is_terminal=should_stop,
            stop_reason="coverage_met" if should_stop else None
        )
    
    async def _parse_bedrock_stream(
            self,
            client,
            messages,
            tool_config,
            step_num
        ) -> tuple[dict, str, float, dict]:
        """Parse Bedrock stream — returns (raw_output_dict, tool_use_id, ttft_ms, usage)."""
        
        async def _stream_call():
            """Inner function for retry wrapper."""
            start = time.perf_counter()

            response = await client.converse_stream(
                modelId=settings.model.model_id,
                messages=messages,
                system=[{"text": GENERAL_SYSTEM_PROMPT}],
                inferenceConfig={"temperature": settings.model.temperature, "maxTokens": settings.model.max_tokens_json},
                toolConfig=tool_config
            )

            tool_use_id = None
            tool_input_raw = ""
            usage = {}

            async for event in response.get("stream", []):
                if "metadata" in event:
                    metadata = event["metadata"]
                    if "usage" in metadata:
                        usage = metadata["usage"]  # {"inputTokens": N, "outputTokens": M}
                    if "metrics" in metadata:
                        # Optional: latencyMs and other metrics from AWS
                        usage["latencyMs"] = metadata["metrics"].get("latencyMs")
                # Parsing toolUse
                if "contentBlockStart" in event:
                    start_block = event["contentBlockStart"].get("start", {})
                    if "toolUse" in start_block:
                        tool_use_id = start_block["toolUse"]["toolUseId"]
                        tool_input_raw = ""
                    elif "text" in start_block:
                        logger.debug("Step %d: Text block started (ignored)", step_num)
                elif "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"]["delta"]
                    if "toolUse" in delta:
                        tool_input_raw += delta["toolUse"].get("input", "")
                    elif "text" in delta:
                        logger.debug("Step %d: Text delta received (ignored)", step_num)
                elif "contentBlockStop" in event:
                    logger.debug("Step %d: Content block stopped", step_num)

            if not tool_input_raw or not tool_use_id:
                raise StrategyError(f"Empty tool input or missing tool_use_id at step {step_num}")

            ttft_ms = (time.perf_counter() - start) * 1000

            # Debugging: Printing raw JSON before validation
            raw_output = json.loads(tool_input_raw)
            logger.debug("ReAct Raw tool input: %s", raw_output)

            # Ensure required fields exist with defaults (defensive programming)
            if "done" not in raw_output:
                raw_output["done"] = False
                logger.warning("Step %d: Missing 'done' field, defaulting to False", step_num)
            if "entities" not in raw_output:
                raw_output["entities"] = {}
                logger.warning("Step %d: Missing 'entities' field, defaulting to empty", step_num)
            if "thought" not in raw_output:
                raw_output["thought"] = ""
                logger.warning("Step %d: Missing 'thought' field, defaulting to empty", step_num)
            if "question" not in raw_output:
                raw_output["question"] = None
                logger.warning("Step %d: Missing 'question' field, defaulting to None", step_num)

            return raw_output, tool_use_id, ttft_ms, usage
        
        # Execute with retry for transient errors
        return await retry_with_exponential_backoff(
            _stream_call,
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0
        )

    def _evaluate_termination(
        self, 
        output: AgentStepOutput, 
        user_reply: str
    ) -> tuple[bool, dict]:
        """
        Business logic: should we stop?
        Returns: (should_stop, metadata_for_logging)
        """
        if not self.current_profile:
            return output.done, {"note": "no_profile"}

        coverage = check_coverage(
            collected=output.payload,
            profile=self.current_profile,
            rule=CoverageRule(threshold=self.dod_threshold)
        )
        
        # Key research logic: agent can say "done", but we override if coverage low
        should_stop = output.done and coverage.threshold_met
        
        meta = {
            "coverage": coverage.coverage,
            "collected": coverage.collected_count,
            "target": coverage.target_count,
            "threshold_met": coverage.threshold_met,
            "agent_requested_stop": output.done
        }
        
        return should_stop, meta

    def _turns_for_step(
        self,
        user_text: str,
        validated_step: ReactStep,
        tool_use_id: str
    ) -> list[ConversationTurn]:
        """Create conversation turns with correct tool_use_id pairing."""

        assistant_turn = ConversationTurn(
            role="assistant",
            content=[{
                "toolUse": {
                    "toolUseId": tool_use_id,
                    "name": "react_step",
                    "input": validated_step.model_dump()
                }
            }]
        )

        # Only add user turn if there's actual content (avoid blank text for Bedrock API)
        if user_text and user_text.strip():
            user_turn = ConversationTurn(
                role="user",
                content=[
                    {"text": user_text},
                    {"toolResult": {
                        "toolUseId": tool_use_id,
                        "status": "success",
                        "content": [{"text": "User answered."}]
                    }}
                ]
            )
            return [assistant_turn, user_turn]
        else:
            # No user response (e.g., done=True with no question) — only return assistant turn
            return [assistant_turn]

    def _log_step(self, step_num: int, output: AgentStepOutput, user_reply: str, meta: dict):
        """Log with clear semantic labels."""
        cov = meta.get("coverage", 0)
        cov_pct = f"{cov * 100:.0f}%" if isinstance(cov, float) else "N/A"

        logger.info("Step=%d, DoctorQuestion=%s, UserAnswer=%s, Done=%s, cov_pct=%s",
                    step_num, output.question, user_reply, output.done, cov_pct)

    # def _finalize(self, ctx: StrategyContext, start_time: float) -> dict | None:
    #     """Return final result and log summary."""
    #     duration = time.perf_counter() - start_time

    #     termination_reason = ctx.stop_reason or (
    #         "max_steps" if ctx.step_number >= self.max_steps else "unknown"
    #     )
    #     success = ctx.is_terminal and ctx.current_payload is not None

    #     self.dialogue_recorder.save(
    #         strategy="react",
    #         scenario_id=ctx.scenario_id,
    #         run_id=self._run_id
    #     )

    #     self._record_batch_finalize_metrics(
    #         total_duration_sec=round(duration, 2),
    #         total_steps=ctx.step_number,
    #         termination_reason=termination_reason,
    #         success=int(success),
    #     )

    #     if success and ctx.current_payload:
    #         logger.info("FINISHED in %.2fs. Success: payload collected. Reason: %s", duration, ctx.stop_reason)
    #         return ctx.current_payload
    #     logger.info("FINISHED in %.2fs. Terminated without data. Reason: %s", duration, termination_reason or "unknown")

    #     return None
    def _finalize(self, ctx: StrategyContext, start_time: float) -> dict | None:
        """Return final result and log summary."""
        termination_reason = ctx.stop_reason or (
            "max_steps" if ctx.step_number >= self.max_steps else "unknown"
        )
        success = ctx.is_terminal and ctx.current_payload is not None

        return super()._finalize(
            start_time=start_time,
            total_steps=ctx.step_number,
            termination_reason=termination_reason,
            success=success,
            payload=ctx.current_payload,
            scenario_id=ctx.scenario_id,
        )