import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/providers/query-provider";
import { ToastContainer } from "@/components/ui/toast";
import { BottomNav } from "@/components/layout/bottom-nav";
import { AuthHydrator } from "@/components/auth-hydrator";
import { PageTransition } from "@/components/layout/page-transition";
import { AnimatedBackgroundLazy } from "@/components/layout/animated-background-lazy";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
  display: "swap",
  preload: true,
  adjustFontFallback: true,
});

export const metadata: Metadata = {
  title: "Absolute Cinema Duel",
  description:
    "Выбирайте фильм для просмотра через весёлые мини-игры — без споров и обид",
  openGraph: {
    title: "Absolute Cinema Duel",
    description: "Выбирайте фильм через мини-игры с друзьями",
    type: "website",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Absolute Cinema Duel",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#171717" },
    { media: "(prefers-color-scheme: dark)", color: "#171717" },
  ],
  colorScheme: "dark",
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru" className={inter.variable}>
      <body className="font-sans text-white min-h-dvh flex justify-center overflow-x-hidden bg-bg-primary">
        <QueryProvider>
          <AnimatedBackgroundLazy />
          <div className="app-shell w-full max-w-screen-sm mx-auto relative z-10">
            <AuthHydrator />
            <ToastContainer />
            <main className="min-h-dvh pb-22 w-full px-1">
              <PageTransition>{children}</PageTransition>
            </main>
          </div>
          <BottomNav />
        </QueryProvider>
      </body>
    </html>
  );
}
