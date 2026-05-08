"use client"

import { useEffect, useState } from "react"
import type { RefObject } from "react"

import EventTimeline from "./EventTimeline"

type VideoPlayerProps = {
  src: string | null
  videoRef: RefObject<HTMLVideoElement | null>
  timestamps?: number[]
  onJumpTo?: (seconds: number) => void
  events?: Array<{ timestamp: number; type: string; description: string }>
}

export default function VideoPlayer({ src, videoRef, timestamps = [], onJumpTo, events = [] }: VideoPlayerProps) {
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    const handleTimeUpdate = () => setCurrentTime(video.currentTime)
    const handleLoadedMetadata = () => setDuration(video.duration)
    video.addEventListener("timeupdate", handleTimeUpdate)
    video.addEventListener("loadedmetadata", handleLoadedMetadata)
    return () => {
      video.removeEventListener("timeupdate", handleTimeUpdate)
      video.removeEventListener("loadedmetadata", handleLoadedMetadata)
    }
  }, [videoRef])

  const handleSeek = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time
      void videoRef.current.play()
    }
  }

  return (
    <div className="video-player">
      {src ? <video ref={videoRef} controls src={src} /> : <div className="video-placeholder">Upload a match clip.</div>}
      {src && duration > 0 ? (
        <div style={{ marginTop: "8px" }}>
          <EventTimeline events={events} videoDuration={duration} currentTime={currentTime} onSeek={handleSeek} />
        </div>
      ) : null}
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
