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
    <main style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h1>FlowTrace</h1>
      <p>Upload a match clip, inspect the tactical report, and ask questions over evidence.</p>

      <section style={{ display: "grid", gap: 12, maxWidth: 720 }}>
        <input type="file" accept="video/*" onChange={handleFileChange} />
        <input value={teamId} onChange={(event) => setTeamId(event.target.value)} placeholder="team id" />
        <input
          value={matchLabel}
          onChange={(event) => setMatchLabel(event.target.value)}
          placeholder="match label"
        />
        <button type="button" onClick={() => void handleAnalyze()} disabled={loading}>
          {loading ? "Analyzing..." : "Run analysis"}
        </button>
      </section>

      {error ? <p>{error}</p> : null}

      <section style={{ marginTop: 24 }}>
        <VideoPlayer src={previewUrl} videoRef={videoRef} timestamps={timestamps} onJumpTo={jumpTo} />
      </section>

      <section style={{ marginTop: 24 }}>
        <TacticalReport analysis={analysis} />
      </section>

      {analysis ? (
        <section style={{ marginTop: 24 }}>
          <CoachQA matchId={analysis.match_id} onJumpTo={jumpTo} onTimestampsChange={setTimestamps} />
        </section>
      ) : null}
    </main>
  )
}
