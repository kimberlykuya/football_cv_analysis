"use client"

import { useEffect, useState } from "react"

interface GPUStatus {
  gpu_util_pct: number
  vram_used_mb: number
  vram_total_mb: number
  temperature_c: number | null
  device_name: string
  cuda_available: boolean
  timestamp: number
}

export default function GPUMonitor() {
  const [status, setStatus] = useState<GPUStatus | null>(null)
  const [history, setHistory] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Fetch current status and history on mount
    const fetchStatus = async () => {
      try {
        const [statusRes, historyRes] = await Promise.all([
          fetch("/api/gpu/status"),
          fetch("/api/gpu/history?limit=60"),
        ])

        if (statusRes.ok) {
          setStatus(await statusRes.json())
        }
        if (historyRes.ok) {
          const data = await historyRes.json()
          setHistory(data.history || [])
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch GPU status")
      }
    }

    fetchStatus()

    // Poll every 2 seconds
    const interval = setInterval(fetchStatus, 2000)
    return () => clearInterval(interval)
  }, [])

  if (!status) {
    return (
      <div
        style={{
          padding: "12px",
          border: "1px solid rgba(255,255,255,0.2)",
          borderRadius: "6px",
          background: "#1a1a1a",
          fontSize: "12px",
          color: "var(--muted)",
        }}
      >
        Loading GPU status...
      </div>
    )
  }

  const vramPercent = (status.vram_used_mb / status.vram_total_mb) * 100

  return (
    <div
      style={{
        padding: "12px",
        border: "1px solid rgba(255,255,255,0.2)",
        borderRadius: "6px",
        background: "#1a1a1a",
      }}
    >
      <div style={{ fontSize: "11px", color: "var(--muted)", marginBottom: "8px", textTransform: "uppercase" }}>
        {status.device_name}
      </div>

      {/* GPU Utilization Circular Gauge */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "12px" }}>
        <svg width="48" height="48" style={{ flexShrink: 0 }}>
          <circle cx="24" cy="24" r="20" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="2" />
          <circle
            cx="24"
            cy="24"
            r="20"
            fill="none"
            stroke="#ffffff"
            strokeWidth="2"
            strokeDasharray={`${2 * Math.PI * 20}`}
            strokeDashoffset={`${2 * Math.PI * 20 * (1 - status.gpu_util_pct / 100)}`}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.3s ease" }}
          />
          <text x="24" y="28" textAnchor="middle" fontSize="14" fill="var(--ink)" fontWeight="700">
            {Math.round(status.gpu_util_pct)}%
          </text>
        </svg>

        <div style={{ flex: 1 }}>
          <div style={{ fontSize: "12px", color: "var(--ink)", marginBottom: "4px" }}>GPU Utilization</div>
          <div style={{ fontSize: "10px", color: "var(--muted)" }}>
            {Math.round(status.vram_used_mb)} / {Math.round(status.vram_total_mb)} MB VRAM
          </div>
          <div
            style={{
              height: "4px",
              background: "rgba(255,255,255,0.1)",
              borderRadius: "2px",
              marginTop: "4px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                background: "rgba(255,255,255,0.4)",
                width: `${vramPercent}%`,
                transition: "width 0.2s ease",
              }}
            />
          </div>
        </div>
      </div>

      {/* Temperature */}
      {status.temperature_c !== null && (
        <div style={{ fontSize: "11px", color: "var(--muted)", marginBottom: "6px" }}>
          Temp: <span style={{ color: "var(--ink)" }}>{Math.round(status.temperature_c)}°C</span>
        </div>
      )}

      {/* Sparkline History */}
      {history.length > 1 && (
        <div style={{ marginTop: "8px" }}>
          <svg
            width="100%"
            height="30"
            style={{
              display: "block",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "4px",
              background: "rgba(255,255,255,0.02)",
            }}
            preserveAspectRatio="none"
          >
            <polyline
              points={history
                .map((h, i) => {
                  const x = (i / (history.length - 1)) * 100
                  const y = 30 - (h.gpu_util_pct / 100) * 28
                  return `${x},${y}`
                })
                .join(" ")}
              fill="none"
              stroke="rgba(255,255,255,0.4)"
              strokeWidth="1"
            />
          </svg>
          <div style={{ fontSize: "10px", color: "var(--muted)", marginTop: "4px" }}>
            Last 5 min utilization trend
          </div>
        </div>
      )}

      {error && <div style={{ fontSize: "10px", color: "#ffcccc", marginTop: "8px" }}>{error}</div>}
    </div>
  )
}
