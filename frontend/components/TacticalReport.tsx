import type { AnalyzeResponse } from "@/lib/types"

type TacticalReportProps = {
  analysis: AnalyzeResponse | null
}

function formatMetricName(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric-card">
      <span>{formatMetricName(label)}</span>
      <strong>{typeof value === "number" ? value.toFixed(1) : String(value)}</strong>
    </div>
  )
}

function PressureZoneGrid({ zones }: { zones: Record<string, number[][]> }) {
  return (
    <div className="pressure-section">
      {Object.entries(zones).map(([team, grid]) => (
        <div key={team} className="pressure-team">
          <h4>{team.replace("_", " ").toUpperCase()} pressure heatmap</h4>
          <div
            className="pressure-grid"
            style={{ gridTemplateColumns: `repeat(${grid[0]?.length ?? 2}, 1fr)` }}
          >
            {grid.flatMap((row, ri) =>
              row.map((val, ci) => (
                <div
                  key={`${ri}-${ci}`}
                  className="pressure-cell"
                  style={{
                    background: `rgba(255, 255, 255, ${Math.min(val / 100, 1) * 0.5})`,
                    color: val > 50 ? "#000" : "var(--ink)",
                  }}
                >
                  {val}%
                </div>
              ))
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function FormationDisplay({
  formations,
}: {
  formations: Record<string, number[][]>
}) {
  return (
    <div className="formation-list">
      {Object.entries(formations).map(([team, samples]) => {
        const latest = samples[samples.length - 1]
        const formationStr = latest ? latest.join("-") : "unknown"
        return (
          <div key={team} className="formation-row">
            <span>{team.replace("_", " ").toUpperCase()}</span>
            <strong>{formationStr}</strong>
            <small>{samples.length} samples</small>
          </div>
        )
      })}
    </div>
  )
}

export default function TacticalReport({ analysis }: TacticalReportProps) {
  if (!analysis) {
    return (
      <section className="empty-state">
        <p className="eyebrow">Tactical Report</p>
        <h2>Upload and analyze a video to populate match intelligence.</h2>
      </section>
    )
  }

  return (
    <section className="report-grid">
      <div className="section-heading">
        <p className="eyebrow">Tactical Report</p>
        <h2>Match intelligence</h2>
      </div>

      <div className="analysis-block primary">
        <h3>AI Tactical Analysis</h3>
        <p>{analysis.tactical_summary || "No summary generated."}</p>
      </div>

      {analysis.cross_match_report ? (
        <div className="analysis-block">
          <h3>Cross-Match Scouting Report</h3>
          <p>{analysis.cross_match_report}</p>
        </div>
      ) : null}

      <div>
        <h3>Key Metrics</h3>
        <div className="metric-grid">
          {Object.entries(analysis.metrics ?? {}).map(([key, value]) => (
            <MetricCard key={key} label={key} value={value} />
          ))}
        </div>
        <div style={{ marginTop: "12px" }}>
          <p className="muted">{analysis.events_detected} tactical events detected</p>
          <div
            style={{
              fontSize: "11px",
              color: "rgba(255,255,255,0.5)",
              marginTop: "6px",
              display: "flex",
              gap: "8px",
              flexWrap: "wrap",
            }}
          >
            <span
              style={{
                padding: "2px 8px",
                background: "rgba(150,200,255,0.1)",
                color: "#aaccff",
                borderRadius: "3px",
                fontWeight: "500",
              }}
            >
              🧠 Qwen Validation
            </span>
            <span
              style={{
                padding: "2px 8px",
                background: "rgba(255,255,255,0.1)",
                color: "rgba(255,255,255,0.6)",
                borderRadius: "3px",
                fontWeight: "500",
              }}
            >
              + Confidence Scoring
            </span>
          </div>
        </div>
      </div>

      <div className="report-columns">
        <div>
          <h3>Pressure Zones</h3>
          <PressureZoneGrid zones={analysis.pressure_zones ?? {}} />
        </div>
        <div>
          <h3>Detected Formations</h3>
          <FormationDisplay formations={analysis.formations ?? {}} />
        </div>
      </div>
    </section>
  )
}
