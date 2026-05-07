export interface AnalyzeResponse {
  success: boolean
  match_id: string
  team_id: string
  match_label: string
  tactical_summary: string
  cross_match_report: string
  metrics: Record<string, number>
  pressure_zones: Record<string, number[][]>
  formations: Record<string, number[][]>
  events_detected: number
  annotated_video_path?: string | null
}

export interface CoachQAResponse {
  answer: string
  cited_timestamps: number[]
  evidence_count: number
}

export interface TeamProfileResponse {
  team_id: string
  profile: unknown
}

