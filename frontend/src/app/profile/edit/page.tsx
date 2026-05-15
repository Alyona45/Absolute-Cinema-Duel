"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useUserStore } from "@/stores/user-store";
import { useToastStore } from "@/stores/toast-store";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function ProfileEditPage() {
  const router = useRouter();
  const { username, email, avatarUrl, updateProfile, logout } = useUserStore();
  const { addToast } = useToastStore();
  const [newUsername, setNewUsername] = useState(username || "");
  const [newEmail, setNewEmail] = useState(email || "");
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await api.postForm<{ avatar_url: string }>(
        "/users/me/avatar",
        formData
      );
      updateProfile({ avatarUrl: res.avatar_url });
      addToast("Аватар обновлён", "success");
    } catch {
      addToast("Ошибка загрузки аватара", "error");
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      const body: Record<string, string> = {};
      if (newUsername !== username) body.username = newUsername;
      if (newEmail !== email) body.email = newEmail;

      if (Object.keys(body).length > 0) {
        await api.patch("/users/me", body);
        updateProfile({
          username: newUsername || username || undefined,
          email: newEmail || email || undefined,
        });
        addToast("Профиль обновлён", "success");
      }
      router.push("/profile");
    } catch {
      addToast("Ошибка обновления профиля", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-[calc(100dvh-5rem)]">
      <div className="flex-1 px-6 py-6 flex flex-col items-center gap-8">
        <div className="flex flex-col items-center gap-3">
          <Avatar
            name={newUsername || "U"}
            src={avatarUrl}
            size="xl"
            borderColor="red"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="text-neutral-400 text-sm hover:text-white transition-colors"
          >
            Изменить фото
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleAvatarUpload}
            className="hidden"
          />
        </div>

        <div className="w-full max-w-sm flex flex-col gap-6">
          <Input
            label="Имя пользователя"
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
            placeholder="Иванов(а)"
          />
          <Input
            label="Электронная почта"
            type="email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            placeholder="example@mail.ru"
          />
        </div>
      </div>

      <div className="px-6 pb-6 flex flex-col gap-4">
        <Button
          variant="primary"
          className="w-full text-base"
          loading={loading}
          onClick={handleSave}
        >
          Обновить
        </Button>

        <button
          onClick={async () => {
            const { refreshToken } = useUserStore.getState();
            try {
              if (refreshToken) {
                await api.post("/auth/logout", { refresh_token: refreshToken });
              }
            } catch {}
            logout();
            addToast("Вы вышли из аккаунта", "info");
            router.push("/");
          }}
          className="w-full py-3 text-center text-sm font-medium transition-colors bg-transparent border-none cursor-pointer"
          style={{ color: "rgba(239,68,68,0.65)" }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "#ef4444")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "rgba(239,68,68,0.65)")}
        >
          Выйти из аккаунта
        </button>
      </div>
    </div>
  );
}
