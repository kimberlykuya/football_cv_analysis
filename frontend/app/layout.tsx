import type { Metadata } from "next"
import type { ReactNode } from "react"
import NavBar from "@/components/NavBar"
import "./globals.css"

export const metadata: Metadata = {
  title: "FlowTrace",
  description: "Soccer tactical analyzer",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode
}>) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>
        <NavBar />
        {children}
      </body>
    </html>
  )
}

