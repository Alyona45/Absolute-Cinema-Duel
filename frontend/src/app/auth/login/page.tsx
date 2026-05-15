"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/api";
import { useUserStore } from "@/stores/user-store";
import { useToastStore } from "@/stores/toast-store";
import type { TokenResponse, User } from "@/types";
import Link from "next/link";

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useUserStore();
  const { addToast } = useToastStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailError("");
    setLoading(true);

    try {
      const tokens = await api.postFormLogin<TokenResponse>(
        "/auth/login",
        email,
        password
      );
      api.setToken(tokens.access_token);
      const user = await api.get<User>("/users/me");
      setAuth({
        userId: user.id,
        username: user.username,
        email: user.email,
        avatarUrl: user.avatar_url,
        accessToken: tokens.access_token,
        refreshToken: tokens.refresh_token,
      });
      addToast("Вы вошли в аккаунт", "success");
      router.push("/profile");
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setEmailError("Неверная почта или пароль");
      } else {
        setEmailError("Ошибка сервера. Попробуйте позже");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-[calc(100dvh-5rem)]">
      <div className="flex-1 px-6 py-8 flex flex-col justify-center items-center gap-12 content-appear">
        <div className="w-full max-w-[400px] flex flex-col items-center gap-8">
          <h1 className="text-2xl font-extrabold text-center text-white">
            Войти
          </h1>

          <form
            onSubmit={handleSubmit}
            className="w-full flex flex-col items-center gap-8 stagger-fade"
          >
            <div className="w-full flex flex-col gap-3">
              <Input
                type="email"
                placeholder="почта"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                error={emailError}
                required
              />

              <Input
                type="password"
                placeholder="пароль"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={emailError ? "border-red-600 border-2" : ""}
                required
              />
            </div>

            <div className="flex flex-col justify-center items-center gap-5 w-full">
              <button
                type="button"
                className="text-white text-base hover:underline text-center"
              >
                Забыли пароль
              </button>
              <Link
                href="/auth/register"
                className="text-white text-base hover:underline text-center"
              >
                Нет аккаунта? Зарегистрироваться
              </Link>
            </div>

            <div className="w-full max-w-[320px]">
              <button
                type="submit"
                disabled={loading}
                className="
                  w-full h-14 rounded-full bg-red-700 hover:bg-red-600
                  text-white text-lg font-bold transition-colors
                  disabled:opacity-60 disabled:cursor-not-allowed
                  shadow-[0px_8px_40px_0px_rgba(0,0,0,0.3)]
                "
              >
                {loading ? "..." : "Войти"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}