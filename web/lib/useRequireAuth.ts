"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch, readPassword } from "./api";

export function useRequireAuth(): { ready: boolean; password: string } {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [password, setPassword] = useState("");

  useEffect(() => {
    const pwd = readPassword();
    if (!pwd) {
      router.replace("/login");
      return;
    }

    apiFetch("/dashboard", {}, pwd)
      .then(() => {
        setPassword(pwd);
        setReady(true);
      })
      .catch(() => {
        router.replace("/login");
      });
  }, [router]);

  return { ready, password };
}
