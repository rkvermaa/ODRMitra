"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Search,
  Filter,
  ArrowRight,
  FileText,
  FilePlus,
} from "lucide-react";
import * as api from "@/lib/api";
import {
  formatINR,
  formatDate,
  statusLabel,
  statusColor,
  categoryLabel,
} from "@/lib/format";

export default function DisputesPage() {
  const [disputes, setDisputes] = useState<api.Dispute[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    api.listDisputes()
      .then(setDisputes)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = disputes.filter((d) => {
    const matchSearch =
      !search ||
      d.title.toLowerCase().includes(search.toLowerCase()) ||
      d.case_number.toLowerCase().includes(search.toLowerCase()) ||
      d.respondent_name?.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || d.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const statuses = ["all", ...new Set(disputes.map((d) => d.status))];

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-navy-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Cases</h1>
          <p className="mt-1 text-sm text-gray-500">
            {disputes.length} total dispute case{disputes.length !== 1 ? "s" : ""}
          </p>
        </div>
        <Link
          href="/file-case"
          className="flex items-center gap-2 rounded-lg bg-navy-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-navy-700"
        >
          <FilePlus className="h-4 w-4" />
          File New Case
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 sm:max-w-xs">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search cases..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-navy-500 focus:outline-none focus:ring-2 focus:ring-navy-500/20"
          />
        </div>

        <div className="flex items-center gap-1 rounded-lg border border-gray-300 bg-white p-1">
          {statuses.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                statusFilter === s
                  ? "bg-navy-600 text-white"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {s === "all" ? "All" : statusLabel(s)}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      {filtered.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
          <FileText className="mx-auto h-10 w-10 text-gray-300" />
          <p className="mt-3 font-medium text-gray-600">No cases found</p>
          <p className="mt-1 text-sm text-gray-400">
            {search ? "Try a different search term" : "File your first case to get started"}
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-4 py-3">Case</th>
                <th className="hidden px-4 py-3 md:table-cell">Respondent</th>
                <th className="hidden px-4 py-3 sm:table-cell">Category</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Filed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((d) => (
                <tr
                  key={d.id}
                  className="cursor-pointer transition-colors hover:bg-gray-50"
                  onClick={() => (window.location.href = `/disputes/${d.id}`)}
                >
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900 truncate max-w-[250px]">
                      {d.title}
                    </p>
                    <p className="text-xs text-gray-500">{d.case_number}</p>
                  </td>
                  <td className="hidden px-4 py-3 text-sm text-gray-600 md:table-cell">
                    {d.respondent_name || "—"}
                  </td>
                  <td className="hidden px-4 py-3 sm:table-cell">
                    <span className="text-xs font-medium text-gray-600">
                      {categoryLabel(d.category)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm font-semibold text-gray-800">
                    {formatINR(d.claimed_amount)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColor(d.status)}`}
                    >
                      {statusLabel(d.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-xs text-gray-500">
                    {formatDate(d.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
