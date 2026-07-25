"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  FilePlus,
  TrendingUp,
  Clock,
  IndianRupee,
  AlertCircle,
  ArrowRight,
  Scale,
} from "lucide-react";
import * as api from "@/lib/api";
import { formatINR, formatDate, statusLabel, statusColor, categoryLabel } from "@/lib/format";
import { useAuthStore } from "@/store/auth";

export default function DashboardPage() {
  const { name } = useAuthStore();
  const [disputes, setDisputes] = useState<api.Dispute[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listDisputes()
      .then(setDisputes)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totalClaimed = disputes.reduce((s, d) => s + (d.claimed_amount || 0), 0);
  const activeCount = disputes.filter(
    (d) => !["closed", "resolution"].includes(d.status)
  ).length;
  const filedCount = disputes.filter((d) => d.status === "filed").length;

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-navy-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Greeting hero */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-navy-600 via-navy-700 to-navy-800 p-6 text-white shadow-lg shadow-navy-200/60">
        <div
          className="pointer-events-none absolute -top-16 right-0 h-56 w-56 rounded-full opacity-20"
          style={{ background: "radial-gradient(circle, #f97316, transparent 70%)" }}
        />
        <h1 className="relative text-2xl font-bold">
          Namaste, {name?.split(" ")[0]} 🙏
        </h1>
        <p className="relative mt-1 text-sm text-navy-200">
          Here&apos;s an overview of your MSME dispute cases
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Cases"
          value={disputes.length.toString()}
          icon={FileText}
          color="navy"
        />
        <StatCard
          label="Active Cases"
          value={activeCount.toString()}
          icon={TrendingUp}
          color="saffron"
        />
        <StatCard
          label="Awaiting Action"
          value={filedCount.toString()}
          icon={Clock}
          color="blue"
        />
        <StatCard
          label="Total Claimed"
          value={formatINR(totalClaimed)}
          icon={IndianRupee}
          color="green"
        />
      </div>

      {/* Quick actions */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Link
          href="/file-case"
          className="group relative flex items-center gap-4 overflow-hidden rounded-2xl bg-gradient-to-br from-saffron-500 to-saffron-600 p-5 text-white shadow-lg shadow-saffron-200 transition-all hover:-translate-y-0.5 hover:shadow-xl hover:shadow-saffron-300"
        >
          <div
            className="pointer-events-none absolute -right-8 -top-8 h-28 w-28 rounded-full opacity-25"
            style={{ background: "radial-gradient(circle, #fff, transparent 70%)" }}
          />
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-white/20 backdrop-blur">
            <FilePlus className="h-6 w-6" />
          </div>
          <div>
            <p className="font-semibold">File New Case</p>
            <p className="text-sm text-saffron-100">
              Voice-assisted case filing with AI
            </p>
          </div>
          <ArrowRight className="ml-auto h-5 w-5 shrink-0 text-saffron-100 transition-transform group-hover:translate-x-1" />
        </Link>

        <Link
          href="/disputes"
          className="group flex items-center gap-4 rounded-2xl border border-gray-100 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-navy-200 hover:shadow-md"
        >
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-navy-500 to-navy-700 text-white shadow-md shadow-navy-100">
            <FileText className="h-6 w-6" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">View All Cases</p>
            <p className="text-sm text-gray-500">Track status and documents</p>
          </div>
          <ArrowRight className="ml-auto h-5 w-5 shrink-0 text-gray-300 transition-transform group-hover:translate-x-1" />
        </Link>

        <Link
          href="/knowledge"
          className="group flex items-center gap-4 rounded-2xl border border-gray-100 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md"
        >
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 text-white shadow-md shadow-indigo-100">
            <Scale className="h-6 w-6" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">Legal Knowledge</p>
            <p className="text-sm text-gray-500">MSMED Act & provisions</p>
          </div>
          <ArrowRight className="ml-auto h-5 w-5 shrink-0 text-gray-300 transition-transform group-hover:translate-x-1" />
        </Link>
      </div>

      {/* Recent cases */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Recent Cases</h2>
          <Link
            href="/disputes"
            className="text-sm font-medium text-navy-600 hover:underline"
          >
            View all
          </Link>
        </div>

        {disputes.length === 0 ? (
          <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
            <AlertCircle className="mx-auto h-10 w-10 text-gray-300" />
            <p className="mt-3 font-medium text-gray-600">No cases yet</p>
            <p className="mt-1 text-sm text-gray-400">
              File your first dispute case to get started
            </p>
            <Link
              href="/file-case"
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-navy-600 px-4 py-2 text-sm font-medium text-white hover:bg-navy-700"
            >
              <FilePlus className="h-4 w-4" />
              File New Case
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {disputes.slice(0, 5).map((d) => (
              <Link
                key={d.id}
                href={`/disputes/${d.id}`}
                className="flex items-center gap-4 rounded-2xl border border-gray-100 bg-white p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:border-navy-200 hover:shadow-md"
              >
                <div className="hidden h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-navy-50 to-navy-100 text-sm font-bold text-navy-600 sm:flex">
                  {d.case_number.split("-").pop()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-gray-900">
                    {d.title}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                    <span>{d.case_number}</span>
                    <span>·</span>
                    <span>{categoryLabel(d.category)}</span>
                    {d.respondent_name && (
                      <>
                        <span>·</span>
                        <span>vs {d.respondent_name}</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="hidden flex-col items-end gap-1 sm:flex">
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColor(d.status)}`}
                  >
                    {statusLabel(d.status)}
                  </span>
                  {d.claimed_amount && (
                    <span className="text-sm font-semibold text-gray-700">
                      {formatINR(d.claimed_amount)}
                    </span>
                  )}
                </div>
                <ArrowRight className="h-4 w-4 shrink-0 text-gray-300" />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  const iconBgMap: Record<string, string> = {
    navy: "bg-gradient-to-br from-navy-500 to-navy-700 shadow-navy-200",
    saffron: "bg-gradient-to-br from-saffron-400 to-saffron-600 shadow-saffron-200",
    blue: "bg-gradient-to-br from-blue-500 to-blue-700 shadow-blue-200",
    green: "bg-gradient-to-br from-green-500 to-green-700 shadow-green-200",
  };
  const accentMap: Record<string, string> = {
    navy: "from-navy-500",
    saffron: "from-saffron-500",
    blue: "from-blue-500",
    green: "from-green-500",
  };

  return (
    <div className="group relative overflow-hidden rounded-2xl border border-gray-100 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md">
      <div
        className={`absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r ${accentMap[color]} to-transparent`}
      />
      <div className="flex items-center gap-3.5">
        <div
          className={`flex h-11 w-11 items-center justify-center rounded-xl text-white shadow-lg ${iconBgMap[color]}`}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-[13px] font-medium text-gray-500">{label}</p>
          <p className="text-[1.35rem] font-bold tracking-tight text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
}
