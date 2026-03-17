# src/pipeline/schemas.py
from pydantic import BaseModel, Field


class DialogueTurn(BaseModel):
    """Single utterance with speaker role"""
    speaker: str  # "Doctor" or "Patient"
    text: str
    turn_index: int  # order in dialogue


class ParsedDialogue(BaseModel):
    """
    Intermediate format after CSV parsing.
    Saved to JSONL for inspection and downstream use.
    """
    dialogue_id: str
    
    # Raw source
    raw_text: str  # Original dialogue string from CSV
    
    # Structured turns
    turns: list[DialogueTurn] = Field(default_factory=list)
    
    # Separated by role (for easy access in simulator)
    patient_utterances: list[str] = Field(default_factory=list)
    doctor_utterances: list[str] = Field(default_factory=list)
    
    # Metadata from CSV
    reference_summary: str | None = None
    automatic_summary: str | None = None
    
    # Quality flags (for consistency checks)
    is_balanced: bool = True  # roughly equal turns?
    has_patient_responses: bool = True
    
    class Config:
        frozen = True  # immutable after creation