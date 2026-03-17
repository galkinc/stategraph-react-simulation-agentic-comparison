# src/research/metrics_sink.py
"""
A lightweight metrics collector for comparing ReAct vs. StateGraph.
Writes metrics to CSV for subsequent analysis in pandas.
"""
import json
import logging
import time
from pathlib import Path
from typing import Protocol, runtime_checkable, Any, Literal
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

@runtime_checkable
class MetricsSink(Protocol):
    """Contract for collecting experimental metrics."""

    def record(
        self,
        strategy: Literal["react", "stategraph"],
        scenario_id: str,
        metric: str,
        value: float | int | str | bool,
        step: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Record one metric point."""
        ...

    def flush(self, output_path: Path | str | None = None) -> Path:
        """Save buffered metrics to CSV. Returns the file path."""
        ...


@dataclass
class MetricRecord:
    """The internal representation of the recorded metric."""
    timestamp: float = field(default_factory=time.time)
    strategy: str = ""
    scenario_id: str = ""
    metric: str = ""
    value: float | int | str | bool = 0
    step: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    run_id: str | None = None
    batch_id: str | None = None

    def to_row(self) -> dict[str, Any]:
        """Prepare a row for CSV export."""
        row = asdict(self)
        # Expanding the meta dict with a prefix
        if self.meta:
            for k, v in self.meta.items():
                row[f"meta_{k}"] = v
            del row["meta"]
        if row.get("run_id") is None:
            del row["run_id"]
        return row


class JSONLMetricsSink:
    
    def __init__(
            self, 
            buffer_size: int = 100, 
            output_dir: str = "output", 
            output_file: str = "research_metrics.jsonl"
        ):
        self.buffer: list[MetricRecord] = []
        self.buffer_size = buffer_size
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = output_file
        self._current_file: Path | None = None
    
    def record(self,
               strategy: Literal["react", "stategraph"],
               scenario_id: str,
               metric: str,
               value: float | int | str | bool,
               step: int | None = None,
               meta: dict[str, Any] | None = None,
               run_id: str | None = None,
               batch_id: str | None = None) -> None:
        self.buffer.append(MetricRecord(
            strategy=strategy,
            scenario_id=scenario_id,
            metric=metric,
            value=value,
            step=step,
            meta=meta or {},
            run_id=run_id,
            batch_id=batch_id
        ))
        if len(self.buffer) >= self.buffer_size:
            self.flush()
    
    def flush(self, output_path: Path | str | None = None, output_file: str | None = None) -> Path:
        if not output_file:
            output_file = self.output_file
        if not self.buffer:
            logger.debug("MetricsSink.flush() called with empty buffer")
            output_path = Path(output_path or self.output_dir / output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            return output_path
        
        logger.debug(f"Flushing {len(self.buffer)} metrics to {output_path}")

        output_path = Path(output_path or self.output_dir / output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, "a", encoding="utf-8") as f:
                for record in self.buffer:
                    # Direct serialization dataclass -> dict -> JSON
                    line = {
                        "timestamp": record.timestamp,
                        "strategy": record.strategy,
                        "scenario_id": record.scenario_id,
                        "metric": record.metric,
                        "value": record.value,
                        "step": record.step,
                        "run_id": record.run_id,
                        **({"batch_id": record.batch_id} if record.batch_id else {}),
                        **({"meta": record.meta} if record.meta else {})
                    }
                    f.write(json.dumps(line, ensure_ascii=False) + "\n")
            logger.debug(f"Successfully wrote {len(self.buffer)} records")
            self.buffer.clear()
        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")
            raise

        self._current_file = output_path
        return output_path
    
    @property
    def current_file(self) -> Path | None:
        return self._current_file