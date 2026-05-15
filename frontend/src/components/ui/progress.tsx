import { cn } from "@/lib/utils";

interface ProgressProps {
  value: number;
  className?: string;
  label?: string;
}

export function Progress({ value, className, label }: ProgressProps) {
  const percent = Math.min(Math.max(value * 100, 0), 100);

  return (
    <div className={cn("w-full", className)}>
      {label && (
        <div className="text-sm text-neutral-400 mb-1">{label}</div>
      )}
      <div className="h-2 bg-neutral-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-red-600 rounded-full transition-all duration-500"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
