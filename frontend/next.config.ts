import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Perf: enable gzip on all responses from the Next server itself.
  compress: true,
  // Perf: strip `console.*` calls from the production bundle (except errors).
  // Dev builds keep all logs so you can still debug freely.
  compiler: {
    removeConsole:
      process.env.NODE_ENV === "production" ? { exclude: ["error", "warn"] } : false,
  },
  experimental: {
    // Perf: these packages re-export huge surfaces; `optimizePackageImports`
    // rewrites `import { X } from "<pkg>"` into deep path imports so only X
    // lands in the client bundle. Biggest wins: framer-motion and lucide-react.
    optimizePackageImports: [
      "framer-motion",
      "lucide-react",
      "@tanstack/react-query",
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_URL || "http://localhost:8000"}/:path*`,
      },
      {
        source: "/storage/:path*",
        destination: `${process.env.API_URL || "http://localhost:8000"}/storage/:path*`,
      },
    ];
  },
  images: {
    // Perf: cache optimized images on disk for a day (the default is 60 s).
    // Kinopoisk posters rarely change, so a long TTL is safe here.
    minimumCacheTTL: 60 * 60 * 24,
    // Perf: limit the size matrix so the optimizer doesn't generate 8 variants
    // per image when we only ever render three card widths.
    deviceSizes: [360, 640, 768, 1080, 1280],
    imageSizes: [64, 128, 160, 200, 280, 400],
    formats: ["image/avif", "image/webp"],
    remotePatterns: [
      {
        protocol: "https",
        hostname: "kinopoiskapiunofficial.tech",
      },
      {
        protocol: "https",
        hostname: "**.kinopoisk.ru",
      },
      {
        protocol: "https",
        hostname: "**.yandex.net",
      },
      {
        protocol: "https",
        hostname: "image.tmdb.org",
      },
      {
        protocol: "http",
        hostname: "localhost",
        port: "",
      },
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
      },
      {
        protocol: "http",
        hostname: "127.0.0.1",
      },
    ],
  },
};

export default nextConfig;
