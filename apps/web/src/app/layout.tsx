import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent Flight Recorder",
  description: "Trace, replay, evaluate, and audit AI agent behavior",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}