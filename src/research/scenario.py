from dataclasses import dataclass, field 
from typing import Literal
import datetime


@dataclass
class ResearchScenario:
    id: str
    profile_id: str | None
    user_goal: str
    tier: Literal["T1", "T2", "T3"] = "T1"
    expected_fields: set[str] = field(default_factory=set)
    run_id: str | None = None

    def __post_init__(self):
        if self.run_id is None:
            self.run_id = f"{self.id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"