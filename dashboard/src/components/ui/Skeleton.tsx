import { cn } from "../../lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("animate-pulse bg-chip rounded", className)} />
  );
}

export function CardSkeleton() {
  return (
    <div className="bg-card-a rounded-lg border border-edge p-5 space-y-3">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-8 w-16" />
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="bg-card-a rounded-lg border border-edge overflow-hidden">
      <div className="border-b border-edge px-4 py-3 flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-20" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="border-b border-edge-a px-4 py-3 flex gap-4">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-3 w-16" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="bg-card-a rounded-lg border border-edge p-5">
      <Skeleton className="h-3 w-32 mb-4" />
      <Skeleton className="h-[220px] w-full" />
    </div>
  );
}
