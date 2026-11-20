import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "ViralCut — Creator Studio", description: "Turn YouTube livestreams into standout short-form clips." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
