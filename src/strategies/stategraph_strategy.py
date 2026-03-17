from typing import Literal
import logging
import time
import json

from langgraph.graph import StateGraph, START, END

from src.domain.strategy_models import StateGraphState
from src.strategies.base import (
    BaseStrategy,
    StrategyError,
    GENERAL_SYSTEM_PROMPT,
    ActionPayload,
    ReactStep,
)
from config import settings
from src.aws_client import BedrockClientManager
from src.research.scenario import ResearchScenario
from src.research.metrics_sink import MetricsSink
from src.simulator.patient_simulator import PatientSimulator
from src.research.metrics_helpers import count_words, count_latency_ms, is_compliant
from src.domain.coverage import check_coverage, CoverageRule, CoverageResult
from src.utils.retry import retry_with_exponential_backoff

logger = logging.getLogger(__name__)


class StateGraphStrategy(BaseStrategy):
    """
    LangGraph StateGraph implementation for symptom elicitation.
    Uses Functional API (langgraph>=1.0.7).
    """

    def __init__(
        self,
        client: BedrockClientManager | None = None,
        max_steps: int = settings.max_steps,
        fallback_text: str | None = None,
        metrics_sink: MetricsSink | None = None,
        profiles_path: str = settings.data.profiles_path,
        simulator: PatientSimulator | None = None,
        dialogue_id: str | None = None,
        dod_threshold: float = None,
        batch_id: str | None = None,
    ):
        super().__init__(
            client=client,
            max_steps=max_steps,
            fallback_text=fallback_text,
            metrics_sink=metrics_sink,
            profiles_path=profiles_path,
            simulator=simulator,
            dialogue_id=dialogue_id,
            dod_threshold=dod_threshold,
            batch_id=batch_id,
        )

        self.graph = self._build_graph()
        self._step_start_time: float | None = None
        self._total_steps: int = 0
        self._final_payload: dict | None = None

    def _build_graph(self) -> StateGraph:
        """Build the state graph with nodes and edges."""
        builder = StateGraph(StateGraphState)

        builder.add_node("setup_context", self.node_setup_context)
        builder.add_node("agent_call", self.node_agent_call)
        builder.add_node("evaluate_stop", self.node_evaluate_stop)
        builder.add_node("simulator", self.node_simulator)

        builder.add_edge(START, "setup_context")
        builder.add_edge("setup_context", "agent_call")
        builder.add_edge("agent_call", "evaluate_stop")

        builder.add_conditional_edges(
            "evaluate_stop",
            self._should_terminate_edge,
            path_map={"end": END, "continue": "simulator"}
        )

        builder.add_edge("simulator", "agent_call")

        return builder.compile()

    async def _run_impl(self, scenario: ResearchScenario) -> dict | None:
        """Execute the state graph with full metrics tracking."""
        start_time = time.perf_counter()
        self._record_metric("started", 1)

        self._current_scenario_id = scenario.id
        self._total_steps = 0
        self._final_payload = None

        if scenario.profile_id and not self.current_profile:
            self._load_profile_sync(scenario.profile_id)

        state = StateGraphState(
            messages=[],
            step_number=0,
            current_payload=None,
            is_terminal=False,
            stop_reason=None,
            scenario_id=scenario.id
        )

        try:
            async for event in self.graph.astream(state, stream_mode="updates"):
                logger.debug("Graph event: %s", event)
                final_state = event

            return self._finalize(final_state, start_time)

        except StrategyError as e:
            logger.error("Strategy error: %s", e)
            self._record_metric("error", 1, step=0)
            raise
        except Exception as e:
            logger.exception("Unexpected error in StateGraph")
            self._record_metric("critical_error", 1, step=0)
            raise StrategyError(f"Execution failed: {e}") from e

    # =========================================================================
    # NODES
    # =========================================================================

    async def node_setup_context(self, state: StateGraphState) -> dict:
        """Initialize conversation with seed message (step 0)."""
        step_start = time.perf_counter()

        seed_message = self._get_seed_message()

        tech_seed = "Hi"
        messages = [
            {"role": "user", "content": [{"text": tech_seed}]},
            {"role": "assistant", "content": [{"text": seed_message}]},
        ]

        self._record_seed_turns(tech_seed, seed_message)

        message_latency_ms = count_latency_ms(step_start)

        patient_reply, sim_latency_ms = await self._simulate_patient_response(seed_message, step_start)
        messages.append({"role": "user", "content": [{"text": patient_reply}]})

        self._record_patient_turn(patient_reply, step=0)

        if self.current_profile:
            logger.info("Using profile ID: %s, gender: %s",
                        self.current_profile.dialogue_id,
                        self.current_profile.gender)

        self._log_step(0, "", seed_message, patient_reply, 0.0)

        self._record_batch_seed_metrics(
            step_num=0,
            message_word_count=count_words(seed_message),
            message_ms=message_latency_ms,
            simulator_latency_ms=sim_latency_ms,
            patient_message_word_count=count_words(patient_reply),
            e2e_latency_ms= count_latency_ms(step_start)
        )

        return {"messages": messages, "step_number": 0}

    async def node_agent_call(self, state: StateGraphState) -> dict:
        """Call LLM and parse response."""
        step_num = state["step_number"] + 1
        self._step_start_time = time.perf_counter()
        self._total_steps = step_num

        messages = state["messages"]
        tool_config = {
            "tools": [self._react_json_schema],
            "toolChoice": {"tool": {"name": "react_step"}}
        }

        message_start = time.perf_counter()
        validated_step, tool_use_id, ttft_ms, usage = await self._call_llm(messages, step_num)
        message_latency_ms = count_latency_ms(message_start)

        # Record LLM metrics immediately (in case simulator is not called)
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

        self._record_doctor_turn(validated_step, step_num, tool_use_id)

        messages.append({
            "role": "assistant",
            "content": [{
                "toolUse": {
                    "toolUseId": tool_use_id,
                    "name": "react_step",
                    "input": validated_step.model_dump()
                }
            }]
        })

        return {
            "messages": messages,
            "step_number": step_num,
            "_step_ttft_ms": ttft_ms,
            "_agent_output": validated_step.model_dump(),
            "_tool_use_id": tool_use_id,
            "_usage": usage,
        }

    async def node_evaluate_stop(self, state: StateGraphState) -> dict:
        """Evaluate termination criteria."""
        agent_output = state.get("_agent_output")
        if not agent_output:
            logger.error("Agent_output missing — graph flow broken")
            raise ValueError("Agent output is required but missing in state")

        step_num = state["step_number"]

        done = agent_output.get("done", False)
        self._record_metric("agent_done", int(done), step=step_num)
        coverage_result = self._compute_coverage_result(agent_output)
        coverage = coverage_result.coverage
        self._record_metric("coverage", coverage, step=step_num)
        self._record_metric("coverage_collected", coverage_result.collected_count, step=step_num)
        self._record_metric("coverage_target", coverage_result.target_count, step=step_num)

        # 1. Check max steps first
        if step_num >= self.max_steps:
            logger.info("Max steps reached (%d)", self.max_steps)
            self._log_step(
                step_num,
                agent_output.get("thought", ""),
                agent_output.get("question", ""),
                "(no response)",
                coverage
            )
            return {"is_terminal": True, "stop_reason": "max_steps"}

        # 2. No profile -> trust agent's done flag (like ReAct)
        if not self.current_profile:
            return {
                "is_terminal": done,
                "stop_reason": "agent_done" if done else None,
            }

        # 3. Have profile → check coverage (already computed above)
        logger.debug("Step %d: entities=%s, coverage=%.2f", step_num, agent_output.get("entities", {}), coverage)

        threshold_met = coverage >= settings.coverage.coverage_threshold

        # 4. Termination: done AND coverage threshold met
        should_stop = done and threshold_met
        self._record_metric("final_done", int(should_stop), step=step_num)

        if should_stop:
            logger.info("Coverage: %.2f, threshold_met: %s", coverage, threshold_met)
            self._final_payload = agent_output.get("entities", {})

            # Record simulator metrics (simulator not called)
            # self._record_metric("simulator_latency_ms", 0.0, step=step_num)
            self._record_metric("e2e_latency_ms", count_latency_ms(self._step_start_time), step=step_num)

        return {
            "is_terminal": should_stop,
            "stop_reason": "coverage_met" if should_stop else None,
        }

    async def node_simulator(self, state: StateGraphState) -> dict:
        """Generate patient response and add to messages."""
        agent_output = state.get("_agent_output", {})
        question = agent_output.get("question")
        tool_use_id = state.get("_tool_use_id")
        step_num = state.get("step_number", 0)

        if not question:
            logger.info("No question to simulate (done=True)")
            return {"messages": state["messages"]}

        user_text, sim_latency_ms = await self._simulate_patient_response(question, self._step_start_time)
        
        # Validate simulator response — ensure non-empty text for Bedrock API
        if not user_text or not user_text.strip():
            logger.warning("Simulator returned empty response at step %d, using fallback", step_num)
            user_text = self.fallback_text
        
        self._record_metric("patient_message_word_count",count_words(user_text), step=step_num)
        e2e_latency_ms = count_latency_ms(self._step_start_time)

        # Record simulator-specific metrics (LLM metrics recorded in node_agent_call)
        self._record_metric("simulator_latency_ms", sim_latency_ms, step=step_num)
        self._record_metric("e2e_latency_ms", e2e_latency_ms, step=step_num)

        self._total_steps = step_num

        messages = list(state["messages"])
        # Only add user turn if there's actual content (avoid blank text for Bedrock API)
        if user_text and user_text.strip():
            messages.append({
                "role": "user",
                "content": [
                    {"text": user_text},
                    {"toolResult": {
                        "toolUseId": tool_use_id,
                        "status": "success",
                        "content": [{"text": "User answered."}]
                    }}
                ]
            })

            self._record_patient_turn(user_text, step=step_num)

        # Compute coverage for logging only (already recorded in node_evaluate_stop)
        coverage_result = self._compute_coverage_result(agent_output)
        self._log_step(step_num, agent_output.get("thought", ""), question, user_text, coverage_result.coverage)

        return {"messages": messages}

    # =========================================================================
    # EDGE FUNCTIONS
    # =========================================================================

    def _should_terminate_edge(self, state: StateGraphState) -> Literal["end", "continue"]:
        """Conditional edge logic for termination."""
        return "end" if state.get("is_terminal", False) else "continue"

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_seed_message(self) -> str:
        """Get seed message from profile or fallback."""
        if self.current_profile and self.current_profile.doctor_utterances:
            return self.current_profile.doctor_utterances[0]
        seed_message = self.fallback_text
        logger.warning("Using fallback seed: %s", seed_message)
        return seed_message

    def _record_seed_turns(self, tech_seed: str, seed_message: str) -> None:
        """Record initial seed turns."""
        self.dialogue_recorder.record_turn(role="patient", text=tech_seed, step=0, metadata={"type": "seed"})
        self.dialogue_recorder.record_turn(role="doctor", text=seed_message, step=0, metadata={"type": "seed"})

    async def _simulate_patient_response(self, question: str, step_start: float) -> tuple[str, float]:
        """Generate patient response and return (text, latency_ms)."""
        sim_start = time.perf_counter()
        user_text = await self._generate_user_response(question)
        sim_latency_ms = count_latency_ms(sim_start)
        return user_text, sim_latency_ms

    def _record_patient_turn(self, text: str, step: int) -> None:
        """Record patient turn in dialogue recorder."""
        self.dialogue_recorder.record_turn(role="patient", text=text, step=step)

    def _record_doctor_turn(self, validated_step: ReactStep, step_num: int, tool_use_id: str) -> None:
        """Record doctor turn in dialogue recorder."""
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

    def _compute_coverage_result(self, agent_output: dict) -> CoverageResult:
        """Compute coverage from agent output payload. Returns full CoverageResult."""
        if not self.current_profile:
            return CoverageResult(
                coverage=0.0,
                collected_count=0,
                target_count=0,
                threshold_met=False
            )

        payload = agent_output.get("entities", {})
        try:
            validated_payload = ActionPayload(**payload)
            coverage_result = check_coverage(
                collected=validated_payload,
                profile=self.current_profile,
                rule=CoverageRule(threshold=self.dod_threshold)
            )
            return coverage_result
        except Exception as e:
            logger.warning("Failed to validate payload: %s", e)
            return CoverageResult(
                coverage=0.0,
                collected_count=0,
                target_count=0,
                threshold_met=False
            )

    async def _call_llm(self, messages: list, step_num: int) -> tuple[ReactStep, str, float, dict]:
        """Call LLM and parse stream. Returns (validated_step, tool_use_id, ttft_ms, usage)."""

        async def _llm_call():
            """Inner function for retry wrapper."""
            ttft_ms = None
            first_token_received = False
            tool_use_id = None
            tool_input_raw = ""
            usage = {}
            tool_config = {
                "tools": [self._react_json_schema],
                "toolChoice": {"tool": {"name": "react_step"}}
            }

            async with self.llm_client.get_client() as client:
                response = await client.converse_stream(
                    modelId=settings.model.model_id,
                    messages=messages,
                    system=[{"text": GENERAL_SYSTEM_PROMPT}],
                    inferenceConfig={"temperature": 0.1, "maxTokens": 300},
                    toolConfig=tool_config
                )

                async for event in response.get("stream", []):
                    if "metadata" in event:
                        metadata = event["metadata"]
                        if "usage" in metadata:
                            usage = metadata["usage"]
                        if "metrics" in metadata:
                            usage["latencyMs"] = metadata["metrics"].get("latencyMs")

                    if "contentBlockStart" in event:
                        if not first_token_received:
                            ttft_ms = (time.perf_counter() - self._step_start_time) * 1000
                            first_token_received = True

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

            try:
                validated_step = ReactStep(**raw_output)
            except Exception as e:
                logger.error("Validation failed: %s", e)
                raise StrategyError(f"Agent output invalid at step {step_num}: {e}") from e

            return validated_step, tool_use_id, ttft_ms, usage

        # Execute with retry for transient errors
        return await retry_with_exponential_backoff(
            _llm_call,
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0
        )

    # def _finalize(self, final_state: dict, start_time: float) -> dict | None:
    #     """Return final result and log summary."""
    #     duration = time.perf_counter() - start_time

    #     stop_reason = None
    #     if final_state and "evaluate_stop" in final_state:
    #         eval_output = final_state["evaluate_stop"]
    #         if isinstance(eval_output, dict):
    #             stop_reason = eval_output.get("stop_reason")

    #     termination_reason = stop_reason or (
    #         "max_steps" if self._total_steps >= self.max_steps else "unknown"
    #     )
    #     success = stop_reason == "coverage_met" and self._final_payload is not None

    #     self.dialogue_recorder.save(
    #         strategy="stategraph",
    #         scenario_id=self._current_scenario_id,
    #         run_id=self._run_id
    #     )

    #     self._record_batch_finalize_metrics(
    #         total_duration_sec=round(duration, 2),
    #         total_steps=self._total_steps,
    #         termination_reason=termination_reason,
    #         success=success
    #     )

    #     if success and self._final_payload:
    #         logger.info("FINISHED in %.2fs. Success: payload collected. Reason: %s", duration, stop_reason)
    #         return self._final_payload
    #     logger.info("FINISHED in %.2fs. Terminated. Reason: %s", duration, termination_reason)
        
    #     return None

    def _log_step(self, step_num: int, thought: str, question: str, user_reply: str, coverage: float | None) -> None:
        """Log step with clear semantic labels."""
        if coverage is not None:
            cov_pct = f"{coverage * 100:.0f}%"
        else:
            cov_pct = "N/A"
        logger.info("Step=%d, DocThink=%s, DocQ=%s, UserAnswer=%s, cov_pct=%s",
                    step_num, thought, question, user_reply, cov_pct)
    def _finalize(self, final_state: dict, start_time: float) -> dict | None:
        """Return final result and log summary."""
        stop_reason = None
        if final_state and "evaluate_stop" in final_state:
            eval_output = final_state["evaluate_stop"]
            if isinstance(eval_output, dict):
                stop_reason = eval_output.get("stop_reason")

        termination_reason = stop_reason or (
            "max_steps" if self._total_steps >= self.max_steps else "unknown"
        )
        success = stop_reason == "coverage_met" and self._final_payload is not None

        return super()._finalize(
            start_time=start_time,
            total_steps=self._total_steps,
            termination_reason=termination_reason,
            success=success,
            payload=self._final_payload,
            scenario_id=self._current_scenario_id
        )