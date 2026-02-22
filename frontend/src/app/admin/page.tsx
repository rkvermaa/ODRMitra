"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Smartphone, FileText, MessageCircle, ArrowRight } from "lucide-react";
import * as api from "@/lib/api";

interface Stats {
  total_bots: number;
  connected_bots: number;
  total_cases: number;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats>({ total_bots: 0, connected_bots: 0, total_cases: 0 });

  useEffect(() => {
    async function loadStats() {
      try {
        const [bots, cases] = await Promise.all([
          api.adminListBots(),
          api.adminListCases(),
        ]);
        setStats({
          total_bots: bots.length,
          connected_bots: bots.filter((b: api.AdminBot) => b.status === "connected").length,
          total_cases: cases.length,
        });
      } catch {
        // Stats will show zeros on error
      }
    }
    loadStats();
  }, []);

  const cards = [
    {
      title: "WhatsApp Bots",
      value: `${stats.connected_bots} / ${stats.total_bots}`,
      subtitle: "connected",
      icon: Smartphone,
      color: "green",
      href: "/admin/whatsapp-bots",
    },
    {
      title: "Total Cases",
      value: stats.total_cases.toString(),
      subtitle: "disputes filed",
      icon: FileText,
      color: "blue",
      href: "/admin/cases",
    },
    {
      title: "Telegram Bots",
      value: "—",
      subtitle: "coming soon",
      icon: MessageCircle,
      color: "gray",
      href: "/admin/telegram-bots",
    },
  ];

  const colorMap: Record<string, { bg: string; icon: string; border: string }> = {
    green: { bg: "bg-green-50", icon: "text-green-600", border: "border-green-200" },
    blue: { bg: "bg-blue-50", icon: "text-blue-600", border: "border-blue-200" },
    gray: { bg: "bg-gray-50", icon: "text-gray-400", border: "border-gray-200" },
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Admin Dashboard</h1>

      <div className="grid gap-6 md:grid-cols-3">
        {cards.map((card) => {
          const colors = colorMap[card.color];
          const Icon = card.icon;
          return (
            <Link
              key={card.title}
              href={card.href}
              className={`rounded-xl border ${colors.border} ${colors.bg} p-6 transition-shadow hover:shadow-md`}
            >
              <div className="flex items-center justify-between mb-4">
                <Icon className={`h-6 w-6 ${colors.icon}`} />
                <ArrowRight className="h-4 w-4 text-gray-400" />
              </div>
              <p className="text-3xl font-bold text-gray-900">{card.value}</p>
              <p className="text-sm text-gray-500 mt-1">{card.subtitle}</p>
              <p className="text-xs font-medium text-gray-700 mt-3">{card.title}</p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
