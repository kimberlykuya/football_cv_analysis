"use client"

import { useEffect, useRef } from "react"

interface TimelineEvent {
  timestamp: number
  type: string
  description: string
}

interface EventTimelineProps {
  events: TimelineEvent[]
  videoDuration: number
  currentTime: number
  onSeek: (time: number) => void
  height?: number
}

export default function EventTimeline({ events, videoDuration, currentTime, onSeek, height = 60 }: EventTimelineProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Set canvas resolution for crisp rendering
    const dpr = window.devicePixelRatio || 1
    canvas.width = canvas.offsetWidth * dpr
    canvas.height = height * dpr
    ctx.scale(dpr, dpr)

    // Draw background
    ctx.fillStyle = "#1a1a1a"
    ctx.fillRect(0, 0, canvas.offsetWidth, height)

    // Draw grid
    ctx.strokeStyle = "rgba(255,255,255,0.1)"
    ctx.lineWidth = 1
    const gridCount = 4
    for (let i = 0; i <= gridCount; i++) {
      const x = (i / gridCount) * canvas.offsetWidth
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, height)
      ctx.stroke()
    }

    // Draw time labels
    ctx.fillStyle = "rgba(255,255,255,0.4)"
    ctx.font = "10px sans-serif"
    ctx.textAlign = "center"
    for (let i = 0; i <= gridCount; i++) {
      const time = (i / gridCount) * videoDuration
      const x = (i / gridCount) * canvas.offsetWidth
      const label = formatTime(time)
      ctx.fillText(label, x, height - 3)
    }

    // Draw events
    if (events.length > 0) {
      const eventsByType: { [key: string]: TimelineEvent[] } = {}
      events.forEach((e) => {
        if (!eventsByType[e.type]) {
          eventsByType[e.type] = []
        }
        eventsByType[e.type].push(e)
      })

      const types = Object.keys(eventsByType)
      types.slice(0, 3).forEach((type, typeIdx) => {
        const typeEvents = eventsByType[type]
        const color = getEventColor(typeIdx)

        typeEvents.forEach((event) => {
          const x = (event.timestamp / videoDuration) * canvas.offsetWidth
          const y = 10 + typeIdx * 8

          // Draw event marker
          ctx.fillStyle = color
          ctx.beginPath()
          ctx.arc(x, y, 2, 0, 2 * Math.PI)
          ctx.fill()

          // Draw vertical line
          ctx.strokeStyle = color
          ctx.globalAlpha = 0.3
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.moveTo(x, y + 3)
          ctx.lineTo(x, height - 12)
          ctx.stroke()
          ctx.globalAlpha = 1
        })
      })
    }

    // Draw playhead
    const playheadX = (currentTime / videoDuration) * canvas.offsetWidth
    ctx.strokeStyle = "#ffffff"
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(playheadX, 0)
    ctx.lineTo(playheadX, height - 12)
    ctx.stroke()
  }, [events, videoDuration, currentTime, height])

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const time = (x / rect.width) * videoDuration
    onSeek(Math.max(0, Math.min(time, videoDuration)))
  }

  return (
    <canvas
      ref={canvasRef}
      onClick={handleClick}
      style={{
        width: "100%",
        height: `${height}px`,
        display: "block",
        cursor: "pointer",
        borderRadius: "4px",
        border: "1px solid rgba(255,255,255,0.1)",
      }}
    />
  )
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
  return `${m}:${s.toString().padStart(2, "0")}`
}

function getEventColor(typeIdx: number): string {
  const colors = [
    "rgba(255, 255, 255, 0.8)", // White
    "rgba(170, 170, 170, 0.8)", // Gray
    "rgba(120, 120, 120, 0.8)", // Dark gray
  ]
  return colors[typeIdx % colors.length]
}
