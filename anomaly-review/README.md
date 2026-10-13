# Tutor Session Review Research Pipeline

This is an isolated offline project for event normalization, question-session reconstruction, and evidence-linked behavioral metrics. It does not modify the ChatSight application and does not contain production student data.

```bash
cd anomaly-review
uv sync
uv run pytest -q

uv run session-review fixtures/synthetic_sessions.json --output /tmp/sessions.json
uv run session-metrics /tmp/sessions.json --output /tmp/metrics.json
uv run session-rank /tmp/sessions.json --output /tmp/ranking.json
uv run session-ranking-demo --output /tmp/synthetic-ranking.json
```

Outputs are create-only so an existing analysis file cannot be overwritten accidentally.

Phase 2C adds an offline, provisional adapter workflow for an approved deidentified
JSON export. See `PHASE2C_VALIDATION.md` before using it. The committed example is
synthetic and does not document the actual tutor export schema.

```bash
uv run session-real-validate fixtures/phase2c_export.synthetic.json \
  --mapping fixtures/phase2c_mapping.synthetic.json \
  --dataset-id synthetic-phase2c-demo \
  --quality-output /tmp/phase2c-quality.json
```

## Instructor UI prototype

The UI uses React, TypeScript, Vite, and Lucide icons. It is a static single-page application with no backend, model calls, or database access.

```bash
cd anomaly-review/frontend
npm install
npm run dev
```

Open `http://127.0.0.1:4173`. The committed synthetic data is ready to use. Instructor reviews are stored only in the browser's local storage.

Run its checks with:

```bash
npm test
npm run build
```

See `FRONTEND_PROTOTYPE.md` for the data boundary, placeholders, and future integration path.

- `PHASE1_FEASIBILITY.md`: local data feasibility audit.
- `PHASE2_SESSION_PIPELINE.md`: reconstruction behavior and unverified source assumptions.
- `PHASE2C_VALIDATION.md`: provisional real-JSON mapping, quality checks, and validation workflow.
- `METRICS.md`: Phase 3A definitions and limitations.
- `SYNTHETIC_EXAMPLE.md`: expected results from invented sessions.
- `FRONTEND_PROTOTYPE.md`: instructor UI architecture and prototype limitations.
- `PHASE3B_RANKING.md`: question baselines, eligibility, ranking formulas, and integration contract.
- `PHASE3B_SYNTHETIC_COMPARISON.md`: illustrative comparison of ranking methods.
