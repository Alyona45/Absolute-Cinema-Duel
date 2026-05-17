export default function Loading() {
  return (
    <div className="flex items-center justify-center min-h-[calc(100dvh-5rem)] px-6">
      <div className="flex flex-col items-center gap-4">
        <div className="relative h-14 w-14">
          <div className="absolute inset-0 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm" />
          <div className="absolute inset-2 rounded-full border-2 border-red-500/70 border-t-transparent animate-spin" />
        </div>
        <p className="text-sm text-white/55 tracking-[0.16em] uppercase">
          Загрузка
        </p>
      </div>
    </div>
  );
}
