import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const protectedPaths = ["/profile", "/profile/edit"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isProtected = protectedPaths.some((p) => pathname.startsWith(p));

  if (isProtected) {
    const hasSession =
      request.cookies.has("guest_token") ||
      request.cookies.has("access_token");

  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/profile/:path*"],
};
