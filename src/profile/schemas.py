# src/profiles/schemas.py
from typing import Optional
from pydantic import BaseModel, Field


class ComprehendEntity(BaseModel):
    """Normalized entity from Amazon Comprehend Medical"""
    text: str
    category: str  # MEDICAL_CONDITION, ANATOMY, MEDICATION, etc.
    entity_type: Optional[str] = None  # BRAND_NAME, DX_NAME, etc.
    score: float
    traits: list[str] = Field(default_factory=list)  # NEGATION, DOSAGE, etc.
    begin_offset: Optional[int] = None
    end_offset: Optional[int] = None


class PatientProfile(BaseModel):
    """
    Consolidated patient profile for response simulation.
    Used to ground LLM responses in factual dialogue history.
    """
    dialogue_id: str
    raw_dialogue: str  # Full source text for RAG-style grounding
    
    # Aggregated medical facts from Comprehend
    conditions: list[str] = Field(default_factory=list)
    negated_conditions: list[str] = Field(default_factory=list)
    anatomy: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    treatments: list[str] = Field(default_factory=list)
    time_expressions: list[str] = Field(default_factory=list)
    
    # Separated utterances from parsed dialogue
    patient_utterances: list[str] = Field(default_factory=list)
    doctor_utterances: list[str] = Field(default_factory=list)
    
    # Demographics & Context
    age: Optional[str] = None
    gender: Optional[str] = None
    
    # Constraints for the simulator LLM
    allowed_topics: list[str] = Field(
        default_factory=list, 
        description="Topics the simulated patient can discuss based on profile"
    )
    forbidden_facts: list[str] = Field(
        default_factory=list,
        description="Facts explicitly denied or absent - simulator must not invent these"
    )
    
    # Metadata for debugging
    comprehend_entities_count: int = 0
    dialogue_turns_count: int = 0
    
    class Config:
        frozen = True
        