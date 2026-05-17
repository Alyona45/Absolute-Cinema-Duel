import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "bg-neutral-700 rounded-2xl animate-pulse",
        className
      )}
    />
  );
}
