# BrightSmile AI Assistant — Dental X-ray AI Clinical Decision-Support POC

> **Clinical disclaimer:** This is a research / clinical decision-support proof
> of concept. It is **not** an autonomous diagnostic system, does not produce
> a diagnosis, and every AI finding requires dentist review before any
> clinical use.

> **Model status:** the frozen **DENTEX YOLO11m** dental-disease-detection
> model and its evaluation artifacts are loaded from
> `backend/model_artifacts/` (sourced from `dental_ai_poc_claude_package`).
> Real bounding-box findings are returned. See
> [Model artifacts](#7-model-artifacts) and
> [Evaluation metrics](#9-evaluation-metrics) for exact, unmodified numbers.

![Results and review screen](docs/screenshot-review.png)

## Quickstart for non-technical users (fork & run locally)

No coding knowledge needed — just copy-paste each command into a terminal,
one at a time, and press Enter. "Terminal" = Terminal app on Mac, or
PowerShell/Git Bash on Windows.

### Step 0 — one-time tools install

You need four free programs installed first:

- **Git** — https://git-scm.com/downloads
- **Python** (3.11 or newer) — https://www.python.org/downloads/
- **Node.js** (20 or newer) — https://nodejs.org/
- **Postgres with the `pgvector` extension** (needed for chat/RAG citations —
  skip this if you only want the upload/review flow, see Step 2b) — easiest
  via Docker: `pgvector/pgvector:pg16` image (see Step 2b), or Homebrew:
  `brew install postgresql@16 pgvector`

After installing, check they worked by running:

```bash
git --version
python3 --version
node --version
```

Expected output (exact numbers may differ, that's fine):
```
git version 2.43.0
Python 3.11.9
v20.11.0
```
If any command says "command not found," reinstall that program and restart your terminal.

### Step 1 — get the code

```bash
git clone https://github.com/<your-fork>/BrightSmile_AI_Assistant
cd BrightSmile_AI_Assistant
```
Expected output:
```
Cloning into 'BrightSmile_AI_Assistant'...
remote: ...
Receiving objects: 100% ...
```
The clone includes the real AI model file (`backend/model_artifacts/best.pt`,
~40MB) — nothing extra to download for the model itself, so this may take
a little longer than a typical small repo clone.

### Step 2a — start Postgres (needed for auth + cases + chat)

Easiest with Docker:
```bash
docker run -d --name brightsmile-db -p 5433:5432 \
  -e POSTGRES_USER=brightsmile -e POSTGRES_PASSWORD=brightsmile -e POSTGRES_DB=brightsmile \
  pgvector/pgvector:pg16
```
This image ships the `pgvector` extension already installed, which the
chat/RAG feature needs (Section 5a). If you use a different Postgres
(e.g. Homebrew), make sure it's version 13+ and `pgvector` is installed
before continuing — the app's schema init will fail otherwise once RAG is
enabled.

### Step 2b — configure secrets

```bash
cd backend
cp .env.example .env
```
Open `.env` in a text editor and fill in:
- `BRIGHTSMILE_DATABASE_URL` — defaults to the Docker command above
  (`postgresql://brightsmile:brightsmile@localhost:5433/brightsmile`)
- `BRIGHTSMILE_LLM_PROVIDER` — one of `openai`, `anthropic`, `gemini`, `groq`
- the matching `BRIGHTSMILE_<PROVIDER>_API_KEY` — get a key from that
  provider's dashboard; this powers the chat feature only, not the X-ray
  detection model itself (that runs fully locally, no key needed)

**Never commit `.env`** — it holds real API keys. It's already gitignored.

### Step 3 — start the backend (the "brain")

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
`pip install` downloads the AI libraries (~1-2GB, including PyTorch and the
sentence-transformers embedding/reranker models used for chat citations) —
this can take several minutes depending on your internet connection; this
is normal, not a hang.

Expected output (last lines):
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```
Leave this terminal window open and running. To check it's really working,
open a **second** terminal and run:
```bash
curl http://localhost:8000/api/v1/health
```
Expected output:
```
{"status":"ok","model_loaded":true,"model_version":"dentex_dental_ai_poc-YOLO11m-conf0.20-imgsz1024","model_artifacts_status":"loaded_from_frozen_package"}
```
`"status":"ok"` = backend is alive. `"model_loaded":true` = the real frozen
YOLO11m model loaded successfully and will return real findings.

### Step 3a — load the RAG corpus (optional, only if `BRIGHTSMILE_RAG_ENABLED=true`)

The chat feature can ground its answers in real ADA guideline PDFs
(`backend/rag_corpus/`) instead of the LLM's general knowledge. One-time
setup, with the backend's venv active:
```bash
PYTHONPATH=. python scripts/ingest_ada_docs.py --corpus-dir rag_corpus
```
Expected output:
```
  ada_aaomr_imaging_patient_selection: ingested 170 chunks
  caries_chairside_guide_primary_teeth: ingested 31 chunks
  caries_risk_assessment_form_instructions: ingested 32 chunks
```
Skip this step (and leave `BRIGHTSMILE_RAG_ENABLED=false`) if you only want
the upload/detection/review flow without chat citations.

### Step 4 — start the frontend (the website you see)

Open a **new, third** terminal window (leave the backend one running) and run:
```bash
cd BrightSmile_AI_Assistant/frontend
npm install
npm run dev
```
Expected output (last lines):
```
  VITE v...  ready in ... ms

  ➜  Local:   http://localhost:5173/
```
Open that `http://localhost:5173/` link in your browser. You should see the
"BrightSmile AI Assistant" upload screen.

### Step 5 — try it

1. Log in — the first run auto-seeds a default password (`123456`) for any
   dentist/patient/admin id you use. Log in as a dentist (e.g. `Dr. Test A`),
   or use "Forgot password? Reset to default" if unsure.
2. Drag a panoramic dental X-ray image (JPEG/PNG) onto the upload page — the
   model was trained on panoramic X-rays specifically, so other image types
   (or a random photo) likely won't produce findings, which is expected, not
   a bug.
3. Click **Analyze**.
4. You'll land on the results screen with bounding boxes drawn over any
   detected Caries / Deep Caries / Periapical Lesion / Impacted Tooth
   findings, each labeled "Possible &lt;condition&gt; detected in this
   region — dentist review required."
5. Click a finding's **Accept**, **Reject**, or **Correct** button.
6. Open the chat panel — if RAG is enabled (Step 3a), it auto-sends a
   findings summary grounded in the ADA guideline corpus with citations. Ask
   follow-up questions, or "zoom into the &lt;condition&gt; on the left/right"
   to get a cropped, boxed close-up of one specific finding.

### Step 6 — run the automated tests (optional, proves nothing is broken)

Backend tests (in the terminal from Step 3, same `.venv` active):
```bash
python -m pytest -q
```
Expected output (exact time varies):
```
80 passed in 3.3s
```

Frontend tests (in the terminal from Step 4):
```bash
cd frontend
npm run test
```
Expected output:
```
 Test Files  4 passed (4)
      Tests  14 passed (14)
```

### Stopping everything

In each terminal window, press `Ctrl+C` to stop the backend/frontend.

### Common problems

| Symptom | Fix |
|---|---|
| `command not found: python3` / `node` / `git` | Re-do Step 0, restart terminal |
| `port 8000 already in use` | Another program is using that port — close it, or run `uvicorn app.main:app --reload --port 8001` and use that port instead |
| Frontend loads but "Analyze" gives an error | Make sure the backend terminal (Step 3) is still running and shows no errors |
| `pip install` fails | Make sure you ran `source .venv/bin/activate` (or Windows equivalent) first |
| Backend fails at startup with a Postgres connection error | Make sure the Step 2a container is running: `docker ps` should list it; check `BRIGHTSMILE_DATABASE_URL` in `.env` matches its port |
| Chat feature errors with "LLM_PROVIDER is not set" | Fill in `BRIGHTSMILE_LLM_PROVIDER` + the matching API key in `.env`, then restart the backend |
| Chat replies but never shows citations | `BRIGHTSMILE_RAG_ENABLED` is `false`, or Step 3a's ingest script hasn't been run yet |
| CORS error in browser console when frontend is on an unusual port | The backend allows any `http://localhost:<port>` origin by regex already — if you're not on localhost, add your origin to `cors_origins` in `app/core/config.py` |

## 1. Architecture

```
React (login / upload / gallery / results-review / chat UI)
        │  HTTP (multipart upload, JSON, session cookie)
        ▼
FastAPI API  (auth, health, predictions, cases, review, admin)
        │
        ├──► Auth (session cookie, bcrypt password hash) ─► Postgres (doctors/patients/admins/sessions)
        │
        ▼
Prediction service   (orchestrates validate → predict → post-process → persist)
        │
        ▼
Model predictor      (ModelPredictor interface)
   ├── YoloPredictor   — wraps frozen ultralytics YOLO, used when best.pt exists
   └── StubPredictor    — returns zero findings, used when weights are absent
        │
        ▼
YOLO inference → post-processing (threshold filter, class filter, finding_id assignment)
        │
        ▼
Structured Finding[] (condition, confidence, bbox in original-image coordinates)
        │
        ▼
Case storage (Postgres for metadata + local filesystem for image bytes,
              app/storage/interface.py seam — local-only backend also available)
        │
        ├──► Chat service ─► LLM (OpenAI/Anthropic/Gemini/Groq, pluggable via
        │                     app/services/llm/factory.py) grounded by:
        │                     Retriever (hybrid BM25 + dense pgvector search,
        │                     cross-encoder reranking) over ADA guideline PDFs
        │                     ─► Citations + server-side annotated/cropped
        │                        X-ray image (real YOLO bboxes, not LLM-drawn)
        ▼
Frontend visualization (bounding-box overlay, accept/reject/correct, chat w/ citations)
```

Concerns are kept in separate layers: storage behind `app/storage/interface.py`
(local filesystem or Postgres), the predictor behind `app/services/predictor.py`,
the LLM provider behind `app/services/llm/factory.py`, and the RAG index behind
`app/storage/rag_interface.py` — each swappable without touching callers.

## 2. Setup

Requirements: Python 3.11+, Node 20+, Postgres 13+ with `pgvector` (for auth/
cases/chat — see Quickstart Step 2a for the easiest Docker route), Docker
(optional, for `docker compose up`).

```bash
git clone <this repo>
cd BrightSmile_AI_Assistant
```

## 3. Running the backend

```bash
# start Postgres with pgvector (see Quickstart Step 2a), then:
cd backend
cp .env.example .env   # fill in DATABASE_URL + an LLM provider API key
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

To enable chat citations, also run the RAG ingestion once (Quickstart Step 3a):
```bash
PYTHONPATH=. python scripts/ingest_ada_docs.py --corpus-dir rag_corpus
```

## 4. Running the frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173 (expects the backend at `http://localhost:8000/api/v1`,
overridable via `VITE_API_BASE_URL`).

## 5. Running with Docker

```bash
docker compose up --build
```

Backend on `:8000`, frontend on `:3000`, Postgres (with `pgvector`) on `:5433`.
Case data persists to `./storage/cases` on the host via a bind mount; database
data persists to the `brightsmile_db` named volume. Set your LLM provider API
key as an environment variable before running (e.g.
`BRIGHTSMILE_OPENAI_API_KEY=sk-... docker compose up --build`) — it's passed
through into the backend container.

RAG ingestion still needs to be run once inside the backend container:
```bash
docker compose exec backend python scripts/ingest_ada_docs.py --corpus-dir rag_corpus
```

(Docker Desktop/daemon was not available in the environment this POC was
built in, so the Dockerfiles/compose file are written to spec but not
build-verified here — verify with `docker compose up --build` before
relying on them.)

## 5a. RAG-grounded chat

The chat feature (per-case, in `CaseDetailPage`) can ground its answers in
real ADA clinical guideline PDFs instead of the LLM's unaided knowledge:

- **Corpus**: `backend/rag_corpus/*.pdf` (+ `.json` metadata sidecars for
  `doc_type`/`url`/`condition_tags`) — ships with 3 real ADA documents
  (caries management, caries risk assessment, 2026 ADA/AAOMR imaging
  patient-selection guidance).
- **Ingestion**: `scripts/ingest_ada_docs.py` extracts text (`pypdf`),
  chunks it structure-aware (`app/services/rag/chunking.py`), embeds it
  (`BAAI/bge-base-en-v1.5` via `sentence-transformers`, local — no API
  cost), and stores it in Postgres+`pgvector`.
- **Retrieval**: hybrid BM25 (sparse) + dense cosine search, fused via
  Reciprocal Rank Fusion (`app/services/rag/hybrid.py`), then narrowed by a
  cross-encoder reranker (`app/services/rag/reranker.py`) — see
  `app/services/rag/retriever.py`.
- **Citations**: every chat reply that used a source returns numbered
  `citations` (source name + URL) alongside the reply text.
- **Image annotation/zoom**: if the reply names a detected condition, the
  backend renders the *real* YOLO bounding box(es) onto the X-ray
  server-side (`app/services/image_annotation.py`) and returns it inline —
  the LLM never touches pixels. Asking to "zoom into the caries on the
  left" (or "the second one", "the lower tooth") crops tight to that one
  finding using positional/ordinal disambiguation.
- **Expansion**: `scripts/ingest_pubmed.py` adds open-access PubMed articles
  scoped by MeSH term, reusing the same pipeline, tagged with lower trust
  weight than ADA guidelines.
- **Toggle**: set `BRIGHTSMILE_RAG_ENABLED=false` to disable chat citations
  entirely (chat still works, ungrounded, same as before RAG existed).

## 6. API endpoints

| Method | Path                                | Purpose                                   |
|--------|-------------------------------------|--------------------------------------------|
| GET    | `/api/v1/health`                    | Liveness + model-load status               |
| POST   | `/api/v1/auth/doctor/login`         | Doctor session login                       |
| POST   | `/api/v1/auth/patient/login`        | Patient session login                      |
| POST   | `/api/v1/auth/admin/login`          | Admin session login                        |
| GET    | `/api/v1/auth/doctors`              | Public list of known doctor names          |
| POST   | `/api/v1/auth/*/reset-password`     | Reset a login's password to the default    |
| POST   | `/api/v1/predictions`               | Upload an X-ray, run inference             |
| GET    | `/api/v1/cases/{case_id}`           | Fetch a case's findings + review history   |
| POST   | `/api/v1/cases/{case_id}/review`    | Accept / reject / correct a finding        |
| GET    | `/api/v1/cases/{case_id}/chat`      | Fetch chat history for a case              |
| POST   | `/api/v1/cases/{case_id}/chat`      | Ask the LLM a question (RAG-grounded if enabled) |
| DELETE | `/api/v1/cases/{case_id}/chat`      | Clear chat history for a case              |
| GET    | `/api/v1/admin/*`                   | Admin case/doctor/patient browsing          |

`POST /predictions` accepts `multipart/form-data` with a `file` field (JPEG
or PNG, ≤10MB). Response shape:

```json
{
  "case_id": "44ccc96313ec44c8a66ba2ef9e720c2e",
  "model_version": "dentex_dental_ai_poc-YOLO11m-conf0.20-imgsz1024",
  "image_dimensions": {"width": 1200, "height": 900},
  "findings": [
    {
      "finding_id": "finding_001",
      "condition": "Caries",
      "confidence": 0.87,
      "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 400},
      "review_required": true,
      "status": "pending",
      "clinical_message": "Possible Caries detected in this region — dentist review required."
    }
  ],
  "disclaimer": "..."
}
```

`POST /cases/{case_id}/review` body:

```json
{"finding_id": "finding_001", "action": "accepted"}
{"finding_id": "finding_001", "action": "rejected"}
{"finding_id": "finding_001", "action": "corrected", "condition": "Deep_Caries", "bbox": {"x1":10,"y1":20,"x2":50,"y2":80}}
```

Corrections never overwrite the original AI prediction — the original
finding and the dentist's correction are stored side by side for future
dataset curation, never used to auto-retrain.

`POST /cases/{case_id}/chat` body/response:

```json
// request
{"message": "How should I manage the deep caries finding?"}

// response
{
  "reply": "**Insights:**\n- Restorative treatment with resin-modified GIC or composite is recommended for carious lesions [1]...\n\n**Suggestions for doctor:**\n- Confirm pulp involvement before restoring...",
  "citations": [
    {"chunk_id": "e730c0e6...", "source": "caries_chairside_guide_primary_teeth", "url": "https://www.ada.org/..."}
  ],
  "annotated_image": "data:image/jpeg;base64,..."
}
```
`citations` is empty and `annotated_image` is `null` if RAG is disabled or
no source/condition was relevant to the reply.

## 7. Model artifacts

Source package: `dental_ai_poc_claude_package` (DENTEX dental AI POC).
The following frozen artifacts are copied into `backend/model_artifacts/`
and are the sole source of truth for the app's model behavior — nothing
below was invented or tuned by the application code:

| Artifact | Used for |
|---|---|
| `best.pt` | The frozen YOLO11m weights. Never retrained or modified. |
| `frozen_model_config.json` | Class list + confidence threshold |
| `final_experiment_manifest.json` | Version/provenance metadata |
| `final_test_metrics.json` | Held-out test set performance (Section 9) |
| `validation_metrics.json` | Validation set performance (Section 9) |
| `threshold_selection.json` | Proof the 0.20 threshold was chosen on validation data only, never the test set |
| `dataset_summary.json` | Dataset composition (Section 9) |
| `split_manifest.json` | Exact train/val/test image split (seed 42) |
| `inference_benchmark.json` | Measured inference latency (Section 9) |

Concretely, `backend/app/core/constants.py` mirrors these values 1:1:

- `MODEL_WEIGHTS_PATH` → `model_artifacts/best.pt`
- `SUPPORTED_CONDITIONS` → `frozen_model_config.json["classes"]`, in id order
- `CONFIDENCE_THRESHOLD = 0.20` → `frozen_model_config.json["confidence_threshold"]`
- `MODEL_IMAGE_SIZE = 1024`, `MODEL_IOU_THRESHOLD = 0.7` → `final_test_metrics.json`
- `MODEL_VERSION = "dentex_dental_ai_poc-YOLO11m-conf0.20-imgsz1024"` → `final_experiment_manifest.json`

`backend/app/services/predictor.py`'s `YoloPredictor` loads `best.pt` once
at startup via `ultralytics.YOLO(...)` and is used automatically because the
file is present. If `best.pt` were ever removed, the app falls back to
`StubPredictor` (zero findings, never invented ones) rather than breaking —
`GET /api/v1/health`'s `model_loaded` / `model_artifacts_status` fields tell
you which mode is active at any time.

## 8. Supported conditions

Exactly four classes are ever exposed — the model's real trained classes,
in their real class-id order, unmodified:

| id | Class name (API value) | Display label |
|---|---|---|
| 0 | `Caries` | Caries |
| 1 | `Deep_Caries` | Deep Caries |
| 2 | `Periapical_Lesion` | Periapical Lesion |
| 3 | `Impacted_Tooth` | Impacted Tooth |

Per the source package's README, this model does **not** detect (and this
app never claims it detects): missing teeth, fillings, crowns, implants, or
periodontal bone loss — those require additional labeled training data.

Enforced in three places: `predictor.py` (drops any detection outside this
set even if the model emits it), `prediction_service.py` post-processing,
and the frontend's `SUPPORTED_CONDITIONS` (correction dropdown can't select
anything else).

## 9. Evaluation metrics

All numbers below are copied verbatim from the frozen artifacts in
`backend/model_artifacts/` — nothing here is estimated. These are **model
evaluation metrics**, produced once during training/evaluation on a fixed
held-out split; they are a different thing from **runtime application
metrics** (API/inference latency logged per-request via
`app/core/logging.py`), which vary by hardware and are not pre-computed.

**Dataset** (`dataset_summary.json`): DENTEX, 678 total labeled images,
split 70/15/15 (train 474 / val 102 / test 102, seed 42), 3,529 annotations.
Class distribution: Caries 2,189, Impacted_Tooth 604, Deep_Caries 578,
Periapical_Lesion 158 — classes are imbalanced, which the precision/recall
tradeoff below partly reflects.

**Confidence threshold selection** (`threshold_selection.json`): 0.20 was
chosen by maximizing F1 on the **validation** split only; the test split
was never used for threshold selection (candidates from 0.05–0.90 were
swept, full table in the JSON file).

**Validation performance** at confidence 0.20, iou 0.7, imgsz 1024, 102
images (`validation_metrics.json`):

| Metric | Value |
|---|---|
| Precision | 0.5846 |
| Recall | 0.6511 |
| F1 | 0.6160 |
| mAP@50 | 0.5486 |
| mAP@50:95 | 0.3934 |

**Held-out test performance** at the same settings, 102 images
(`final_test_metrics.json`) — this is the number that matters for judging
real-world performance, since it was never used to pick the threshold:

| Metric | Value |
|---|---|
| Precision | 0.4658 |
| Recall | 0.5413 |
| F1 | 0.5007 |
| mAP@50 | 0.4430 |
| mAP@50:95 | 0.2958 |

Per-class breakdown and false-positive/false-negative counts are **not**
present in the supplied `final_test_metrics.json` (it reports only the
aggregate precision/recall/F1/mAP shown above) — do not treat this README
as claiming per-class numbers that don't exist in the artifact. Specificity
is intentionally not reported: the evaluation methodology (object-detection
mAP/precision/recall) does not define a negative-class unit that would make
specificity meaningful.

**Inference benchmark** (`inference_benchmark.json`), measured on a Tesla
T4 GPU, 50 images, imgsz 1024, confidence 0.20:

| Metric | Value |
|---|---|
| Average latency | 142.31 ms/image |
| Throughput | 7.03 images/sec |

This was measured on a T4 GPU in the original training environment — CPU-only
or different-GPU inference in your local setup will differ; the app logs
its own live inference latency per request rather than relying on this
number at runtime.

## 10. Privacy

- Cases are keyed by a randomly generated opaque `case_id` (`uuid4().hex`),
  never derived from a filename, patient name, or MRN.
- Auth uses server-side session cookies (httpOnly) + bcrypt-hashed
  passwords (`app/core/security.py`) — no plaintext passwords stored or
  logged.
- Logs never include raw image bytes or patient identifiers — only
  `case_id`, timings, and finding counts/conditions (see
  `app/core/logging.py` docstring).
- Uploaded image bytes are stored only on the local filesystem under
  `storage/cases/{case_id}/`; case/review/chat metadata lives in Postgres
  when `BRIGHTSMILE_STORAGE_BACKEND=postgres` (default), or the same
  filesystem tree when set to `local`.
- The RAG corpus (`backend/rag_corpus/`) is public ADA guideline text, not
  patient data — but chat messages and case findings are sent to whichever
  third-party LLM provider you configure (`BRIGHTSMILE_LLM_PROVIDER`); review
  that provider's data-handling terms before sending real patient cases
  through it.

## 11. Limitations

- Test-set F1 is 0.50 (Section 9) — expect real misses (false negatives)
  and false positives; this is why every finding requires dentist review
  and nothing is ever labeled a diagnosis.
- Trained/evaluated on 678 DENTEX images total (102-image test set) — a
  small evaluation set; performance on your own X-ray population may differ.
- Only detects the 4 listed classes (Section 8) — no coverage of missing
  teeth, fillings, crowns, implants, or periodontal bone loss.
- No encryption at rest; single-node deployment only (no clustering/HA).
- Dockerfiles/compose are written to spec but not build-verified (no Docker
  daemon available in the build environment).
- No retraining pipeline exists, intentionally — dentist review data is
  captured for future *manual, controlled* dataset curation only.
- RAG corpus is small (3 ADA PDFs, ~230 chunks) and hand-curated — citation
  coverage is good for caries/imaging questions, thinner for periapical
  lesions and periodontal topics until more sources are ingested
  (`scripts/ingest_pubmed.py` is the path to expand it).
- Chat's condition-name matching for citations/image annotation is regex-based
  (`app/services/image_annotation.py`) — it works off the LLM's reply text
  naming a known condition, not a structured tool call, so unusual phrasing
  could occasionally miss a match.

## 12. Clinical disclaimer

BrightSmile AI Assistant provides AI-assisted, unverified findings for
research and clinical decision-support purposes only. It does not diagnose
disease, does not replace a licensed dentist's judgment, and every finding
must be reviewed (accepted, rejected, or corrected) by a dentist before any
clinical decision is made based on it.

## 13. Future improvements

- Expand the DENTEX training set beyond 678 images to improve test-set F1.
- Persist runtime metrics (API/inference/post-processing latency) to a
  time-series store instead of structured logs only.
- Expand the RAG corpus with `scripts/ingest_pubmed.py` (open-access PubMed,
  MeSH-scoped) once the ADA corpus alone shows retrieval gaps
  (`app/services/rag/eval.py` has the Recall@k/MRR harness to measure this).
- Build the manual dataset-curation workflow that consumes review audit
  data (never automatic retraining).
- Persist per-turn source citations on `ChatMessage` itself (currently only
  returned on the live response, not reloaded from history) so
  `scripts/eval_groundedness.py`'s per-turn judge check can be finished.
