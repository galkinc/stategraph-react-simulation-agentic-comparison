---

## Data & Reproducibility

### Dataset

- **45 scenarios** derived from real doctor-patient dialogues
- **135 runs** (3 batches × 45 scenarios × 2 strategies)
- **Grounded simulation:** Patient simulator constrained by structured profiles (AWS Comprehend Medical)

---

### Data Files

| File | Content |
| ---- | ------- |
| `data/output/aggregate_metrics.json` | Full aggregated metrics (by_run, by_scenario, experiment_statistics) |
| `data/output/research_metrics.jsonl` | Raw event-level metrics |
| `data/output/dialogues/` | Dialogue transcripts |

### Configuration

| Parameter | Value |
| --------- | ----- |
| Model | Anthropic Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`) |
| Max steps | 15 |
| Coverage threshold | 0.2 |
| Response length | 5-12 words |

### Scripts

| Script | Purpose |
| ------ | ------- |
| `scripts/generate_results_tables.py` | Generate Markdown tables from raw data |
| `scripts/generate_figures.py` | Generate figures (PNG + SVG) |

---

## Citation

```bibtex
@misc{stategraph-react-benchmark-2026,
  title={LangGraph vs. ReAct: An Engineering Benchmark for Conversational Agents},
  author={[Your Name]},
  year={2026},
  url={https://github.com/[your-username]/stategraph-react-simulation-agentic-comparison}
}
```

---

## License

MIT License — see [LICENSE](../LICENSE) for details.

---

## Acknowledgments

- Real dialogue corpora for scenario generation
- AWS Comprehend Medical for entity extraction
- Anthropic Claude 3 Haiku (Bedrock) for LLM

---

*For raw data, see `data/output/aggregate_metrics.json`. For figure files, see `docs/figures/`.*