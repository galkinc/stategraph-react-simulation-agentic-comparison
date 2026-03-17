"""
Base strategy contract for fair comparison between ReAct and StateGraph.
Kept minimal for research agility — no over-engineering.
"""
from abc import ABC, abstractmethod
from typing import Any
import json
import logging
import time

from pydantic import BaseModel, Field, field_validator, ValidationInfo

from src.domain.strategy_models import StrategyContext, ConversationTurn
from src.research.scenario import ResearchScenario
from src.research.metrics_sink import MetricsSink
from src.research.dialogue_recorder import DialogueRecorder
from src.profile.schemas import PatientProfile
from src.simulator.patient_simulator import PatientSimulator
from src.aws_client import bedrock_manager, BedrockClientManager
from src.bedrock_tools import BedrockToolItem
from config import settings

logger = logging.getLogger(__name__)

# --- System Prompt (shared between all strategies) ---
GENERAL_SYSTEM_PROMPT = f"""
You are a medical symptom elicitation agent.
Keep your respond to user in exactly {settings.min_words} to {settings.max_words} words. Be concise.
Extract any medical entities into the 'entities' field (conditions, anatomy, medications, etc.).
Set 'done' to true ONLY when you have sufficient information, 'done' field must be at the TOP LEVEL.
"""


# --- Shared Pydantic Models (used by all strategies) ---
class ActionPayload(BaseModel):
    """Shared payload schema for medical entity extraction."""
    conditions: list[str] = Field(
        default_factory=list, description="trait SYMPTOM или DIAGNOSIS, score >= 0.7"
    )
    anatomy: list[str] = Field(
        default_factory=list, description="ANATOMY/SYSTEM_ORGAN_SITE, score >= 0.6"
    )
    onset_duration: list[str] = Field(
        default_factory=list, description="TIME_EXPRESSION/TIME_TO_DX_NAME"
    )
    treatments: list[str] = Field(
        default_factory=list, description="TEST_TREATMENT_PROCEDURE"
    )
    negated_conditions: list[str] = Field(
        default_factory=list, description="MEDICAL_CONDITION/DX_NAME + trait NEGATION"
    )
    medications: list[str] | None = Field(
        default=None, description="List of medications, nullable"
    )

    @field_validator('medications', mode='before')
    @classmethod
    def parse_medications(cls, v, info: ValidationInfo | None = None):
        if v is None or isinstance(v, list):
            return v
        if isinstance(v, str):
            return [x.strip() for x in v.split(',') if x.strip()]
        return v


class ReactStep(BaseModel):
    """Shared step schema for ReAct-style reasoning."""
    thought: str = Field(..., description="Short reasoning, 1 sentence max")
    question: str | None = Field(
        default=None,
        description=f"Question to user, exactly {settings.min_words}-{settings.max_words}. Nullable when done=True",
        max_length=settings.max_words * 6
    )
    done: bool = Field(..., description="Indicates if conversation is done and enough entities collect base by the dialog")
    entities: ActionPayload = Field(..., description="Collected entities")


class StrategyError(Exception):
    """Base exception for strategy execution failures."""
    def __init__(self, message: str, context: dict | None = None):
        super().__init__(message)
        self.context = context or {}
    pass


class BaseStrategy(ABC):
    """
    Abstract base for all strategies in this research.

    Contract:
    - Accept ResearchScenario (same input for all strategies)
    - Return dict | None (same output format)
    - Record metrics via shared MetricsSink (not here — injected in __init__)
    """
    
    # Class-level cache for JSON schema (shared across instances)
    _react_json_schema: dict | None = None

    def __init__(
        self,
        client: BedrockClientManager | None = None,
        max_steps: int = 10,
        fallback_text: str = "I don't have more details right now.",
        metrics_sink: MetricsSink | None = None,
        run_id: str | None = None,
        profiles_path: str = settings.data.profiles_path,
        simulator: PatientSimulator | None = None,
        dialogue_id: str | None = None,
        dod_threshold: float = None,
        batch_id: str | None = None,
        **kwargs
    ):
        self.max_steps = max_steps
        self.fallback_text = fallback_text
        self.metrics_sink = metrics_sink
        self._run_id = run_id
        self._batch_id = batch_id
        self.dialogue_recorder = DialogueRecorder(output_dir=settings.data.dialogues_output_path)
        self.profiles_path = profiles_path
        self.simulator = simulator or PatientSimulator()
        self.current_profile: PatientProfile | None = None
        
        # LLM client initialization (shared)
        self.llm_client = client or bedrock_manager
        
        # DOD threshold (shared)
        self.dod_threshold = dod_threshold or settings.coverage.coverage_threshold
        
        # Profile loading (shared)
        if dialogue_id:
            self._load_profile_sync(dialogue_id)
        
        # Lazy schema init (shared across all strategies)
        if self._react_json_schema is None:
            self._react_json_schema = BedrockToolItem.from_pydantic(
                ReactStep,
                tool_name="react_step",
                description="ReAct step for symptom elicitation"
            ).to_bedrock_dict()


    @abstractmethod
    async def _run_impl(self, scenario: ResearchScenario) -> dict[str, Any] | None:
        """Concrete logic must be implemented here."""
        ...

    async def run(self, scenario: ResearchScenario) -> dict[str, Any] | None:
        self._run_id = scenario.run_id
        self._current_scenario_id = scenario.id
        return await self._run_impl(scenario)

    #  --- Metrics Helpers ---

    def _record_metric(
        self,
        name: str,
        value: Any,
        step: int | None = None,
        scenario_id: str | None = None,
        meta: dict | None = None,
        run_id: str | None = None,
        batch_id: str | None = None
    ) -> None:
        """Write the metric via MetricsSink, if present."""

        if self.metrics_sink:
            strategy_name = self.__class__.__name__.lower().replace("strategy", "")
            final_sid = scenario_id or getattr(self, '_current_scenario_id', 'unknown')
            final_run_id = run_id or self._run_id
            final_batch_id = batch_id or self._batch_id

            self.metrics_sink.record(
                strategy=strategy_name,
                scenario_id=final_sid,
                metric=name,
                value=value,
                step=step,
                meta=meta or {},
                run_id=final_run_id,
                batch_id=final_batch_id
            )

    def _record_batch_seed_metrics(
        self,
        step_num: int,
        message_ms: float,
        message_word_count: int,
        simulator_latency_ms: float,
        patient_message_word_count: int,
        e2e_latency_ms: float,
        scenario_id: str | None = None,
        run_id: str | None = None,
    ) -> None:
        """Write a bath of the seed metrics via _record_metric."""
        metrics = {
            "message_ms": message_ms,
            "message_word_count": message_word_count,
            "simulator_latency_ms": simulator_latency_ms,
            "patient_message_word_count": patient_message_word_count,
            "e2e_latency_ms": e2e_latency_ms,
        }

        for metric_name, value in metrics.items():
            self._record_metric(
                name=metric_name,
                value=value,
                step=step_num,
                scenario_id=scenario_id,
                run_id=run_id
            )
    
    def _record_batch_agent_metrics(
        self,
        step_num: int,
        ttft_ms: float,
        output_tokens: int ,
        input_tokens: int,
        message_ms: float,
        message_word_count: int,
        is_compliant: bool | int,
        scenario_id: str | None = None,
        run_id: str | None = None
    ) -> None:
        """Write a bath of the agent metrics via _record_metric."""
        metrics = {
            "ttft_ms": ttft_ms,
            "output_tokens": output_tokens,
            "input_tokens": input_tokens,
            "message_ms": message_ms,
            "message_word_count": message_word_count,
            "is_compliant": int(is_compliant)
        }

        for metric_name, value in metrics.items():
            self._record_metric(
                name=metric_name,
                value=value,
                step=step_num,
                scenario_id=scenario_id,
                run_id=run_id
            )

    def _record_batch_finalize_metrics(
        self,
        total_duration_sec: float,
        total_steps: int ,
        termination_reason: str,
        success: bool | int,
        scenario_id: str | None = None,
        run_id: str | None = None
    ) -> None:
        metrics = {
            "total_duration_sec": total_duration_sec,
            "total_steps": total_steps,
            "termination_reason": termination_reason,
            "success": int(success),
            "stop": 1
        }

        for metric_name, value in metrics.items():
            self._record_metric(
                name=metric_name,
                value=value,
                scenario_id=scenario_id,
                run_id=run_id
            )        

    # --- Protected hooks for subclasses (extension points) ---
    
    def _should_terminate(self, context: StrategyContext, **kwargs) -> bool:
        """
        Hook: custom termination logic.
        Default: stop if context.is_terminal or max_steps reached.
        """
        return context.is_terminal or context.step_number >= self.max_steps

    # --- Common utility methods for all strategies ---

    def _load_profile_sync(self, dialogue_id: str) -> bool:
        """Load PatientProfile from JSONL by dialogue_id — sync I/O for research."""
        try:
            with open(self.profiles_path, 'r', encoding='utf-8') as f:
                for line in f:
                    data = json.loads(line)
                    if data.get('dialogue_id') == dialogue_id:
                        self.current_profile = PatientProfile(**data)
                        logger.info("Loaded profile for dialogue_id: %s", dialogue_id)
                        return True
            logger.warning("Profile not found for dialogue_id: %s", dialogue_id)
            return False
        except Exception as e:
            logger.error("Failed to load profile: %s", e)
            return False

    async def _generate_user_response(self, question: str) -> str:
        """Generate simulator response — isolated for mocking."""
        return (
            await self.simulator.generate_response(self.current_profile, question)
            if self.current_profile else self.fallback_text
        )

    def _turn_to_bedrock_msg(self, turn: ConversationTurn) -> dict:
        """Map internal domain model to Bedrock API format."""
        return {"role": turn.role, "content": turn.content}

    def _finalize(
        self,
        start_time: float,
        total_steps: int,
        termination_reason: str,
        success: bool,
        payload: dict | None,
        scenario_id: str,
        strategy_name: str | None = None
    ) -> dict | None:
        """Return final result and log summary."""
        if strategy_name is None:
            strategy_name = self.__class__.__name__.lower().replace("strategy", "")
        duration = time.perf_counter() - start_time

        self.dialogue_recorder.save(
            strategy=strategy_name,
            scenario_id=scenario_id,
            run_id=self._run_id
        )

        self._record_batch_finalize_metrics(
            total_duration_sec=round(duration, 2),
            total_steps=total_steps,
            termination_reason=termination_reason,
            success=int(success),
        )

        if success and payload:
            logger.info("FINISHED in %.2fs. Success: payload collected. Reason: %s", duration, termination_reason)
            return payload
        logger.info("FINISHED in %.2fs. Terminated without data. Reason: %s", duration, termination_reason or "unknown")

        return None