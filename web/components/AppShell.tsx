"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { PropsWithChildren } from "react";

import { clearPassword } from "@/lib/api";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/pain-points", label: "Pain Points" },
  { href: "/report", label: "Report" },
  { href: "/demo", label: "Demo" },
];

export function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-[1300px] flex-col gap-4 p-4 lg:flex-row lg:gap-5 lg:p-7">
      <header className="card flex items-center justify-between gap-2 p-3 lg:hidden">
        <div>
          <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Friction Finder</p>
          <p className="text-sm font-semibold text-ink">Ops Backlog</p>
        </div>
        <div className="flex gap-2 overflow-x-auto">
          {links.map((link) => {
            const active = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`whitespace-nowrap rounded-md px-2 py-1 text-xs ${
                  active ? "bg-teal-700 text-white" : "bg-slate-100 text-slate-700"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>
      </header>
      <aside className="card sticky top-5 hidden h-fit w-64 shrink-0 p-4 lg:block">
        <div className="mb-5 rounded-lg bg-gradient-to-br from-slate-900 to-slate-700 p-4 text-white">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-300">Friction Finder</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">Ops Backlog</h1>
        </div>
        <nav className="space-y-1">
          {links.map((link) => {
            const active = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`block rounded-lg px-3 py-2 text-sm ${
                  active ? "bg-teal-700 text-white" : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <button
          type="button"
          className="btn-secondary mt-5 w-full"
          onClick={() => {
            clearPassword();
            router.replace("/login");
          }}
        >
          Sign out
        </button>
      </aside>
      <main className="flex-1">{children}</main>
    </div>
  );
}
