"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Search, User, Film } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", icon: Home, label: "Главная" },
  { href: "/create", icon: Film, label: "Комната" },
  { href: "/join", icon: Search, label: "Найти" },
  { href: "/profile", icon: User, label: "Профиль" },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      data-scroll-ignore
      className="fixed bottom-0 left-0 right-0 z-50 bg-neutral-800/92 backdrop-blur-xl border-t border-neutral-700/50 safe-area-bottom md:left-1/2 md:right-auto md:w-full md:max-w-screen-sm md:-translate-x-1/2 md:rounded-t-2xl md:border-x"
    >
      <div className="flex items-center justify-around h-17 max-w-screen-sm w-full mx-auto px-4">
        {navItems.map(({ href, icon: Icon, label }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex flex-col items-center gap-1.5 px-3 py-2 rounded-lg transition-colors duration-200",
                active ? "text-white" : "text-neutral-400 hover:text-neutral-200"
              )}
            >
              <Icon size={21} strokeWidth={active ? 2.4 : 1.7} />
              <span className="text-[11px] leading-none font-medium">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
