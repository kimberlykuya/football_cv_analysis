"use client"

import type { RefObject } from "react"

type VideoPlayerProps = {
  src: string | null
  videoRef: RefObject<HTMLVideoElement | null>
  timestamps?: number[]
  onJumpTo?: (seconds: number) => void
}

export default function VideoPlayer({ src, videoRef, timestamps = [], onJumpTo }: VideoPlayerProps) {
  return (
    <div>
      <video ref={videoRef} controls src={src ?? undefined} style={{ width: "100%" }} />
      {timestamps.length > 0 && onJumpTo ? (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
          {timestamps.map((timestamp) => (
            <button key={timestamp} type="button" onClick={() => onJumpTo(timestamp)}>
              {timestamp.toFixed(1)}s
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}

