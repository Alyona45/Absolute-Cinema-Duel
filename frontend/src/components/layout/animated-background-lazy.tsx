"use client";

import dynamic from "next/dynamic";

const AnimatedBackground = dynamic(
  () =>
    import("./animated-background").then((m) => m.AnimatedBackground),
  { ssr: false },
);

export function AnimatedBackgroundLazy() {
  return <AnimatedBackground />;
}
