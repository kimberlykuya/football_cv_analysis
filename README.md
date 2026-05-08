# FlowTrace: Soccer Tactical Analyzer on AMD MI300X

Multi-agent soccer match analysis system powered by **AMD MI300X + DeepSeek-V4-Pro + LangGraph + ChromaDB**.

Processes raw match video through three AI agents: **Perceiver** (CV tracking), **Analyst** (tactical metrics), and **QA** (evidence-grounded Q&A), delivering streaming coach insights, analysis history, GPU telemetry, and cross-match pattern detection.

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **GPU** | AMD MI300X (ROCm 6.2) | Batch YOLOv26 tracking + embeddings |
| **LLM** | DeepSeek-V4-Pro via Featherless | Tactical narration + coach Q&A |
| **Validator** | Optional Qwen via Featherless | Event validation + confidence scoring |
| **Local VLM** | Qwen2.5-VL-7B-Instruct | Event-frame visual evidence for RAG |
| **CV** | YOLOv26-X + ByteTrack | Player detection & tracking |
| **Memory** | ChromaDB + Sentence Transformers | Cross-match patterns + per-match RAG |
| **Orchestration** | LangGraph | Multi-agent state machine |
| **API** | FastAPI | Backend service |
| **Frontend** | Next.js 16 + React 19 + TypeScript + Node 20+ | Dashboard UI |

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
- Node.js 20.9+
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

3. **Optional Qwen validation**:
   ```bash
   export QWEN_VALIDATION_ENABLED=true
   export QWEN_BASE_URL=https://api.featherless.ai/v1
   export QWEN_MODEL=Qwen/Qwen3-235B-A22B
   export QWEN_API_KEY=$FEATHERLESS_API_KEY
   ```
   Leave `QWEN_VALIDATION_ENABLED=false` for faster, heuristic confidence scoring.

4. **Optional local VLM evidence**:
   ```bash
   export VLM_ENABLED=true
   export VLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct
   export VLM_DEVICE=cuda
   export VLM_DTYPE=bfloat16
   ```
   Leave `VLM_ENABLED=false` to keep the current text-only RAG path.

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
2. Click "Analyze"
3. View tactical report (formations, pressure zones, events)
4. Ask coach questions → Get answers + timestamp links to video evidence

---

## API Endpoints

### POST `/api/analyze`
Upload video and trigger full pipeline (perceiver → analyst → memory → RAG indexing).

**Request**:
```bash
curl -X POST http://localhost:8001/api/analyze \
  -F "video=@match.mp4"
```

`team_id` and `match_label` are optional. The demo UI omits them and the backend defaults to `team_id=demo-team` and the uploaded filename as the match label.

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

### POST `/api/analyze/stream`
Upload video and stream progress/events over Server-Sent Events. The frontend uses this endpoint by default.

Every SSE message uses the same envelope:

```json
{
  "type": "progress",
  "ts": 1778248000.0,
  "analysis_id": "abc12345",
  "payload": {
    "stage": "perceive",
    "progress_pct": 100
  }
}
```

Event types currently emitted:

- `progress` - pipeline stage progress
- `tactical_event` - event marker ready for feed/timeline
- `complete` - final `AnalyzeResponse` payload
- `error` - terminal failure payload

---

### GET `/api/analyses`
List analysis registry rows for the history page.

```bash
curl http://localhost:8001/api/analyses
```

### GET `/api/gpu/status`
Return current GPU telemetry for the dashboard.

```bash
curl http://localhost:8001/api/gpu/status
```

### GET `/api/gpu/history`
Return recent GPU samples from the in-process ring buffer.

```bash
curl http://localhost:8001/api/gpu/history?limit=60
```

---

### POST `/api/coach-qa`
Ask tactical questions about a match; get answers with cited timestamps and evidence cards.

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
  "evidence_count": 12,
  "evidence_cards": [
    {
      "timestamp": 45.8,
      "type": "visual",
      "title": "Visual evidence",
      "excerpt": "Visual evidence shows the defensive line stretched with central pressure.",
      "confidence": 82,
      "frame_id": "1374",
      "source_image_path": "./uploads/vlm_frames/abc12345/frame_1374.jpg"
    }
  ]
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

Optional Qwen validation uses the same OpenAI-compatible provider by default:

```bash
export QWEN_VALIDATION_ENABLED=true
export QWEN_BASE_URL=https://api.featherless.ai/v1
export QWEN_API_KEY=$FEATHERLESS_API_KEY
export QWEN_MODEL=Qwen/Qwen3-235B-A22B
```

If Qwen validation is disabled, the backend still adds deterministic heuristic confidence scores. If it is enabled and the Qwen call fails, validation logs a warning and falls back to heuristics so the analysis pipeline continues.

## Optional Local VLM Evidence

Set `VLM_ENABLED=true` to enrich RAG with local event-frame visual evidence using Qwen2.5-VL-7B-Instruct:

```bash
export VLM_ENABLED=true
export ALLOW_VLM_FALLBACK=true
export VLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct
export VLM_DEVICE=cuda
export VLM_DTYPE=bfloat16
export VLM_MAX_EVENT_FRAMES=40
export VLM_IMAGE_DIR=./uploads/vlm_frames
```

The VLM does not replace YOLO/ByteTrack. It runs after tactical event detection, samples only event frames, writes JPEG artifacts under `VLM_IMAGE_DIR`, and indexes structured visual evidence into MatchRAG. Set `ALLOW_VLM_FALLBACK=false` only when you want analysis to fail if local VLM inference fails.

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

For a fresh AMD Cloud MI300X instance, use the consolidated setup script from the repo root:

```bash
sed -i 's/\r$//' infra/*.sh
bash infra/setup_amd_env.sh
```

The script creates `.venv`, installs backend requirements including local VLM dependencies, installs ROCm PyTorch, verifies GPU runtime, installs Node 20+ when needed, installs frontend dependencies, and checks for local assets.

By default setup verifies VLM imports but does not download/load Qwen2.5-VL. To force a full local VLM model load during setup:

```bash
VLM_PRELOAD=true VLM_ENABLED=true bash infra/setup_amd_env.sh
```

Runtime configuration lives in `.env.amd.example`:

```bash
set -a && source .env.amd.example && set +a
```

Fill in `FEATHERLESS_API_KEY` with a rotated key and replace `<gpu-public-ip>` in `NEXT_ALLOWED_DEV_ORIGINS`.

`yolo26x.pt` and real demo videos are intentionally not stored in normal Git. Copy them separately:

```powershell
scp C:\Users\USER\Documents\football_analysis\yolo26x.pt root@<gpu-ip>:/root/football_cv_analysis/yolo26x.pt
scp C:\path\to\real-football-clip.mp4 root@<gpu-ip>:/root/football_cv_analysis/test_video.mp4
```

If you only need a smoke-test video:

```bash
python infra/create_test_video.py
```

Verify GPU availability:

```bash
bash infra/amd_setup.sh
```

Should output:
```
GPU Product Name: AMD MI300X
cuda_available=True
device_0=AMD Instinct MI300X...
```

If `cuda_available=False`, PyTorch is CPU-only and the MI300X is not being used by YOLO or embeddings.

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
3. Copy `yolo26x.pt` and a real demo clip separately if they are not in Git
4. Run setup: `bash infra/setup_amd_env.sh`
5. Load env: `set -a && source .env.amd.example && set +a`
6. Run checks: `bash infra/amd_setup.sh && python backend/test_backend.py`
7. Create or copy `test_video.mp4`; then run `python backend/test_pipeline.py`
8. Start backend: `bash infra/start_backend.sh`
9. Start frontend dev: `PUBLIC_IP=<gpu-ip> bash infra/start_frontend_dev.sh`
10. Or start frontend prod: `bash infra/start_frontend_prod.sh`
11. In a second shell, verify services: `BACKEND_URL=http://127.0.0.1:8001 FRONTEND_URL=http://127.0.0.1:3000 bash infra/smoke_check.sh`
12. Access on instance IP:3000

For VLM verification, load env with `VLM_ENABLED=true` before running `infra/smoke_check.sh`; the smoke check will instantiate the local VLM model.

See `.env.production` template for all required variables.

---

## Project Structure

```
flowtrace/
├── backend/
│   ├── api/main.py                  # FastAPI endpoints
│   ├── api/registry.py              # SQLite analysis registry
│   ├── api/gpu_monitor.py           # GPU telemetry endpoints
│   ├── agents/
│   │   ├── llm.py                   # DeepSeek-V4 client (with fallback)
│   │   ├── analyst.py               # Tactical analysis agent
│   │   ├── visual_evidence.py        # Local VLM event-frame evidence
│   │   └── validator.py             # Optional Qwen validation
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
│   │   ├── analyses/page.tsx        # Analysis history
│   │   ├── team/[teamId]/page.tsx   # Team profile
│   │   └── api/
│   │       ├── analyze/route.ts     # Backend proxy
│   │       ├── analyze/stream/route.ts # SSE backend proxy
│   │       ├── analyses/route.ts    # Registry proxy
│   │       ├── gpu/status/route.ts  # GPU status proxy
│   │       └── coach-qa/route.ts    # Q&A proxy
│   ├── components/
│   │   ├── VideoPlayer.tsx
│   │   ├── EventTimeline.tsx
│   │   ├── EventFeed.tsx
│   │   ├── GPUMonitor.tsx
│   │   ├── NavBar.tsx
│   │   ├── CoachQA.tsx
│   │   ├── TacticalReport.tsx
│   │   └── TeamProfile.tsx
│   └── package.json
├── infra/
│   ├── amd_setup.sh                 # GPU verification
│   ├── setup_amd_env.sh             # Fresh MI300X setup
│   ├── check_gpu_runtime.py          # PyTorch ROCm validation
│   ├── create_test_video.py          # Synthetic smoke-test clip
│   ├── start_backend.sh              # Background FastAPI launcher
│   ├── start_frontend_dev.sh         # Next.js dev launcher
│   ├── start_frontend_prod.sh        # Next.js production launcher
│   ├── smoke_check.sh                # Fresh instance service checks
│   ├── start_vllm.sh                 # vLLM startup
│   └── start_sglang.sh               # SGLang startup
├── backend/benchmark.py              # Throughput benchmark
├── benchmark_results.txt            # Published benchmark data
└── README.md                        # This file
```

---

## Development Notes

- **Mock LLM fallback**: If DeepSeek-V4 is unavailable and `ALLOW_MOCK_LLM=true`, `llm.py` returns mock responses automatically.
- **LLM strict mode**: Set `ALLOW_MOCK_LLM=false` in deployment to fail fast on Featherless/API issues.
- **Qwen validation**: Set `QWEN_VALIDATION_ENABLED=true` only when `QWEN_*` credentials/model access are confirmed. Default `false` keeps analysis fast and uses heuristic confidence scoring.
- **Local VLM evidence**: Set `VLM_ENABLED=true` only on GPU instances with enough VRAM for Qwen2.5-VL-7B-Instruct. Default `false` preserves the text-only RAG path.
- **GPU strict mode**: Set `ALLOW_CPU_FALLBACK=false` in deployment to fail fast when ROCm PyTorch is not active.
- **ChromaDB persistence**: Memory stores at `./flowtrace_db/team_memory` and `./flowtrace_db/match_rag`. Auto-created on startup.
- **Analysis registry**: Upload/status history is stored at `./flowtrace_db/analyses_registry.db`.
- **Video uploads**: Stored in `./uploads/`. Clean up old videos to save disk space.
- **YOLO model path**: Override detector weights with `YOLO_MODEL_PATH`; default is `yolo26x.pt` resolved from repo root.
- **YOLO tuning**: Use `YOLO_BATCH_SIZE`, `YOLO_IMGSZ`, and `YOLO_HALF` to tune MI300X throughput.
- **Embedding tuning**: Use `EMBED_BATCH_SIZE` to raise SentenceTransformer batch size on GPU.
- **Next dev origins**: Use `NEXT_ALLOWED_DEV_ORIGINS=<gpu-ip>,http://<gpu-ip>:3000` to debug through the public IP without HMR origin warnings.
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
| `Qwen validation fails` | Set `QWEN_VALIDATION_ENABLED=false` or verify `QWEN_API_KEY`, `QWEN_BASE_URL`, and `QWEN_MODEL` |
| `VLM model load fails` | Keep `VLM_ENABLED=false`, verify `transformers`, `accelerate`, `qwen-vl-utils`, ROCm PyTorch, and available VRAM |
| `VLM evidence missing` | Confirm tactical events were detected and `VLM_IMAGE_DIR` is writable |
| `Frontend build fails (Node.js)` | Ensure Node ≥20.9: `node --version`; try `npm cache clean --force && npm install` |
| `History page is empty` | Confirm backend is using the same working directory and `./flowtrace_db/analyses_registry.db` is writable |
| `GPU dashboard shows CPU` | Confirm `python infra/check_gpu_runtime.py` reports `cuda_available=True`; on ROCm, PyTorch still exposes GPUs through `torch.cuda` |
| `Next dev HMR origin warning` | Run `PUBLIC_IP=<gpu-ip> bash infra/start_frontend_dev.sh` or set `NEXT_ALLOWED_DEV_ORIGINS` |
| `torch.cuda.is_available() is false` | Reinstall ROCm PyTorch in `.venv`; rerun `python infra/check_gpu_runtime.py` |
| `infra/*.sh set: pipefail invalid option` | Run `sed -i 's/\r$//' infra/*.sh` |
| `GPU out of memory` | Reduce `YOLO_BATCH_SIZE` or `YOLO_IMGSZ` |

## Utilization Checks

Watch GPU activity during analysis:

```bash
watch -n 1 rocm-smi
```

Run YOLO batch throughput checks:

```bash
python backend/benchmark.py --model yolo26x.pt --batch-sizes 16,32,64,128
```

Confirm required packages:

```bash
python -m pip show uvicorn langgraph lap ultralytics torch
```

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

