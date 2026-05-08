export async function GET(
  _request: Request,
  { params }: { params: Promise<{ matchId: string }> }
) {
  const backend = process.env.BACKEND_URL ?? "http://localhost:8001"
  const { matchId } = await params
  try {
    const response = await fetch(`${backend}/api/analyses/${matchId}`, { cache: "no-store" })
    const text = await response.text()
    return new Response(text, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown backend error"
    return Response.json({ detail: message }, { status: 502 })
  }
}
