"use client"

import { useState } from "react"

import type { CoachQAResponse } from "@/lib/types"

type CoachQAProps = {
  matchId: string
  onJumpTo?: (seconds: number) => void
  onTimestampsChange?: (timestamps: number[]) => void
}

export default function CoachQA({ matchId, onJumpTo, onTimestampsChange }: CoachQAProps) {
  const [question, setQuestion] = useState("")
  const [response, setResponse] = useState<CoachQAResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const askQuestion = async () => {
    if (!question.trim()) return
    setLoading(true)
    setError(null)

    try {
      const result = await fetch("/api/coach-qa", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ match_id: matchId, question }),
      })

      const payload = (await result.json()) as CoachQAResponse | { detail?: string }
      if (!result.ok) {
        setError("detail" in payload && payload.detail ? payload.detail : "Coach Q&A request failed")
        setLoading(false)
        return
      }

      const qaResponse = payload as CoachQAResponse
      setResponse(qaResponse)
      // Propagate cited timestamps to parent so VideoPlayer can display them
      if (onTimestampsChange && qaResponse.cited_timestamps) {
        onTimestampsChange(qaResponse.cited_timestamps)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error contacting backend")
    }
    setLoading(false)
  }

  return (
    <div>
      <h3>Coach Q&A</h3>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              void askQuestion()
            }
          }}
          placeholder="Why did we concede?"
          style={{ flex: 1 }}
        />
        <button type="button" onClick={() => void askQuestion()} disabled={loading}>
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {error ? <p style={{ color: "red" }}>{error}</p> : null}
      {response ? (
        <div style={{ marginTop: 12, padding: 12, background: "#f5f5f5", borderRadius: 8 }}>
          <p style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{response.answer}</p>
          {response.cited_timestamps.length > 0 && onJumpTo ? (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12, alignItems: "center" }}>
              <span style={{ fontWeight: 600 }}>Jump to evidence:</span>
              {response.cited_timestamps.map((timestamp) => (
                <button
                  key={timestamp}
                  type="button"
                  onClick={() => onJumpTo(timestamp)}
                  style={{
                    padding: "4px 10px",
                    borderRadius: 16,
                    border: "1px solid #0070f3",
                    background: "#0070f3",
                    color: "#fff",
                    cursor: "pointer",
                    fontSize: 12
                  }}
                >
                  ▶ {timestamp.toFixed(1)}s
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

