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
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {name?.split(" ")[0]}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
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
          className="group flex items-center gap-4 rounded-xl border-2 border-dashed border-saffron-300 bg-saffron-50 p-5 transition-colors hover:border-saffron-400 hover:bg-saffron-100"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-saffron-500 text-white">
            <FilePlus className="h-6 w-6" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">File New Case</p>
            <p className="text-sm text-gray-500">
              Voice-assisted case filing with AI
            </p>
          </div>
          <ArrowRight className="ml-auto h-5 w-5 text-saffron-400 transition-transform group-hover:translate-x-1" />
        </Link>

        <Link
          href="/disputes"
          className="group flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-5 transition-colors hover:border-navy-300 hover:bg-navy-50"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-navy-600 text-white">
            <FileText className="h-6 w-6" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">View All Cases</p>
            <p className="text-sm text-gray-500">Track status and documents</p>
          </div>
          <ArrowRight className="ml-auto h-5 w-5 text-gray-300 transition-transform group-hover:translate-x-1" />
        </Link>

        <Link
          href="/knowledge"
          className="group flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-5 transition-colors hover:border-navy-300 hover:bg-navy-50"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-indigo-600 text-white">
            <Scale className="h-6 w-6" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">Legal Knowledge</p>
            <p className="text-sm text-gray-500">MSMED Act & provisions</p>
          </div>
          <ArrowRight className="ml-auto h-5 w-5 text-gray-300 transition-transform group-hover:translate-x-1" />
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
                className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-4 transition-colors hover:border-navy-200 hover:shadow-sm"
              >
                <div className="hidden h-10 w-10 items-center justify-center rounded-lg bg-navy-50 text-sm font-bold text-navy-600 sm:flex">
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
  const bgMap: Record<string, string> = {
    navy: "bg-navy-50",
    saffron: "bg-saffron-50",
    blue: "bg-blue-50",
    green: "bg-green-50",
  };
  const iconBgMap: Record<string, string> = {
    navy: "bg-navy-600 text-white",
    saffron: "bg-saffron-500 text-white",
    blue: "bg-blue-600 text-white",
    green: "bg-green-600 text-white",
  };

  return (
    <div className={`rounded-xl border border-gray-200 bg-white p-5`}>
      <div className="flex items-center gap-3">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-lg ${iconBgMap[color]}`}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
}
