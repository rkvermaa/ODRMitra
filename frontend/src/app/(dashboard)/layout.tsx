"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/store/auth";
import {
  LayoutDashboard,
  FileText,
  FilePlus,
  Scale,
  BookOpen,
  LogOut,
  Menu,
  X,
  ChevronRight,
  Smartphone,
} from "lucide-react";
import * as api from "@/lib/api";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/disputes", label: "My Cases", icon: FileText },
  { href: "/file-case", label: "File New Case", icon: FilePlus },
  { href: "/knowledge", label: "Legal Knowledge", icon: BookOpen },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, name, role, logout, hydrate } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [botNumbers, setBotNumbers] = useState<api.BotNumber[]>([]);

  useEffect(() => {
    hydrate();
    setHydrated(true);
  }, [hydrate]);

  useEffect(() => {
    api.getBotNumbers().then(setBotNumbers).catch(() => {});
  }, []);

  useEffect(() => {
    if (hydrated && !isAuthenticated) {
      router.replace("/login");
    }
  }, [hydrated, isAuthenticated, router]);

  if (!hydrated || !isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-navy-600 border-t-transparent" />
      </div>
    );
  }

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-navy-600 text-white transition-transform lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-navy-500 px-5">
          <Scale className="h-7 w-7 text-saffron-400" />
          <div>
            <span className="text-lg font-bold tracking-tight">ODRMitra</span>
            <span className="ml-1 text-xs text-navy-200">ओडीआर मित्र</span>
          </div>
          <button
            className="ml-auto lg:hidden"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-navy-500 text-white"
                    : "text-navy-100 hover:bg-navy-500/50 hover:text-white"
                }`}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {item.label}
                {active && (
                  <ChevronRight className="ml-auto h-4 w-4 text-saffron-400" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Bot WhatsApp Numbers */}
        {botNumbers.length > 0 && (
          <div className="mx-3 mb-2 rounded-lg bg-navy-500/50 px-3 py-3">
            <div className="flex items-center gap-2 mb-2">
              <Smartphone className="h-4 w-4 text-green-400" />
              <span className="text-xs font-medium text-navy-100">WhatsApp Support</span>
            </div>
            {botNumbers.map((bot, i) => (
              <p key={i} className="text-xs text-navy-200 font-mono">
                +{bot.phone_number.replace(/(\d{2})(\d{5})(\d{5})/, "$1 $2 $3")}
                {bot.label && (
                  <span className="text-navy-300 ml-1">({bot.label})</span>
                )}
              </p>
            ))}
          </div>
        )}

        {/* User info + Logout */}
        <div className="border-t border-navy-500 p-4">
          <div className="mb-3 text-sm">
            <p className="font-medium">{name}</p>
            <p className="text-xs capitalize text-navy-200">{role}</p>
          </div>
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-navy-200 transition-colors hover:bg-navy-500 hover:text-white"
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-16 items-center gap-4 border-b border-gray-200 bg-white px-4 shadow-sm lg:px-6">
          <button
            className="lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-6 w-6 text-gray-600" />
          </button>

          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Scale className="h-4 w-4 text-navy-600" />
            <span className="font-medium text-navy-600">ODRMitra</span>
            <ChevronRight className="h-3 w-3" />
            <span className="capitalize text-gray-700">
              {pathname.split("/").filter(Boolean).pop()?.replace("-", " ") || "Dashboard"}
            </span>
          </div>

          <div className="ml-auto flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full bg-saffron-50 px-3 py-1 text-xs font-medium text-saffron-700 sm:flex">
              <div className="h-2 w-2 rounded-full bg-saffron-500" />
              AI Assistant Ready
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
