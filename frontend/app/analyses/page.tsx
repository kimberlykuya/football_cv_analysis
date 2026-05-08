"use client"

import { useEffect, useState } from "react"

interface Analysis {
  match_id: string
  team_id: string
  match_label: string
  status: "processing" | "done" | "error"
  events_detected: number
  created_at: string
}

export default function AnalysesPage() {
  const [rows, setRows] = useState<Analysis[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch("/api/analyses")
        if (!res.ok) throw new Error("Failed to load analyses")
        const data = await res.json()
        setRows(data.analyses ?? [])
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error")
      }
    }
    void load()
  }, [])

  return (
    <main className="app-shell">
      <section className="surface">
        <h1 style={{ marginTop: 0 }}>Analysis History</h1>
        {error ? <p className="error-banner">{error}</p> : null}
        <div style={{ display: "grid", gap: "8px" }}>
          {rows.map((item) => (
            <div
              key={item.match_id}
              style={{
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "6px",
                padding: "10px",
                display: "grid",
                gridTemplateColumns: "1fr 1fr auto auto",
                gap: "10px",
                alignItems: "center",
              }}
            >
              <div>{item.team_id}</div>
              <div>{item.match_label || item.match_id}</div>
              <div>{item.events_detected} events</div>
              <div>{item.status}</div>
            </div>
          ))}
          {rows.length === 0 ? <p className="muted">No analyses yet.</p> : null}
        </div>
      </section>
    </main>
  )
}
