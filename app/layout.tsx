import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Explainable K-Means",
  description: "Turn Quantitative Clusters into Qualitative Personas using AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
