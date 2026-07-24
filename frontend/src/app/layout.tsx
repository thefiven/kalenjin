import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Kalenjin",
  description: "Personal training tracker",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <nav className="border-b px-6 py-4 flex items-center justify-between text-sm">
            <div className="flex gap-4">
              <Link href="/agenda" className="font-medium hover:underline">
                Agenda
              </Link>
              <Link href="/dashboard" className="font-medium hover:underline">
                Dashboard
              </Link>
            </div>
            <ThemeToggle />
          </nav>
          <main className="flex-1">{children}</main>
        </ThemeProvider>
      </body>
    </html>
  );
}
