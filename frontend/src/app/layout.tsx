import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ZF-Core V19.0 — Protokol Zerotime",
  description: "Platform analisis & eksekusi trading kripto derivatif berbasis AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id" className="dark">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
