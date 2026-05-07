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
    <div
      style={{
        background: "#f5f5f5",
        borderRadius: 8,
        padding: "12px 16px",
        minWidth: 140,
      }}
    >
      <div style={{ fontSize: 12, color: "#666", marginBottom: 4 }}>
        {formatMetricName(label)}
      </div>
      <div style={{ fontSize: 20, fontWeight: 700 }}>
        {typeof value === "number" ? value.toFixed(1) : String(value)}
      </div>
    </div>
  )
}

function PressureZoneGrid({ zones }: { zones: Record<string, number[][]> }) {
  return (
    <div>
      {Object.entries(zones).map(([team, grid]) => (
        <div key={team} style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>
            {team.replace("_", " ").toUpperCase()} — Pressure Heatmap (%)
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: `repeat(${grid[0]?.length ?? 2}, 1fr)`,
              gap: 4,
              maxWidth: 300,
            }}
          >
            {grid.flatMap((row, ri) =>
              row.map((val, ci) => (
                <div
                  key={`${ri}-${ci}`}
                  style={{
                    background: `rgba(220, 38, 38, ${Math.min(val / 50, 1)})`,
                    color: val > 25 ? "#fff" : "#333",
                    padding: "8px 4px",
                    textAlign: "center",
                    borderRadius: 4,
                    fontSize: 13,
                    fontWeight: 600,
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
    <div>
      {Object.entries(formations).map(([team, samples]) => {
        const latest = samples[samples.length - 1]
        const formationStr = latest ? latest.join("-") : "unknown"
        return (
          <div key={team} style={{ marginBottom: 12 }}>
            <span style={{ fontWeight: 600 }}>
              {team.replace("_", " ").toUpperCase()}:
            </span>{" "}
            <span style={{ fontSize: 18, fontWeight: 700 }}>
              {formationStr}
            </span>
            <span style={{ color: "#888", fontSize: 13, marginLeft: 8 }}>
              (from {samples.length} samples)
            </span>
          </div>
        )
      })}
    </div>
  )
}

export default function TacticalReport({ analysis }: TacticalReportProps) {
  if (!analysis) {
    return (
      <section style={{ padding: 24, color: "#888" }}>
        Tactical report coming soon — upload and analyze a video first.
      </section>
    )
  }

  return (
    <section style={{ display: "grid", gap: 24 }}>
      <h2 style={{ margin: 0 }}>Tactical Report</h2>

      {/* Tactical Summary */}
      <div>
        <h3 style={{ margin: "0 0 8px" }}>AI Tactical Analysis</h3>
        <div
          style={{
            background: "#fafafa",
            border: "1px solid #e5e5e5",
            borderRadius: 8,
            padding: 16,
            lineHeight: 1.7,
            whiteSpace: "pre-wrap",
          }}
        >
          {analysis.tactical_summary || "No summary generated."}
        </div>
      </div>

      {/* Cross-Match Report */}
      {analysis.cross_match_report && (
        <div>
          <h3 style={{ margin: "0 0 8px" }}>Cross-Match Scouting Report</h3>
          <div
            style={{
              background: "#f0f4ff",
              border: "1px solid #d0d8f0",
              borderRadius: 8,
              padding: 16,
              lineHeight: 1.7,
              whiteSpace: "pre-wrap",
            }}
          >
            {analysis.cross_match_report}
          </div>
        </div>
      )}

      {/* Key Metrics */}
      <div>
        <h3 style={{ margin: "0 0 12px" }}>Key Metrics</h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
          {Object.entries(analysis.metrics ?? {}).map(([key, value]) => (
            <MetricCard key={key} label={key} value={value} />
          ))}
        </div>
        <p style={{ fontSize: 13, color: "#888", marginTop: 8 }}>
          {analysis.events_detected} tactical events detected
        </p>
      </div>

      {/* Pressure Zones */}
      <div>
        <h3 style={{ margin: "0 0 12px" }}>Pressure Zones</h3>
        <PressureZoneGrid zones={analysis.pressure_zones ?? {}} />
      </div>

      {/* Formations */}
      <div>
        <h3 style={{ margin: "0 0 12px" }}>Detected Formations</h3>
        <FormationDisplay formations={analysis.formations ?? {}} />
      </div>
    </section>
  )
}

