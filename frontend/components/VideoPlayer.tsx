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
    <div className="video-player">
      {src ? (
        <video ref={videoRef} controls src={src} />
      ) : (
        <div className="video-placeholder">
          <span>Upload a match clip to preview footage.</span>
        </div>
      )}
      {timestamps.length > 0 && onJumpTo ? (
        <div className="timestamp-row">
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
