async function proxyError(response: Response) {
  const text = await response.text()
  try {
    const payload = JSON.parse(text)
    return Response.json(payload, { status: response.status })
  } catch {
    return Response.json(
      { detail: text || `Backend returned ${response.status}` },
      { status: response.status }
    )
  }
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ teamId: string }> }
) {
  const backend = process.env.BACKEND_URL ?? "http://localhost:8001"
  const { teamId } = await params

  try {
    const response = await fetch(
      `${backend}/api/team/${teamId}/profile`,
      { cache: "no-store" }
    )

    if (!response.ok) {
      return proxyError(response)
    }

    const text = await response.text()
    return new Response(text, {
      status: response.status,
      headers: {
        "content-type":
          response.headers.get("content-type") ?? "application/json",
      },
    })
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown error contacting backend"
    return Response.json({ detail: message }, { status: 502 })
  }
}
