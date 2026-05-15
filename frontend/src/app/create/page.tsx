"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast-store";
import { useSessionStore } from "@/stores/session-store";
import { useUserStore } from "@/stores/user-store";
import type { GameSession } from "@/types";

export default function CreatePage() {
  const router = useRouter();
  const { addToast } = useToastStore();
  const { setGuest, setRuntimeUserId } = useUserStore();
  const { setSession } = useSessionStore();
  const [roomName, setRoomName] = useState("");
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    setLoading(true);
    try {
      const result = await api.post<{ room_id: string; user_id: string; username: string }>("/rooms");

      setRuntimeUserId(result.user_id);
      if (result.user_id.startsWith("guest:")) {
        setGuest(result.username, result.user_id);
      }

      const session = await api.get<GameSession>(`/sessions/by-code/${result.room_id}`);
      setSession(session);
      router.push(`/session/${result.room_id}`);
    } catch (err) {
      console.error("[CREATE] Error:", err);
      addToast("Не удалось создать комнату", "error");
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-[calc(100dvh-5rem)]">
      <div className="flex-1 px-6 py-8 flex flex-col justify-center items-center gap-9 content-appear">
        <h1 className="text-[1.9rem] leading-tight font-extrabold text-center text-white">
          Создать комнату
        </h1>

        <div className="w-full max-w-sm flex flex-col gap-6 stagger-fade">
          <Input
            label="Название комнаты (необязательно)"
            placeholder="Кинозал друзей"
            value={roomName}
            onChange={(e) => setRoomName(e.target.value)}
          />
        </div>

        <div className="w-full max-w-sm pt-1">
          <Button
            variant="primary"
            className="w-full"
            loading={loading}
            onClick={handleCreate}
          >
            Создать
          </Button>
        </div>
      </div>
    </div>
  );
}
