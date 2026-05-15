import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100dvh-5rem)] px-6 gap-6 text-center content-appear">
      <h1 className="text-6xl font-bold text-red-500 drop-shadow-[0_12px_40px_rgba(220,38,38,0.45)]">
        404
      </h1>
      <p className="text-white/55 max-w-xs">Страница не найдена</p>
      <Link
        href="/"
        className="px-8 py-3 bg-red-600 text-white rounded-full font-bold shadow-[0_16px_45px_rgba(220,38,38,0.28)] hover:bg-red-500 transition-all duration-300"
      >
        На главную
      </Link>
    </div>
  );
}
