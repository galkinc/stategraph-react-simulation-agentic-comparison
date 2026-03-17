production-grade research pipelines

jsonl logs
   ↓
Event normalization
   ↓
Dialog Run Model
   ↓
Aggregations
   ↓
Comparison
   ↓
Export JSON


logs.jsonl
   ↓
load_events()
   ↓
group_by_run()
   ↓
DialogRun objects
   ↓
compute_run_metrics()
   ↓
aggregate_by_scenario()
   ↓
compare_strategies()


jsonl logs
   ↓
Pydantic (Event model)        ← validation
   ↓
internal python objects       ← быстрые структуры
   ↓
Pydantic (Output schema)      ← стабильный контракт
   ↓
JSON export

- НЕ считать метрики напрямую из событий. Сначала собираем run state.
- Использвать pydantic

validate inputs
model core entities
avoid modeling internal math
model outputs

В build_runs нужно обязательно игнорировать step 0 при агрегации.

Но не удалять его из данных.

Потому что он нужен для:

init message length
doctor seed

Поэтому:

run.steps
   0 → seed
   1..N → real dialog


----

mini evaluation framework

JSONL
 ↓
MetricEvent
 ↓
build_runs
 ↓
DialogRun
 ↓
compute_run_metrics
 ↓
ScenarioMetrics
 ↓
aggregate_by_scenario
 ↓
comparison
 ↓
export


Сейчас у вас 45 сценариев × 2 стратегии.

Это paired experiment.

Поэтому правильная статистика:

delta_per_scenario

а не средние.

Вы это уже начали делать.

Но можно усилить.


13. Bootstrap significance test

Это то, что используют в LLM evaluation papers.

Идея:

45 сценариев

делаем bootstrap:

10000 выборок

каждый раз считаем:

mean(delta_success_rate)

Получаем confidence interval.


JSONL events
      ↓
build_runs
      ↓
DialogRun
      ↓
compute_run_metrics
      ↓
ScenarioMetrics
      ↓
aggregate_by_scenario
      ↓
ScenarioAggregate
      ↓
compare_strategies
      ↓
run_all_tests
      ↓
ExportedMetrics

events -> runs -> metrics -> aggregation -> comparison -> statistics

Это почти textbook структура для LLM experiment evaluation.