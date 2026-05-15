"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/api";
import { useToastStore } from "@/stores/toast-store";
import Link from "next/link";

export default function RegisterPage() {
  const router = useRouter();
  const { addToast } = useToastStore();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    setLoading(true);

    const newErrors: Record<string, string> = {};
    if (username.length < 2) newErrors.username = "Минимум 2 символа";
    if (!email.includes("@")) newErrors.email = "Некорректная почта";
    if (password.length < 8) newErrors.password = "Минимум 8 символов";

    if (Object.keys(newErrors).length) {
      setErrors(newErrors);
      setLoading(false);
      return;
    }

    try {
      await api.post("/auth/register", { email, password, username });
      addToast("Аккаунт создан! Войдите.", "success");
      router.push("/auth/login");
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.message === "Email is already registered") {
          setErrors({ email: "Почта уже зарегистрирована" });
        } else if (error.message === "Username is already taken") {
          setErrors({ username: "Имя пользователя уже занято" });
        } else {
          setErrors({ email: "Ошибка сервера. Попробуйте позже" });
        }
      } else {
        setErrors({ email: "Ошибка сервера. Попробуйте позже" });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-[calc(100dvh-5rem)]">
      <div className="flex-1 px-6 py-8 flex flex-col justify-end items-center gap-10 content-appear">
        <div className="w-full max-w-sm flex flex-col items-center gap-10">
          <h1 className="text-[1.9rem] leading-tight font-extrabold text-center">
            Зарегистрироваться
          </h1>

          <form
            onSubmit={handleSubmit}
            className="w-full flex flex-col gap-6.5 stagger-fade"
          >
            <Input
              label="Имя пользователя:"
              placeholder="Иванов(а)"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              error={errors.username}
              required
            />
            <Input
              label="Электронная почта:"
              type="email"
              placeholder="example@mail.ru"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={errors.email}
              required
            />
            <Input
              label="Пароль:"
              type="password"
              placeholder="••••••"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={errors.password}
              required
            />
          </form>

          <Link
            href="/auth/login"
            className="text-white/95 text-base hover:underline"
          >
            Уже есть аккаунт? Войти
          </Link>
        </div>

        <div className="w-full max-w-sm">
          <Button
            variant="primary"
            className="w-full text-base"
            loading={loading}
            onClick={handleSubmit}
          >
            Зарегистрироваться
          </Button>
        </div>
      </div>
    </div>
  );
}
