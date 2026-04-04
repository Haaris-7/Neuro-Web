import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Neuro Web — Brain Response Analysis",
  description:
    "Analyze how websites affect cognitive load, attention, and stress responses with neuroscience-informed metrics.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${inter.variable} h-full antialiased`}>
      <body className="min-h-screen bg-[#0a0e1a] text-slate-100">{children}</body>
    </html>
  );
}
