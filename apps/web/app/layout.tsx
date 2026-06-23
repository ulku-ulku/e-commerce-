import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Commerce-AI",
  description: "E-ticaret AI içgörü & karar motoru",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
