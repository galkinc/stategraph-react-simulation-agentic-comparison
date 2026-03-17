import json
from pathlib import Path
from typing import Iterator
from pydantic import BaseModel

from metrics_agregator.models import MetricEvent

def load_events(path: str) -> Iterator[MetricEvent]:

    with open(path) as f:
        for line in f:
            yield MetricEvent.model_validate_json(line)

def save_json(data: BaseModel, path: Path | str) -> None:
    path = Path(path)
    with path.open("w", encoding="utf-8") as f:
        f.write(data.model_dump_json(indent=2))
        