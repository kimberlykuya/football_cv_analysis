"use client"

import { useRef, useState } from "react"
import type { ChangeEvent } from "react"

import CoachQA from "@/components/CoachQA"
import TacticalReport from "@/components/TacticalReport"
import VideoPlayer from "@/components/VideoPlayer"
import type { AnalyzeResponse } from "@/lib/types"

export default function HomePage() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [teamId, setTeamId] = useState("team-a")
  const [matchLabel, setMatchLabel] = useState("")
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [timestamps, setTimestamps] = useState<number[]>([])

  const jumpTo = (seconds: number) => {
    if (!videoRef.current) return
    videoRef.current.currentTime = seconds
    void videoRef.current.play()
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    setVideoFile(file)
    setAnalysis(null)
    setError(null)

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
    }

    setPreviewUrl(file ? URL.createObjectURL(file) : null)
  }

  const handleAnalyze = async () => {
    if (!videoFile) {
      setError("Select a match video first.")
      return
    }

    setLoading(true)
    setError(null)
    const formData = new FormData()
    formData.append("video", videoFile)
    formData.append("team_id", teamId)
    formData.append("match_label", matchLabel)

    const response = await fetch("/api/analyze", {
      method: "POST",
      body: formData,
    })

    const payload = (await response.json()) as AnalyzeResponse | { detail?: string }
    if (!response.ok) {
      setError("detail" in payload && payload.detail ? payload.detail : "Analysis failed")
      setLoading(false)
      return
    }

    setAnalysis(payload as AnalyzeResponse)
    setLoading(false)
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">AMD MI300X Tactical Workbench</p>
          <h1>FlowTrace</h1>
          <p className="hero-copy">
            Upload match footage, generate a tactical report, then ask evidence-backed
            coaching questions over the exact video moments.
          </p>
        </div>
        <div className="hero-stats" aria-label="Pipeline status">
          <span>YOLOv26 tracking</span>
          <strong>{analysis ? analysis.events_detected : 0}</strong>
          <span>events detected</span>
        </div>
      </section>

      <section className="control-panel">
        <label className="file-drop">
          <input type="file" accept="video/*" onChange={handleFileChange} />
          <span>{videoFile ? videoFile.name : "Choose match clip"}</span>
        </label>
        <input value={teamId} onChange={(event) => setTeamId(event.target.value)} placeholder="team id" />
        <input
          value={matchLabel}
          onChange={(event) => setMatchLabel(event.target.value)}
          placeholder="match label"
        />
        <button className="primary-action" type="button" onClick={() => void handleAnalyze()} disabled={loading}>
          {loading ? "Analyzing..." : "Run analysis"}
        </button>
      </section>

      {error ? <p className="error-banner">{error}</p> : null}

      <section className="workspace-grid">
        <div className="surface video-surface">
          <div className="section-heading">
            <p className="eyebrow">Source footage</p>
            <h2>Match view</h2>
          </div>
          <VideoPlayer src={previewUrl} videoRef={videoRef} timestamps={timestamps} onJumpTo={jumpTo} />
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
    </main>
  )
}
