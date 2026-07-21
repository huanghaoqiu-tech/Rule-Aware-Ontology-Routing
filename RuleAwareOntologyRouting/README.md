# Rule-Aware Ontology Routing

Rule-Aware Ontology Routing experiment code for the BioPortal-50 benchmark
(10 SWRL+ / 40 SWRL− OWL files under `data/bioportal_owl/`).

## Layout

- `config.yaml` — CBF / routing / dataset parameters
- `cbf.py` — Counting Bloom Filter
- `hybrid_index.py` — hybrid inverted index (\(I_{tbox}\), \(I_{head}\))
- `weighted_scoring.py` — weighted scoring + τ / Top-k
- `ontology_parser.py` — offline TBox + SWRL head extraction
- `router.py` — online routing pipeline
- `queries.py` — 50 evaluation queries with ground truth
- `run_experiment.py` — build index, run BF/TOR/RR/Router, write metrics
- `results/` — `index_cache.json`, `metrics.json`

## Run

```bash
python -u RuleAwareOntologyRouting/run_experiment.py --rebuild-index
```
