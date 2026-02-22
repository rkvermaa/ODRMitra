"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/store/auth";
import {
  LayoutDashboard,
  Smartphone,
  MessageCircle,
  FileText,
  BookOpen,
  Scale,
  LogOut,
  Menu,
  X,
  ChevronRight,
  Shield,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/whatsapp-bots", label: "WhatsApp Bots", icon: Smartphone },
  { href: "/admin/telegram-bots", label: "Telegram Bots", icon: MessageCircle },
  { href: "/admin/knowledge-base", label: "Knowledge Base", icon: BookOpen },
  { href: "/admin/cases", label: "All Cases", icon: FileText },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, name, role, logout, hydrate } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    hydrate();
    setHydrated(true);
  }, [hydrate]);

  useEffect(() => {
    if (hydrated && !isAuthenticated) {
      router.replace("/login");
    } else if (hydrated && role !== "admin") {
      router.replace("/dashboard");
    }
  }, [hydrated, isAuthenticated, role, router]);

  if (!hydrated || !isAuthenticated || role !== "admin") {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  const isActive = (href: string) => {
    if (href === "/admin") return pathname === "/admin";
    return pathname.startsWith(href);
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
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-blue-900 text-white transition-transform lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-blue-800 px-5">
          <Scale className="h-7 w-7 text-blue-300" />
          <div>
            <span className="text-lg font-bold tracking-tight">ODRMitra</span>
            <span className="ml-1 text-xs text-blue-300">Admin</span>
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
            const active = isActive(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-blue-800 text-white"
                    : "text-blue-100 hover:bg-blue-800/50 hover:text-white"
                }`}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {item.label}
                {active && (
                  <ChevronRight className="ml-auto h-4 w-4 text-blue-300" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* User info + Logout */}
        <div className="border-t border-blue-800 p-4">
          <div className="mb-3 flex items-center gap-2 text-sm">
            <Shield className="h-4 w-4 text-blue-300" />
            <div>
              <p className="font-medium">{name}</p>
              <p className="text-xs text-blue-300">Administrator</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-blue-200 transition-colors hover:bg-blue-800 hover:text-white"
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

          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Scale className="h-4 w-4 text-blue-600" />
            <span className="font-medium text-blue-600">Admin Portal</span>
            <ChevronRight className="h-3 w-3" />
            <span className="capitalize text-gray-700">
              {pathname === "/admin"
                ? "Dashboard"
                : pathname.split("/").filter(Boolean).pop()?.replace("-", " ") || "Dashboard"}
            </span>
          </div>

          <div className="ml-auto flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 sm:flex">
              <div className="h-2 w-2 rounded-full bg-blue-500" />
              Admin Mode
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
