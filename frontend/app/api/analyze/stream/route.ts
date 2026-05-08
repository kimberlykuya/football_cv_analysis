export const runtime = "nodejs"

export async function POST(request: Request) {
  const backend = process.env.BACKEND_URL ?? "http://localhost:8001"
  try {
    const formData = await request.formData()
    const response = await fetch(`${backend}/api/analyze/stream`, {
      method: "POST",
      body: formData,
    })
    return new Response(response.body, {
      status: response.status,
      headers: {
        "content-type": "text/event-stream",
        "cache-control": "no-cache",
        connection: "keep-alive",
      },
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown backend error"
    return Response.json({ detail: message }, { status: 502 })
  }
}
