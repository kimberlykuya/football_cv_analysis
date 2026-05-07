import TeamProfile from "@/components/TeamProfile"
import type { TeamProfileResponse } from "@/lib/types"

async function loadTeamProfile(teamId: string): Promise<TeamProfileResponse | null> {
  const backend = process.env.BACKEND_URL ?? "http://localhost:8001"
  const response = await fetch(`${backend}/api/team/${teamId}/profile`, {
    cache: "no-store",
  })

  if (!response.ok) {
    return null
  }

  return (await response.json()) as TeamProfileResponse
}

export default async function TeamProfilePage({
  params,
}: {
  params: Promise<{ teamId: string }>
}) {
  const { teamId } = await params
  const data = await loadTeamProfile(teamId)

  if (!data) {
    return (
      <main style={{ padding: 24, fontFamily: "sans-serif" }}>
        <h1>Team Profile</h1>
        <p>No profile data found yet.</p>
      </main>
    )
  }

  return (
    <main style={{ padding: 24, fontFamily: "sans-serif" }}>
      <TeamProfile teamId={data.team_id} profile={data.profile} />
    </main>
  )
}

