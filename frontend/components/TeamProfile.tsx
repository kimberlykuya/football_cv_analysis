import type { TeamProfileResponse } from "@/lib/types"

type TeamProfileProps = {
  teamId: string
  profile: TeamProfileResponse["profile"]
}

interface StoredEvent {
  type?: string
  zone?: string
  timestamp?: string
  description?: string
  clip_id?: string
}

function isEventObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function extractEvents(profile: unknown): StoredEvent[] {
  if (!isEventObject(profile)) return []

  // ChromaDB returns { ids, documents, metadatas, ... }
  const documents: string[] = Array.isArray(
    (profile as Record<string, unknown>).documents
  )
    ? ((profile as Record<string, unknown>).documents as string[])
    : []

  const metadatas: Record<string, unknown>[] = Array.isArray(
    (profile as Record<string, unknown>).metadatas
  )
    ? ((profile as Record<string, unknown>).metadatas as Record<string, unknown>[])
    : []

  return metadatas.map((meta, i) => ({
    type: String(meta.event_type ?? meta.type ?? "unknown"),
    zone: String(meta.zone ?? ""),
    timestamp: String(meta.timestamp ?? ""),
    description: documents[i] ?? "",
    clip_id: String(meta.clip_id ?? ""),
  }))
}

function EventTypeBadge({ type }: { type: string }) {
  const colorMap: Record<string, string> = {
    overload: "#dc2626",
    high_line: "#2563eb",
    counter_attack: "#f59e0b",
    pressing: "#7c3aed",
  }
  const bg = colorMap[type] ?? "#6b7280"
  return (
    <span
      style={{
        display: "inline-block",
        background: bg,
        color: "#fff",
        borderRadius: 4,
        padding: "2px 8px",
        fontSize: 12,
        fontWeight: 600,
        textTransform: "uppercase",
      }}
    >
      {type.replace(/_/g, " ")}
    </span>
  )
}

export default function TeamProfile({ teamId, profile }: TeamProfileProps) {
  const events = extractEvents(profile)
  const eventTypes = new Set(events.map((e) => e.type ?? "unknown"))
  const clipIds = new Set(events.map((e) => e.clip_id).filter(Boolean))

  return (
    <section style={{ display: "grid", gap: 24 }}>
      <div>
        <h1 style={{ margin: 0 }}>Team Profile: {teamId}</h1>
        <p style={{ color: "#888", margin: "4px 0 0" }}>
          {events.length} stored tactical events across {clipIds.size} clip(s)
        </p>
      </div>

      {/* Summary Stats */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div
          style={{
            background: "#f5f5f5",
            borderRadius: 8,
            padding: "12px 20px",
          }}
        >
          <div style={{ fontSize: 12, color: "#666" }}>Total Events</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{events.length}</div>
        </div>
        <div
          style={{
            background: "#f5f5f5",
            borderRadius: 8,
            padding: "12px 20px",
          }}
        >
          <div style={{ fontSize: 12, color: "#666" }}>Event Types</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>
            {eventTypes.size}
          </div>
        </div>
        <div
          style={{
            background: "#f5f5f5",
            borderRadius: 8,
            padding: "12px 20px",
          }}
        >
          <div style={{ fontSize: 12, color: "#666" }}>Clips Analyzed</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{clipIds.size}</div>
        </div>
      </div>

      {/* Event Type Distribution */}
      {eventTypes.size > 0 && (
        <div>
          <h3 style={{ margin: "0 0 8px" }}>Event Types</h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {[...eventTypes].map((type) => (
              <EventTypeBadge key={type} type={type} />
            ))}
          </div>
        </div>
      )}

      {/* Events Table */}
      {events.length > 0 && (
        <div>
          <h3 style={{ margin: "0 0 12px" }}>Stored Events</h3>
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 14,
              }}
            >
              <thead>
                <tr
                  style={{
                    background: "#f5f5f5",
                    textAlign: "left",
                  }}
                >
                  <th style={{ padding: "8px 12px" }}>Type</th>
                  <th style={{ padding: "8px 12px" }}>Zone</th>
                  <th style={{ padding: "8px 12px" }}>Timestamp</th>
                  <th style={{ padding: "8px 12px" }}>Description</th>
                </tr>
              </thead>
              <tbody>
                {events.slice(0, 50).map((event, i) => (
                  <tr
                    key={i}
                    style={{
                      borderBottom: "1px solid #eee",
                    }}
                  >
                    <td style={{ padding: "8px 12px" }}>
                      <EventTypeBadge type={event.type ?? "unknown"} />
                    </td>
                    <td style={{ padding: "8px 12px" }}>{event.zone}</td>
                    <td style={{ padding: "8px 12px" }}>{event.timestamp}s</td>
                    <td
                      style={{
                        padding: "8px 12px",
                        maxWidth: 400,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {event.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {events.length > 50 && (
            <p style={{ color: "#888", fontSize: 13, marginTop: 8 }}>
              Showing 50 of {events.length} events.
            </p>
          )}
        </div>
      )}

      {/* Raw Data (collapsed by default) */}
      <details>
        <summary style={{ cursor: "pointer", color: "#888", fontSize: 13 }}>
          Raw profile data
        </summary>
        <pre
          style={{
            background: "#fafafa",
            padding: 12,
            borderRadius: 8,
            overflow: "auto",
            maxHeight: 400,
            fontSize: 12,
            marginTop: 8,
          }}
        >
          {JSON.stringify(profile, null, 2)}
        </pre>
      </details>
    </section>
  )
}
