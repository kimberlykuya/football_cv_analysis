# FlowTrace Demo Walkthrough

## Overview

This walkthrough demonstrates the full FlowTrace system: uploading a soccer match video, analyzing it for tactical insights, and asking questions with evidence-backed answers.

---

## Demo Flow

### Step 1: Home Page — Upload Match

**UI**: Main dashboard with upload form

```
┌─────────────────────────────────────────┐
│ FlowTrace: Soccer Tactical Analyzer     │
│ Powered by AMD MI300X + DeepSeek-V4     │
├─────────────────────────────────────────┤
│                                         │
│  1. Upload Match Video                  │
│     ┌─────────────────────────────┐     │
│     │ Select video file... (.mp4) │     │
│     └─────────────────────────────┘     │
│                                         │
│  2. Team Information                    │
│     Team ID: [manchester-city     ]     │
│     Match Label: [vs-arsenal-2024 ]     │
│                                         │
│  3. [ANALYZE] ← Click to start          │
│                                         │
│  Status: Ready                          │
│                                         │
└─────────────────────────────────────────┘
```

**Action**: Select a ~30-second match video (e.g., "highlights.mp4"), enter team ID, click "ANALYZE".

---

### Step 2: Processing

**Backend Flow**:
```
Video Upload
    ↓
[1] Perceiver Agent (YOLOv26 tracking)
    - Detects 22 players (2 teams + 1 referee)
    - Tracks positions for 900 frames (30 sec @ 30fps)
    - Extracts jersey colors (KMeans clustering)
    - Converts pixel coords → pitch coordinates (meters)
    ↓ Output: frame_data (player positions + team labels + timestamps)
    
[2] Analyst Agent
    - Computes formations (e.g., 4-3-3 vs 4-2-3-1)
    - Identifies pressure zones (6 zones across pitch)
    - Detects tactical events (overloads, high lines, pressing)
    - Calls DeepSeek-V4 to narrate findings
    ↓ Output: tactical_summary, metrics, pressure_zones, events
    
[3] Store Memory
    - Saves tactical events to ChromaDB (cross-match pattern store)
    - Generates cross-match report (recurring patterns vs past matches)
    ↓ Output: cross_match_report
    
[4] Index for Q&A (Match RAG)
    - Indexes all frame descriptions + tactical events + summary
    - Enables semantic search by coach questions
    ↓ Output: RAG collection ready for queries

Time: ~20-40 seconds for 30-second video
```

**Frontend Shows**: "Analyzing... (processing perceiver + analyst + memory..."

---

### Step 3: Tactical Report — Analysis Results

**UI**: Tactical analysis display

```
┌──────────────────────────────────────────────────────────┐
│ Match Analysis: manchester-city vs arsenal               │
│ Match ID: abc12345 | Duration: 30 sec (900 frames)      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ 📊 TACTICAL SUMMARY                                     │
│ ────────────────────────────────────────────────────    │
│ Team A (manchester-city) demonstrated a 4-3-3 formation │
│ with aggressive pressing in the attacking third. Average│
│ defensive line height: 42.3m (52% of pitch). Strong     │
│ territorial control in middle zones (65% possession).   │
│                                                          │
│ Team B (arsenal) countered with a 4-2-3-1 setup,       │
│ focusing on defensive compactness. Avg defensive line:  │
│ 38.7m (37% of pitch). Key vulnerability: gaps between   │
│ defensive and midfield lines during rapid transitions.  │
│                                                          │
│ 🎯 KEY FINDINGS                                         │
│ ────────────────────────────────────────────────────    │
│ • Formation: Team A 4-3-3, Team B 4-2-3-1              │
│ • Pressure Zones: Team A dominant (65% middle third)   │
│ • Critical Events:                                      │
│   ✓ [12.4s] Team A 3v1 overload (zone 80m)            │
│   ✓ [45.8s] Team B high defensive line (62.3m)        │
│   ✓ [73.2s] Pressing trigger after turnover           │
│                                                          │
│ 📈 METRICS                                              │
│ ────────────────────────────────────────────────────    │
│ Team A:                                                 │
│   Avg Defensive Line: 42.3m | Compactness: 8.2m       │
│ Team B:                                                 │
│   Avg Defensive Line: 38.7m | Compactness: 9.1m       │
│                                                          │
│ 🔄 PRESSURE ZONES (Heatmap)                            │
│ ────────────────────────────────────────────────────    │
│ Team A:  [12.5% | 25.6% | 35.1%]  (defensive→attacking) │
│ Team B:  [15.2% | 22.3% | 38.7%]  (defensive→attacking) │
│                                                          │
│ 🔗 CROSS-MATCH PATTERNS (From Previous Matches)        │
│ ────────────────────────────────────────────────────    │
│ • High pressing in attacking third: 3/5 matches        │
│ • Defensive line >40m: Recurring vs weaker opponents   │
│ • Vulnerability to counter-attacks: Consistent issue   │
│                                                          │
│ [← Back] [⬇ Download Report]                           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Key Features**:
- ✅ Formations auto-detected
- ✅ Metrics computed from player positions
- ✅ Tactical summary AI-generated (DeepSeek-V4)
- ✅ Cross-match patterns from ChromaDB (if team has history)
- ✅ All data exportable as JSON

---

### Step 4: Coach Q&A — Ask Questions with Evidence

**UI**: Q&A Panel

```
┌──────────────────────────────────────────────────────────┐
│ Ask the Coach AI                                         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ Question:                                                │
│ [Why did we concede in that transition?              ] ← │
│ [ASK]                                                    │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ 🎙️  ANSWER (DeepSeek-V4 + Evidence-Based)             │
│                                                          │
│ The vulnerability occurred during rapid defensive      │
│ transitions when your defensive line was caught high   │
│ (62.3m) without sufficient midfield cover. At [45.8s], │
│ the opponent executed a quick counter-attack, exploiting│
│ the gap between your back 4 and midfield 3. The left   │
│ flank (your right) showed repeated exposure throughout │
│ the match.                                              │
│                                                          │
│ Recommendation: Compact the shape (reduce defensive    │
│ line height to 35-38m) during high-press situations or │
│ deploy an additional defensive midfielder.             │
│                                                          │
│ 📌 JUMP TO EVIDENCE (Click any timestamp)              │
│ ┌─────────────────────────────────────────────────┐    │
│ │ [▶ 12.4s] [▶ 45.8s] [▶ 73.2s] [▶ 89.1s]        │    │
│ └─────────────────────────────────────────────────┘    │
│                                                          │
│ ✅ Video scrubbed to 45.8s                             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Key Features**:
- ✅ Natural language questions
- ✅ AI answers grounded in video evidence
- ✅ Timestamp pills: Click to jump to exact moment in video
- ✅ Multiple questions supported
- ✅ Evidence count shown (12 relevant frames retrieved from RAG)

**Example Questions**:
1. "Why did we concede?" → Answer + timestamps [12.4s, 45.8s, 73.2s]
2. "Where are they vulnerable?" → Answer + timestamps [18.3s, 52.1s]
3. "What formation are they using?" → Answer + timestamps [2.1s, 30.5s]
4. "How should we adjust?" → Answer + timestamps [5.2s, 67.8s]

---

### Step 5: Video Player with Timestamp Scrubbing

**UI**: Video player with timestamp controls

```
┌──────────────────────────────────────────────────────────┐
│ Match Video (30 sec)                                     │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  [Video Stream - 640×480]                               │
│  (Shows live soccer match with bounding boxes & labels)│
│                                                          │
│  🔊 ──●─────────────────────────── 45.8 / 30.0 sec     │
│       [▶︎ Pause] [×1 speed]                             │
│                                                          │
│  🎯 Quick Jump:                                          │
│  [▶ 12.4s] [▶ 45.8s] [▶ 73.2s] [▶ 89.1s]              │
│       ↑ Overload      ↑ High line   (from Q&A evidence)│
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Interaction**: 
- Scrub timeline manually or
- Click timestamp pill from Q&A → video jumps to exact moment

---

### Step 6: Team Profile (Cross-Match Memory)

**Navigation**: Click "Team" tab

```
┌──────────────────────────────────────────────────────────┐
│ Team Profile: manchester-city                           │
│ Analyzed: 5 matches | Patterns: 23 events              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ 📋 RECURRING TACTICAL PATTERNS                          │
│                                                          │
│ 1. High Pressing in Attacking Third                     │
│    Frequency: 4/5 matches | Avg Duration: 35 sec       │
│    Pattern: Triggers after losing possession            │
│    First Observed: Match 1 (arsenal) [12.4s]           │
│                                                          │
│ 2. Defensive Line > 40m                                 │
│    Frequency: 3/5 matches | Against: Weaker teams      │
│    Pattern: Aggressive, pushing for goals               │
│    Recent: Match 5 (burnley) [avg 42.3m]               │
│                                                          │
│ 3. Left Flank Vulnerability                             │
│    Frequency: 5/5 matches ⚠️  Consistent issue         │
│    Pattern: Gaps when pushing forward                   │
│    Recommendation: Shore up left defense or add LWB    │
│                                                          │
│ 4. Counter-Attack Danger Zone                           │
│    Frequency: 3/5 matches | Occurs at: 35–45 min      │
│    Pattern: Fatigue → pressing intensity drops          │
│    Recent: Match 5 conceded at 38 min                   │
│                                                          │
│ 🔄 Historical Events Archive                            │
│ ─── Query by event type (formation, pressure, etc.) ───│
│                                                          │
│ [Export Team Profile] [Compare vs Opponent]             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Key Features**:
- ✅ Auto-aggregates patterns across 5+ matches
- ✅ Shows frequency, trend, and timestamps
- ✅ Identifies consistent weaknesses
- ✅ Searchable event archive
- ✅ Data persists across sessions (ChromaDB)

---

## Real-World Use Cases

### 1. Pre-Match Preparation
- Upload opponent's recent 5-minute highlight clip
- Review formations, pressure tactics, known vulnerabilities
- Cross-match patterns show recurring patterns
- Coaching staff adjusts game plan based on evidence

### 2. Half-Time Analysis
- Upload first-half highlight (15 min)
- Identify what's working and what isn't
- Q&A: "Why are they beating us on the wing?"
- Make tactical adjustments for second half

### 3. Post-Match Review
- Upload full match (90 min)
- Analyze own performance + opponent patterns
- Build cross-match profile for next opponents
- Evidence-backed breakdown for player meetings

### 4. Scouting New Players
- Upload multiple matches of target player
- Analyze positioning, decision-making, movement patterns
- Cross-match reports show consistency/adaptability
- Data-driven recruitment recommendations

---

## Technical Stack (Visible to User)

| Layer | Technology | Visible As |
|-------|-----------|----------|
| **GPU Inference** | AMD MI300X + YOLOv26 | Fast video processing (20–40 sec/match) |
| **LLM** | DeepSeek-V4 via Featherless | Natural language tactical answers |
| **Memory** | ChromaDB | Recurring patterns across matches |
| **Timing** | Frame timestamps | Evidence citation (jump to 45.8s) |
| **Frontend** | Next.js + React | Responsive web UI (real-time updates) |

---

## Performance (Expected)

| Metric | Value |
|--------|-------|
| **Video Upload** | Instant (streaming) |
| **Perceiver (YOLOv26 tracking)** | 20 sec for 30-min video |
| **Analyst (metrics + LLM)** | 5 sec (DeepSeek-V4 provider-dependent) |
| **Memory Storage** | <1 sec |
| **Q&A Response** | 2–3 sec (DeepSeek-V4 reasoning) |
| **End-to-End (30-min video)** | ~28 sec total |

---

## Limitations & Future Work

### Current Limitations
- ✅ Single-match analysis (no multi-game aggregation yet)
- ✅ Homography perspective transform is linear (not full pitch warping)
- ✅ No ball tracking (future: add ball-tracking LLM for possession analysis)
- ✅ Mock LLM fallback if DeepSeek-V4 unavailable (no real reasoning)

### Future Enhancements
1. **Ball Tracking** — Add SAM (Segment Anything) for ball detection
2. **Heatmaps** — Visual player density + pass map overlays
3. **Predictive Analytics** — Next-play prediction using transformer
4. **Team Comparison** — Head-to-head tactical matchups
5. **Real-time Streaming** — Live match analysis (not just video files)

---

## Accessing the Demo

### Live (If Deployed)
Visit: `http://<deployment-url>:3000`

Example: 
- **Hugging Face Space**: https://huggingface.co/spaces/user/flowtrace
- **AMD Developer Cloud**: http://instance-ip:3000

### Local
```bash
# Configure DeepSeek-V4 through Featherless
export DEEPSEEK_BASE_URL=https://api.featherless.ai/v1
export FEATHERLESS_API_KEY=<your-key>

# Terminal 2: Start Backend
cd backend
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# Terminal 3: Start Frontend
cd frontend
npm install && npm run dev

# Then open: http://localhost:3000
```

### Test Video
Download a ~30-second soccer highlight clip (any format: mp4, mov, avi).

Recommended sources:
- YouTube highlights (download via yt-dlp)
- ESPN match clips
- Any soccer match recording (should work!)

---

## Questions?

For debugging, check:
- Backend logs: `uvicorn` output on port 8000
- Frontend console: `npm run dev` terminal + browser dev tools
- File uploads: `./uploads/` directory
- Memory store: `./flowtrace_db/` directory (ChromaDB)

Contact: Refer to GitHub repo for issues.
