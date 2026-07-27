import type { Metadata } from "next";
import Link from "next/link";
import { createTranslator, NextIntlClientProvider } from "next-intl";
import { Geist, Geist_Mono } from "next/font/google";
import { logoutAction } from "@/app/actions";
import { loadLocaleMessages } from "@/lib/i18n";
import { LocaleToggle } from "@/components/locale-toggle";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
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

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const { locale, messages } = await loadLocaleMessages();
  const t = createTranslator({ locale, messages, namespace: "nav" });

  return (
    <html
      lang={locale}
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
            <nav className="border-b px-6 py-4 flex items-center justify-between text-sm">
              <div className="flex gap-4">
                <Link href="/agenda" className="font-medium hover:underline">
                  {t("agenda")}
                </Link>
                <Link href="/dashboard" className="font-medium hover:underline">
                  {t("dashboard")}
                </Link>
                <Link href="/plan" className="font-medium hover:underline">
                  {t("plan")}
                </Link>
                <Link href="/connect/gemini" className="font-medium hover:underline">
                  {t("gemini")}
                </Link>
                <Link href="/connect/garmin" className="font-medium hover:underline">
                  {t("garmin")}
                </Link>
              </div>
              <div className="flex items-center gap-4">
                <LocaleToggle />
                <ThemeToggle />
                <form action={logoutAction}>
                  <Button type="submit" variant="ghost" size="sm">
                    {t("signOut")}
                  </Button>
                </form>
              </div>
            </nav>
            <main className="flex-1">{children}</main>
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
