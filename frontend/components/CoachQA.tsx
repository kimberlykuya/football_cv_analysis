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
      if (onTimestampsChange && qaResponse.cited_timestamps) {
        onTimestampsChange(qaResponse.cited_timestamps)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error contacting backend")
    }
    setLoading(false)
  }

  return (
    <div className="coach-panel">
      <div className="section-heading">
        <p className="eyebrow">Coach Q&A</p>
        <h2>Ask the match</h2>
      </div>
      <div className="qa-input-row">
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              void askQuestion()
            }
          }}
          placeholder="Why did we concede?"
        />
        <button type="button" onClick={() => void askQuestion()} disabled={loading}>
          {loading ? "Analyzing..." : "Ask"}
        </button>
      </div>

      {error ? <p className="error-banner compact">{error}</p> : null}
      {response ? (
        <div className="qa-answer">
          <p>{response.answer}</p>
          {response.cited_timestamps.length > 0 && onJumpTo ? (
            <div className="timestamp-row">
              {response.cited_timestamps.map((timestamp) => (
                <button key={timestamp} type="button" onClick={() => onJumpTo(timestamp)}>
                  {timestamp.toFixed(1)}s
                </button>
              ))}
            </div>
          ) : null}
          {response.evidence_cards?.length ? (
            <div className="evidence-card-list">
              {response.evidence_cards.map((card, index) => (
                <button
                  key={`${card.type}-${card.timestamp}-${index}`}
                  type="button"
                  className="evidence-card"
                  onClick={() => onJumpTo?.(card.timestamp)}
                >
                  <span className="evidence-card-meta">
                    {card.timestamp.toFixed(1)}s · {card.type} · {Math.round(card.confidence)}%
                  </span>
                  <strong>{card.title}</strong>
                  <span>{card.excerpt}</span>
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
