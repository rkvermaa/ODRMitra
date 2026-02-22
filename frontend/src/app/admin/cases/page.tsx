"use client";

import { useEffect, useState } from "react";
import { FileText, Loader2 } from "lucide-react";
import * as api from "@/lib/api";

export default function AdminCasesPage() {
  const [cases, setCases] = useState<api.Dispute[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.adminListCases();
        setCases(data);
      } catch {
        // handled silently
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const statusColors: Record<string, string> = {
    filed: "bg-yellow-100 text-yellow-700",
    intimation_sent: "bg-blue-100 text-blue-700",
    sod_filed: "bg-purple-100 text-purple-700",
    pre_msefc: "bg-orange-100 text-orange-700",
    dgp: "bg-indigo-100 text-indigo-700",
    negotiation: "bg-teal-100 text-teal-700",
    resolution: "bg-green-100 text-green-700",
    closed: "bg-gray-100 text-gray-700",
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <FileText className="h-6 w-6 text-blue-600" />
          All Cases
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          View all disputes across the platform
        </p>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : cases.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <FileText className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p className="text-sm">No cases found.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Case No.
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Category
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Amount
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Filed
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {cases.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-mono font-medium text-blue-600">
                    {c.case_number}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                    {c.title}
                  </td>
                  <td className="px-6 py-4 text-xs text-gray-500 capitalize">
                    {c.category.replace("_", " ")}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
                        statusColors[c.status] || "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {c.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900 font-mono">
                    {c.claimed_amount
                      ? `₹${Number(c.claimed_amount).toLocaleString("en-IN")}`
                      : "—"}
                  </td>
                  <td className="px-6 py-4 text-xs text-gray-500">
                    {new Date(c.created_at).toLocaleDateString()}
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
