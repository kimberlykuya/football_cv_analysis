# FlowTrace: Soccer Tactical Analyzer on AMD MI300X

Multi-agent soccer match analysis system powered by **AMD MI300X + DeepSeek-V4-Pro + LangGraph + ChromaDB**.

Processes raw match video through three AI agents: **Perceiver** (CV tracking), **Analyst** (tactical metrics), and **QA** (evidence-grounded Q&A), delivering real-time coach insights and cross-match pattern detection.

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **GPU** | AMD MI300X (ROCm 6.2) | Batch YOLOv26 tracking + embeddings |
| **LLM** | DeepSeek-V4-Pro via Featherless | Tactical narration + coach Q&A |
| **CV** | YOLOv26-X + ByteTrack | Player detection & tracking |
| **Memory** | ChromaDB + Sentence Transformers | Cross-match patterns + per-match RAG |
| **Orchestration** | LangGraph | Multi-agent state machine |
| **API** | FastAPI | Backend service |
| **Frontend** | Next.js 16 + React 19 + TypeScript | Dashboard UI |

---

## Benchmark Results

**AMD MI300X Throughput** (YOLOv26-X on 640×640 frames):

```
Batch  1:  42.3 frames/sec  (1x baseline)
Batch  4: 118.7 frames/sec  (2.8x faster)
Batch  8: 201.4 frames/sec  (4.8x faster)
Batch 16: 312.8 frames/sec  (7.4x faster) ← Production target
```

**Key Insight**: Batch 16 achieves 7.4× throughput advantage over batch 1, demonstrating AMD MI300X's effective memory bandwidth for batched inference. This enables real-time analysis of 30 fps match feeds with 10× headroom.

*Note: Benchmark results from AMD Developer Cloud MI300X instance. Local CPU benchmarks available but show significantly lower throughput.*

---

## Layout

- `backend/` - FastAPI service, CV pipeline, agents, memory layers, LangGraph orchestration
- `frontend/` - Next.js dashboard (video upload, tactical report, coach Q&A, team profile)
- `infra/` - Hardware setup scripts (ROCm, vLLM, SGLang)
- `backend/benchmark.py` - Throughput benchmark for MI300X
- `benchmark_results.txt` - Published benchmark data

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional) AMD MI300X with ROCm 6.2

### Backend Setup

1. **Install dependencies**:
   ```bash
   python -m pip install -r backend/requirements.txt
   ```

2. **Start the backend**:
   ```bash
   python -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8001
   ```
   Server runs on `http://localhost:8001`

### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Configure backend URL**:
   ```bash
   export BACKEND_URL=http://localhost:8001
   ```

3. **Start dev server**:
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000`

### Full Pipeline

If FastAPI is on `localhost:8001` and `FEATHERLESS_API_KEY` is configured:

1. Upload a match video (~30 seconds recommended)
2. Enter team ID (e.g., "manchester-city")
3. Click "Analyze"
4. View tactical report (formations, pressure zones, events)
5. Ask coach questions → Get answers + timestamp links to video evidence

---

## API Endpoints

### POST `/api/analyze`
Upload video and trigger full pipeline (perceiver → analyst → memory → RAG indexing).

**Request**:
```bash
curl -X POST http://localhost:8001/api/analyze \
  -F "video=@match.mp4" \
  -F "team_id=manchester-city" \
  -F "match_label=vs-arsenal-20240301"
```

**Response**:
```json
{
  "success": true,
  "match_id": "abc12345",
  "team_id": "manchester-city",
  "tactical_summary": "Team A demonstrated a 4-3-3 formation...",
  "cross_match_report": "Recurring pattern: high pressing in defensive third...",
  "metrics": {
    "team_a_avg_defensive_line": 42.3,
    "team_b_avg_defensive_line": 38.7,
    "team_a_compactness": 8.2,
    "team_b_compactness": 9.1
  },
  "pressure_zones": {
    "team_a": [[12.5, 8.3], [25.6, 14.2], [35.1, 12.9]],
    "team_b": [[15.2, 11.6], [22.3, 18.5], [38.7, 16.8]]
  },
  "events_detected": 8
}
```

---

### POST `/api/coach-qa`
Ask tactical questions about a match; get answers with cited timestamps.

**Request**:
```bash
curl -X POST http://localhost:8001/api/coach-qa \
  -H "Content-Type: application/json" \
  -d '{
    "match_id": "abc12345",
    "question": "Why did we concede? Where is the opponent vulnerable?"
  }'
```

**Response**:
```json
{
  "answer": "The opponent's vulnerability lies in their left flank during transitions. At [12.4s], [45.8s], and [73.2s], they showed gaps when pressing high without midfield cover. Recommendation: exploit these spaces with direct wing play and quick counter-attacks to their left side.",
  "cited_timestamps": [12.4, 45.8, 73.2, 89.1],
  "evidence_count": 12
}
```

---

### GET `/api/team/{team_id}/profile`
Retrieve cross-match tactical profile for a team.

**Request**:
```bash
curl http://localhost:8001/api/team/manchester-city/profile
```

**Response**:
```json
{
  "team_id": "manchester-city",
  "events": {
    "ids": ["man-city_match1_0", "man-city_match1_1", ...],
    "documents": [
      "Team A 3v1 overload in zone around 80m at 12.4s",
      "Team B high defensive line at 45.8s — avg position 62.3m",
      ...
    ],
    "metadatas": [
      {"team_id": "manchester-city", "clip_id": "match1", "event_type": "overload", "zone": "zone_80m", "timestamp": "12.4"},
      ...
    ]
  }
}
```

---

## DeepSeek-V4 via Featherless

The backend uses an OpenAI-compatible client and defaults to Featherless:

```bash
export DEEPSEEK_BASE_URL=https://api.featherless.ai/v1
export FEATHERLESS_API_KEY=<your-featherless-key>
export DEEPSEEK_MODEL=deepseek-ai/DeepSeek-V4-Pro
export ALLOW_MOCK_LLM=false
export YOLO_MODEL_PATH=yolo26x.pt
```

Use `deepseek-ai/DeepSeek-V4-Flash` instead when lower cost and lower latency matter more than maximum reasoning quality.

## Optional Local DeepSeek-V4 Serving (MI300X)

### Option 1: vLLM (Recommended)

```bash
bash infra/start_vllm.sh
```

Starts OpenAI-compatible endpoint on `http://localhost:8000/v1/chat/completions`.

**Critical flags for DeepSeek-V4 on MI300X**:
```bash
export VLLM_ROCM_USE_AITER=1           # AMD optimized kernels
export AITER_ENABLE_VSKIP=0            # Prevent crashes
export VLLM_USE_V1=1                   # V1 engine for throughput
--block-size 1                          # Required for MLA architecture
```

### Option 2: SGLang (Faster startup, lighter)

```bash
bash infra/start_sglang.sh
```

Docker-based SGLang endpoint with same OpenAI-compatible interface.

### Fallback (Local Testing)

If DeepSeek-V4 unavailable, `backend/agents/llm.py` falls back to mock responses only when `ALLOW_MOCK_LLM=true`. Set `ALLOW_MOCK_LLM=false` on AMD deployments to fail fast on LLM auth/network issues.

---

## AMD MI300X Setup

Verify GPU availability:

```bash
bash infra/amd_setup.sh
```

Should output:
```
GPU Product Name: AMD MI300X
CUDA is available: True
CUDA Device: AMD MI300X
```

---

## Deployment

### Hugging Face Space

1. Fork/clone repo to GitHub
2. Create Hugging Face Space → select "Docker" runtime
3. Point to GitHub repo
4. Set environment variables:
   - `DEEPSEEK_BASE_URL=https://api.featherless.ai/v1`
   - `FEATHERLESS_API_KEY=<your-key>`
   - `DEEPSEEK_MODEL=deepseek-ai/DeepSeek-V4-Pro`
   - `BACKEND_URL=http://localhost:8001`
5. Space auto-deploys on push

### AMD Developer Cloud / Runpod

1. Create instance with MI300X GPU
2. Clone repo: `git clone <your-repo>`
3. Install deps: `python -m pip install -r backend/requirements.txt && cd frontend && npm install`
4. Start backend: `python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8001`
5. Export `FEATHERLESS_API_KEY=<your-key>`, `DEEPSEEK_BASE_URL=https://api.featherless.ai/v1`, `ALLOW_MOCK_LLM=false`, and `YOLO_MODEL_PATH=yolo26x.pt`
6. Start frontend: `cd frontend && npm run build && npm start`
7. Access on instance IP:3000

See `.env.production` template for all required variables.

---

## Project Structure

```
flowtrace/
├── backend/
│   ├── api/main.py                  # FastAPI endpoints
│   ├── agents/
│   │   ├── llm.py                   # DeepSeek-V4 client (with fallback)
│   │   └── analyst.py               # Tactical analysis agent
│   ├── pipeline/
│   │   ├── perceiver.py             # YOLOv26 tracking pipeline
│   │   ├── team_classifier.py       # Jersey color clustering
│   │   ├── perspective.py           # Pitch coordinate transform
│   │   └── video_writer.py          # Output video with annotations
│   ├── memory/
│   │   ├── tactical_memory.py       # Cross-match ChromaDB store
│   │   └── match_rag.py             # Per-match RAG indexing
│   ├── graph/
│   │   └── flowtrace_graph.py       # LangGraph orchestration
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Main dashboard
│   │   ├── team/[teamId]/page.tsx   # Team profile
│   │   └── api/
│   │       ├── analyze/route.ts     # Backend proxy
│   │       └── coach-qa/route.ts    # Q&A proxy
│   ├── components/
│   │   ├── VideoPlayer.tsx
│   │   ├── CoachQA.tsx
│   │   ├── TacticalReport.tsx
│   │   └── TeamProfile.tsx
│   └── package.json
├── infra/
│   ├── amd_setup.sh                 # GPU verification
│   ├── start_vllm.sh                # vLLM startup
│   └── start_sglang.sh              # SGLang startup
│   ├── benchmark.py                  # Throughput benchmark
├── benchmark_results.txt            # Published benchmark data
└── README.md                        # This file
```

---

## Development Notes

- **Mock LLM fallback**: If DeepSeek-V4 is unavailable and `ALLOW_MOCK_LLM=true`, `llm.py` returns mock responses automatically.
- **LLM strict mode**: Set `ALLOW_MOCK_LLM=false` in deployment to fail fast on Featherless/API issues.
- **ChromaDB persistence**: Memory stores at `./flowtrace_db/team_memory` and `./flowtrace_db/match_rag`. Auto-created on startup.
- **Video uploads**: Stored in `./uploads/`. Clean up old videos to save disk space.
- **YOLO model path**: Override detector weights with `YOLO_MODEL_PATH`; default is `yolo26x.pt` resolved from repo root.
- **Field naming**: Backend uses snake_case (`match_id`, `team_id`); frontend JS uses camelCase (`matchId`, `teamId`). API routes handle conversion.

---

## Performance

| Metric | Value |
|--------|-------|
| **Video parsing** | 30 FPS on MI300X batch=16 |
| **YOLOv26 tracking** | 312.8 FPS on MI300X batch=16 (10× headroom above real-time) |
| **Embeddings** | 64 per batch, ~100ms on MI300X |
| **DeepSeek-V4 latency** | Provider-dependent via Featherless |
| **End-to-end 1-min video** | ~20 sec (perceive) + ~5 sec (analyze) + ~3 sec (memory) = ~28 sec total |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'langgraph'` | Run `python -m pip install -r backend/requirements.txt` |
| `ChromaDB permission error` | `mkdir -p ./flowtrace_db/team_memory ./flowtrace_db/match_rag` |
| `YOLOv26 model download hangs` | Pre-download: `python -c "from ultralytics import YOLO; YOLO('yolo26x.pt')"` |
| `DeepSeek-V4 auth/API error` | Check `FEATHERLESS_API_KEY`, `DEEPSEEK_BASE_URL=https://api.featherless.ai/v1`, and model access |
| `Frontend build fails (Node.js)` | Ensure Node ≥18: `node --version`; try `npm cache clean --force && npm install` |
| `GPU out of memory` | Reduce batch size or video resolution; see `backend/pipeline/perceiver.py` line 40 |

---

## License

MIT (for submission purposes)

---

## Contact & Attribution

Built for **AMD Developer Hackathon** on AMD MI300X hardware.

DeepSeek-V4 model: https://github.com/deepseek-ai/DeepSeek-V4  
YOLOv26: https://github.com/ultralytics/ultralytics  
ChromaDB: https://www.trychroma.com/  
LangGraph: https://langchain-ai.github.io/langgraph/

