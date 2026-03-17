from pathlib import Path
from typing import Any
from dataclasses import dataclass, asdict
import json
import time
import datetime

@dataclass
class DialogueTurn:
    role: str
    text: str | None
    step: int
    timestamp: float
    metadata: dict[str, Any] | None = None

class DialogueRecorder:
    def __init__(self, output_dir: str = "output/dialogues"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.turns: list[DialogueTurn] = []
    
    def record_turn(self, role: str, text: str, step: int, metadata: dict[str, Any] | None = None):
        self.turns.append(DialogueTurn(
            role=role,
            text=text,
            step=step,
            timestamp=time.time(),
            metadata=metadata or {}
        ))
    
    def save(self, strategy: str, scenario_id: str, run_id: str | None = None) -> Path:
        if not run_id:
            run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # react_25_20260227_195538.json
        filepath = self.output_dir / f"{strategy}_{scenario_id}_{run_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([asdict(t) for t in self.turns], f, ensure_ascii=False, indent=2)
        return filepath
    
    def clear(self):
        self.turns.clear()