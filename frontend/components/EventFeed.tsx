"use client"

import { useMemo, useState } from "react"

interface TacticalEvent {
  timestamp: number
  type: string
  description: string
  confidence?: number
  model_source?: string
  team?: string
}

interface EventFeedProps {
  events: TacticalEvent[]
  onEventClick?: (event: TacticalEvent) => void
}

const pretty = (value: string) => value.replace(/_/g, " ")

export default function EventFeed({ events, onEventClick }: EventFeedProps) {
  const [filter, setFilter] = useState<"all" | "high" | "medium" | "low">("all")
  const filtered = useMemo(() => {
    if (filter === "all") return events
    return events.filter((event) => {
      const confidence = event.confidence ?? 60
      if (filter === "high") return confidence >= 70
      if (filter === "medium") return confidence >= 50 && confidence < 70
      return confidence < 50
    })
  }, [events, filter])

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
        <h3 style={{ margin: 0 }}>Tactical Events ({filtered.length})</h3>
        <div style={{ display: "flex", gap: "6px" }}>
          {(["all", "high", "medium", "low"] as const).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setFilter(item)}
              style={{
                padding: "4px 8px",
                border: "1px solid rgba(255,255,255,0.15)",
                borderRadius: "4px",
                background: filter === item ? "rgba(255,255,255,0.22)" : "transparent",
                color: "var(--ink)",
              }}
            >
              {item}
            </button>
          ))}
        </div>
      </div>
      <div style={{ display: "grid", gap: "8px", maxHeight: "380px", overflowY: "auto" }}>
        {filtered.map((event, index) => (
          <button
            key={`${event.timestamp}-${event.type}-${index}`}
            type="button"
            onClick={() => onEventClick?.(event)}
            style={{
              textAlign: "left",
              border: "1px solid rgba(255,255,255,0.1)",
              background: "rgba(255,255,255,0.03)",
              color: "var(--ink)",
              borderRadius: "6px",
              padding: "10px",
              cursor: onEventClick ? "pointer" : "default",
            }}
          >
            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              <strong>{Math.floor(event.timestamp)}s</strong>
              <span style={{ fontSize: "12px", opacity: 0.8 }}>{pretty(event.type)}</span>
            </div>
            <div style={{ fontSize: "13px", marginTop: "4px" }}>{event.description}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
