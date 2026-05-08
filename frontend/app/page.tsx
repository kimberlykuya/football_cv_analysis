"use client"

import type { ChangeEvent } from "react"
import { useRef, useState } from "react"

import CoachQA from "@/components/CoachQA"
import EventFeed from "@/components/EventFeed"
import TacticalReport from "@/components/TacticalReport"
import VideoPlayer from "@/components/VideoPlayer"
import type { AnalyzeResponse } from "@/lib/types"
import { useAnalysisStream } from "@/lib/useAnalysisStream"

export default function HomePage() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [timestamps, setTimestamps] = useState<number[]>([])

  const stream = useAnalysisStream(videoFile)

  const jumpTo = (seconds: number) => {
    if (!videoRef.current) return
    videoRef.current.currentTime = seconds
    void videoRef.current.play()
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    stream.cancelStream()
    const file = event.target.files?.[0] ?? null
    setVideoFile(file)
    setAnalysis(null)
    setError(null)
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(file ? URL.createObjectURL(file) : null)
  }

  const handleAnalyze = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await stream.startStream()
      setAnalysis({
        success: true,
        match_id: String(data.match_id ?? ""),
        team_id: String(data.team_id ?? ""),
        match_label: String(data.match_label ?? videoFile?.name ?? ""),
        tactical_summary: String(data.tactical_summary ?? ""),
        cross_match_report: String(data.cross_match_report ?? ""),
        metrics: (data.metrics as Record<string, number>) ?? {},
        pressure_zones: (data.pressure_zones as Record<string, number[][]>) ?? {},
        formations: (data.formations as Record<string, number[][]>) ?? {},
        events_detected: Number(data.events_detected ?? 0),
        annotated_video_path: (data.annotated_video_path as string | null) ?? null,
      })
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      setError(err instanceof Error ? err.message : "Unknown analysis error")
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    stream.cancelStream()
    setLoading(false)
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">AMD MI300X Tactical Workbench</p>
          <h1>FlowTrace</h1>
          <p className="hero-copy">
            Upload match footage, generate a tactical report, then ask evidence-backed coaching questions.
          </p>
        </div>
        <div className="hero-stats" aria-label="Pipeline status">
          <span>YOLOv26 tracking</span>
          <strong>{analysis ? analysis.events_detected : stream.state.events.length}</strong>
          <span>events detected</span>
        </div>
      </section>

      <section className="control-panel">
        <label className="file-drop">
          <input type="file" accept="video/*" onChange={handleFileChange} />
          <span>{videoFile ? videoFile.name : "Choose match clip"}</span>
        </label>
        <button className="primary-action" type="button" onClick={() => void handleAnalyze()} disabled={loading}>
          {loading ? "Analyzing..." : "Run analysis"}
        </button>
        {loading ? (
          <button className="primary-action" type="button" onClick={handleCancel}>
            Stop
          </button>
        ) : null}
      </section>

      {error ? <p className="error-banner">{error}</p> : null}

      {loading && stream.state.stage ? (
        <section className="surface" style={{ marginBottom: "16px" }}>
          <div className="section-heading">
            <p className="eyebrow">{stream.state.stage}</p>
            <h2>{stream.state.progressPct}%</h2>
          </div>
          <div style={{ height: "8px", background: "rgba(255,255,255,0.08)", borderRadius: "4px" }}>
            <div
              style={{
                height: "8px",
                width: `${stream.state.progressPct}%`,
                background: "rgba(255,255,255,0.45)",
                borderRadius: "4px",
              }}
            />
          </div>
          {stream.state.summaryText ? (
            <div className="analysis-block" style={{ marginTop: "16px" }}>
              <h3>AI Tactical Analysis</h3>
              <p>{stream.state.summaryText}</p>
            </div>
          ) : null}
        </section>
      ) : null}

      <section className="workspace-grid">
        <div className="surface video-surface">
          <div className="section-heading">
            <p className="eyebrow">Source footage</p>
            <h2>Match view</h2>
          </div>
          <VideoPlayer
            src={previewUrl}
            videoRef={videoRef}
            timestamps={timestamps}
            onJumpTo={jumpTo}
            events={stream.state.events}
          />
        </div>

        <div className="surface qa-surface">
          {analysis ? (
            <CoachQA matchId={analysis.match_id} onJumpTo={jumpTo} onTimestampsChange={setTimestamps} />
          ) : (
            <div className="empty-state">
              <p className="eyebrow">Coach Q&A</p>
              <h2>Analyze a clip to unlock evidence search.</h2>
            </div>
          )}
        </div>
      </section>

      <section className="surface report-surface">
        <TacticalReport analysis={analysis} />
      </section>

      <section className="surface report-surface">
        <EventFeed events={stream.state.events} onEventClick={(event) => jumpTo(event.timestamp)} />
      </section>
    </main>
  )
}
