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

export async function POST(request: Request) {
  const backend = process.env.BACKEND_URL ?? "http://localhost:8001"

  try {
    const payload = await request.json()

    if (!payload.match_id || !payload.question) {
      // Use "detail" to match FastAPI convention — frontend checks for this key
      return Response.json(
        { detail: "match_id and question are required" },
        { status: 400 }
      )
    }

    const response = await fetch(`${backend}/api/coach-qa`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    })

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

