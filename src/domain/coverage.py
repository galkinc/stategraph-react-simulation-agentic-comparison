# src/domain/coverage.py
"""
Domain rules for symptom elicitation coverage.
Defines what constitutes a 'complete' medical consultation.
"""
from dataclasses import dataclass, field
from config import settings

# Domain constants: determine the length of the anamnesis collection
COLLECTED_FIELDS = [
    'conditions', 'anatomy', 'medications', 'treatments', 'onset_duration'
    ]
TARGET_FIELDS = [
    'conditions', 'anatomy', 'medications', 'treatments', 'time_expressions'
    ]

@dataclass(frozen=True)
class CoverageRule:
    """
    Dialogue termination rule.
    Combines structure (what we count) and threshold (how much is enough).
    """
    threshold: float = settings.coverage.coverage_threshold
    collected_fields: list[str] = field(default_factory=lambda: COLLECTED_FIELDS.copy())
    target_fields: list[str] = field(default_factory=lambda: TARGET_FIELDS.copy())

@dataclass(frozen=True)
class CoverageResult:
    coverage: float
    collected_count: int
    target_count: int
    threshold_met: bool
    note: str | None = None

def check_coverage(
    collected: object,
    profile: object,
    rule: CoverageRule = CoverageRule()
) -> CoverageResult:
    """
    Check if collected entities meet the coverage rule.
    Pure domain function — no side effects.
    """
    def _count(obj: object, fields: list[str]) -> int:
        count = 0
        for field in fields:
            items = getattr(obj, field, None)
            if isinstance(items, list):
                count += sum(1 for x in items if x)
            elif isinstance(items, str) and items.strip():
                count += 1
        return count
    
    collected_count = _count(collected, rule.collected_fields)
    target_count = _count(profile, rule.target_fields)
    
    if target_count == 0:
        return CoverageResult(
            coverage=1.0,
            collected_count=collected_count,
            target_count=0,
            threshold_met=True,
            note="no_target_entities"
        )
    
    coverage = collected_count / target_count
    return CoverageResult(
        coverage=round(coverage, 2),
        collected_count=collected_count,
        target_count=target_count,
        threshold_met=coverage >= rule.threshold
    )