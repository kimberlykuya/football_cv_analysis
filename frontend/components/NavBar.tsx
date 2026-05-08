"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import GPUMonitor from "./GPUMonitor"

export default function NavBar() {
  const pathname = usePathname()

  return (
    <nav
      style={{
        background: "#0a0a0a",
        borderBottom: "1px solid rgba(255,255,255,0.1)",
        padding: "12px 20px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
        <Link href="/" style={{ textDecoration: "none" }}>
          <div style={{ fontSize: "16px", fontWeight: "700", color: "var(--ink)", cursor: "pointer" }}>
            FlowTrace
          </div>
        </Link>

        <div style={{ display: "flex", gap: "16px" }}>
          <Link
            href="/"
            style={{
              fontSize: "14px",
              color: pathname === "/" ? "var(--ink)" : "var(--muted)",
              textDecoration: "none",
              borderBottom: pathname === "/" ? "2px solid var(--accent)" : "none",
              paddingBottom: "4px",
              transition: "color 0.2s ease",
            }}
          >
            Workbench
          </Link>

          <Link
            href="/analyses"
            style={{
              fontSize: "14px",
              color: pathname === "/analyses" ? "var(--ink)" : "var(--muted)",
              textDecoration: "none",
              borderBottom: pathname === "/analyses" ? "2px solid var(--accent)" : "none",
              paddingBottom: "4px",
              transition: "color 0.2s ease",
            }}
          >
            History
          </Link>
        </div>
      </div>

      <div style={{ width: "200px" }}>
        <GPUMonitor />
      </div>
    </nav>
  )
}
