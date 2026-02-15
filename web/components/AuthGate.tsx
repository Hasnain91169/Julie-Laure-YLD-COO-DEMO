"use client";

import { PropsWithChildren, useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { apiFetch, clearPassword, readPassword } from "@/lib/api";

export function AuthGate({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const router = useRouter();
  const verifiedRef = useRef(false);
  const [ready, setReady] = useState(pathname.startsWith("/login"));

  useEffect(() => {
    let cancelled = false;

    const bypass = pathname.startsWith("/login");
    if (bypass) {
      verifiedRef.current = false;
      setReady(true);
      return () => {
        cancelled = true;
      };
    }

    if (verifiedRef.current) {
      if (!readPassword()) {
        verifiedRef.current = false;
      } else {
        setReady(true);
        return () => {
          cancelled = true;
        };
      }
    }

    setReady(false);

    const authenticate = async () => {
      const password = readPassword();
      if (!password) {
        clearPassword();
        router.replace("/login");
        return;
      }

      try {
        await apiFetch("/dashboard", { method: "GET" });
        if (cancelled) {
          return;
        }
        verifiedRef.current = true;
        setReady(true);
      } catch {
        if (cancelled) {
          return;
        }
        clearPassword();
        router.replace("/login");
      }
    };

    void authenticate();

    return () => {
      cancelled = true;
    };
  }, [pathname, router]);

  if (!ready) {
    return (
      <div className="mx-auto flex min-h-screen w-full max-w-[1300px] items-center justify-center p-6">
        <div className="w-full max-w-md animate-pulse space-y-3">
          <div className="h-2 w-24 rounded bg-slate-200" />
          <div className="h-3 w-full rounded bg-slate-200" />
          <div className="h-3 w-5/6 rounded bg-slate-200" />
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
