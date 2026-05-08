import type { TeamProfileResponse } from "@/lib/types"

type TeamProfileProps = {
  teamId: string
  profile: TeamProfileResponse["profile"]
}

export default function TeamProfile({ teamId, profile }: TeamProfileProps) {
  return (
    <section style={{ display: "grid", gap: "12px" }}>
      <h1 style={{ margin: 0 }}>Team Profile: {teamId}</h1>
      <pre
        style={{
          background: "#121212",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: "8px",
          padding: "12px",
          overflow: "auto",
          maxHeight: "520px",
          fontSize: "12px",
        }}
      >
        {JSON.stringify(profile, null, 2)}
      </pre>
    </section>
  )
}
