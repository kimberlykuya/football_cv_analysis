export async function GET(request: Request) {
  const backend = process.env.BACKEND_URL ?? "http://localhost:8001"
  const url = new URL(request.url)
  const query = url.searchParams.toString()
  try {
    const response = await fetch(`${backend}/api/gpu/history${query ? `?${query}` : ""}`, { cache: "no-store" })
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
