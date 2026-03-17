from dataclasses import dataclass, field
from typing import TypedDict, Any, Annotated, Sequence
from pydantic import BaseModel

from langgraph.graph import add_messages

# --- Bedrock API Contracts (External) ---
# These mirror AWS Bedrock Converse API structure

class BedrockText(TypedDict):
    text: str

class BedrockToolUse(TypedDict):
    toolUse: dict[str, Any] 

class BedrockToolResult(TypedDict):
    toolResult: dict[str, Any]

BedrockContent = BedrockText | BedrockToolUse | BedrockToolResult

# --- Domain Models (Internal) ---

@dataclass(frozen=True)
class ConversationTurn:
    """Immutable record of a single turn."""
    role: str  # 'user' | 'assistant'
    content: list[BedrockContent]
    tool_use_id: str | None = None
    tool_result: dict[str, Any] | None = None

@dataclass(frozen=True)
class AgentStepOutput:
    """Structured output from agent reasoning."""
    thought: str
    payload: BaseModel  # ActionPayload
    question: str
    done: bool = False

# only for ReAct
@dataclass(frozen=True)
class StrategyContext:
    """Immutable snapshot of execution state passed between steps."""
    step_number: int
    history: tuple[ConversationTurn, ...]  # Tuple for immutability
    scenario_id: str
    current_payload: dict[str, Any] | None = None
    is_terminal: bool = False
    stop_reason: str | None = None

# Only for stategraph
class StateGraphState(TypedDict):
    """
    State schema for LangGraph StateGraph strategy.

    messages: list[dict] - чистые dict для Bedrock API (без редюсера)
    step_number: int - номер шага
    current_payload: dict | None - финальные данные при завершении
    is_terminal: bool - флаг завершения
    stop_reason: str | None - причина остановки
    scenario_id: str - ID сценария
    """
    messages: list[dict]  # Чистые dict для Bedrock API
    step_number: int
    current_payload: dict | None = None
    is_terminal: bool
    stop_reason: str | None = None
    scenario_id: str
    # Временные поля для метрик
    _step_ttft_ms: float | None = None
    _agent_output: dict | None = None
    _tool_use_id: str | None = None
    _usage: dict | None = None
    _coverage: float | None = None