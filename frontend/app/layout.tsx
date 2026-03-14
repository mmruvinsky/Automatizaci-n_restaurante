import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Panel — Jamonería MM",
  description: "Sistema de reservas",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  )
}