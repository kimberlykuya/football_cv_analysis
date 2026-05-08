"use client"

import { useCallback, useRef, useState } from "react"

export interface TacticalEvent {
  timestamp: number
  type: string
  description: string
  zone?: string
  confidence?: number
  model_source?: string
  team?: string
}

type StreamEvent = {
  type: "progress" | "tactical_event" | "summary_chunk" | "complete" | "error"
  ts: number
  analysis_id: string
  payload: Record<string, unknown>
}

export interface AnalysisStreamState {
  stage: string | null
  progressPct: number
  events: TacticalEvent[]
  summaryText: string
  isComplete: boolean
  error: string | null
}

export function useAnalysisStream(videoFile: File | null) {
  const abortRef = useRef<AbortController | null>(null)
  const [state, setState] = useState<AnalysisStreamState>({
    stage: null,
    progressPct: 0,
    events: [],
    summaryText: "",
    isComplete: false,
    error: null,
  })

  const startStream = useCallback(
    async (teamId = "demo-team", matchLabel = "") => {
      if (!videoFile) {
        throw new Error("Select a match video first.")
      }

      setState({
        stage: null,
        progressPct: 0,
        events: [],
        summaryText: "",
        isComplete: false,
        error: null,
      })
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      const formData = new FormData()
      formData.append("video", videoFile)
      formData.append("team_id", teamId)
      formData.append("match_label", matchLabel)

      const response = await fetch("/api/analyze/stream", {
        method: "POST",
        body: formData,
        signal: controller.signal,
      })
      if (!response.ok || !response.body) {
        throw new Error(`Analysis failed: ${response.statusText}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      let completePayload: Record<string, unknown> | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split("\n\n")
        buffer = chunks.pop() ?? ""

        for (const chunk of chunks) {
          const dataLine = chunk
            .split("\n")
            .find((line) => line.startsWith("data: "))
          if (!dataLine) continue
          const parsed = JSON.parse(dataLine.slice(6)) as StreamEvent

          if (parsed.type === "progress") {
            setState((prev) => ({
              ...prev,
              stage: String(parsed.payload.stage ?? ""),
              progressPct: Number(parsed.payload.progress_pct ?? 0),
            }))
          } else if (parsed.type === "tactical_event") {
            const payload = parsed.payload
            const event: TacticalEvent = {
              timestamp: Number(payload.timestamp ?? 0),
              type: String(payload.type ?? "unknown"),
              description: String(payload.description ?? ""),
              zone: payload.zone ? String(payload.zone) : undefined,
              confidence: payload.confidence !== undefined ? Number(payload.confidence) : undefined,
              model_source: payload.model_source ? String(payload.model_source) : undefined,
              team: payload.team ? String(payload.team) : undefined,
            }
            setState((prev) => ({
              ...prev,
              events: [...prev.events, event],
            }))
          } else if (parsed.type === "summary_chunk") {
            const chunk = String(parsed.payload.chunk ?? "")
            setState((prev) => ({
              ...prev,
              summaryText: prev.summaryText + chunk,
            }))
          } else if (parsed.type === "error") {
            const message = String(parsed.payload.message ?? "Unknown error")
            setState((prev) => ({ ...prev, error: message, isComplete: true }))
            throw new Error(message)
          } else if (parsed.type === "complete") {
            completePayload = parsed.payload
            setState((prev) => ({ ...prev, isComplete: true }))
          }
        }
      }

      if (!completePayload) {
        throw new Error("Stream ended without completion payload.")
      }

      abortRef.current = null
      return completePayload
    },
    [videoFile]
  )

  const cancelStream = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setState((prev) => ({ ...prev, isComplete: true }))
  }, [])

  return { state, startStream, cancelStream }
}
