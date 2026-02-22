"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  TrendingUp,
  Scale,
  IndianRupee,
  Clock,
  AlertTriangle,
  CheckCircle,
  MessageSquare,
} from "lucide-react";
import * as api from "@/lib/api";
import { formatINR, statusLabel } from "@/lib/format";
import ChatPanel from "@/components/chat/ChatPanel";

export default function DGPPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [dispute, setDispute] = useState<api.Dispute | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDispute(id)
      .then(setDispute)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading || !dispute) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-navy-600 border-t-transparent" />
      </div>
    );
  }

  const prediction = dispute.ai_outcome_prediction as {
    likely_outcome?: string;
    confidence?: number;
    reasoning?: string;
    statutory_basis?: string;
  } | null;

  return (
    <div className="space-y-6">
      <div>
        <button
          onClick={() => router.push(`/disputes/${id}`)}
          className="mb-2 flex items-center gap-1 text-sm text-gray-500 hover:text-navy-600"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to case
        </button>
        <h1 className="text-2xl font-bold text-gray-900">
          Digital Guided Pathway
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          AI-powered outcome prediction for {dispute.case_number}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left: Prediction */}
        <div className="space-y-4">
          {/* Summary card */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="h-5 w-5 text-saffron-500" />
              <h3 className="font-semibold text-gray-900">Outcome Prediction</h3>
            </div>

            {prediction ? (
              <div className="space-y-4">
                {prediction.likely_outcome && (
                  <div className="rounded-lg bg-green-50 p-4">
                    <p className="text-xs font-medium text-green-600 uppercase tracking-wider">Most Likely Outcome</p>
                    <p className="mt-1 text-lg font-semibold text-green-800">
                      {prediction.likely_outcome}
                    </p>
                    {prediction.confidence && (
                      <div className="mt-2">
                        <div className="flex items-center justify-between text-xs text-green-600">
                          <span>Confidence</span>
                          <span>{Math.round(Number(prediction.confidence) * 100)}%</span>
                        </div>
                        <div className="mt-1 h-2 rounded-full bg-green-200">
                          <div
                            className="h-2 rounded-full bg-green-500"
                            style={{ width: `${Number(prediction.confidence) * 100}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {prediction.reasoning && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Reasoning</p>
                    <p className="text-sm text-gray-700 leading-relaxed">
                      {prediction.reasoning}
                    </p>
                  </div>
                )}

                {prediction.statutory_basis && (
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Statutory Basis</p>
                    <p className="text-sm text-gray-700">
                      {prediction.statutory_basis}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <AlertTriangle className="mx-auto h-10 w-10 text-gray-300" />
                <p className="mt-3 font-medium text-gray-600">
                  No prediction available yet
                </p>
                <p className="mt-1 text-sm text-gray-400">
                  Use the AI chat to request an outcome prediction for this case
                </p>
              </div>
            )}
          </div>

          {/* Financial summary */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <div className="flex items-center gap-2 mb-4">
              <IndianRupee className="h-5 w-5 text-navy-600" />
              <h3 className="font-semibold text-gray-900">Financial Summary</h3>
            </div>
            <div className="space-y-3">
              <FinRow label="Invoice Amount" value={formatINR(dispute.invoice_amount)} />
              <FinRow label="Amount Received" value={formatINR(dispute.amount_received)} />
              <FinRow label="Principal Outstanding" value={formatINR(dispute.principal_amount)} />
              <FinRow label="Interest (Sec. 16)" value={formatINR(dispute.interest_amount)} highlight />
              <div className="border-t border-gray-200 pt-3">
                <FinRow label="Total Claimed" value={formatINR(dispute.claimed_amount)} bold />
              </div>
            </div>
          </div>

          {/* Settlement suggestion */}
          <div className="rounded-xl border-2 border-dashed border-saffron-300 bg-saffron-50 p-6">
            <div className="flex items-center gap-2 mb-3">
              <Scale className="h-5 w-5 text-saffron-600" />
              <h3 className="font-semibold text-saffron-800">Settlement Suggestion</h3>
            </div>
            <p className="text-sm text-saffron-700 leading-relaxed">
              Based on the case analysis, a negotiated settlement of{" "}
              <strong>
                {formatINR(
                  dispute.claimed_amount
                    ? dispute.claimed_amount * 0.85
                    : null
                )}
              </strong>{" "}
              (85% of claimed amount) could save both parties time and legal costs.
              Use the AI assistant to explore settlement options.
            </p>
          </div>
        </div>

        {/* Right: Chat */}
        <div style={{ height: "calc(100vh - 220px)" }}>
          <ChatPanel
            disputeId={dispute.id}
            placeholder="Ask about outcome prediction, interest calculation..."
          />
        </div>
      </div>
    </div>
  );
}

function FinRow({
  label,
  value,
  bold,
  highlight,
}: {
  label: string;
  value: string;
  bold?: boolean;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className={`text-sm ${bold ? "font-semibold text-gray-900" : "text-gray-600"}`}>
        {label}
      </span>
      <span
        className={`text-sm ${
          bold
            ? "text-lg font-bold text-navy-800"
            : highlight
            ? "font-semibold text-saffron-600"
            : "font-medium text-gray-900"
        }`}
      >
        {value}
      </span>
    </div>
  );
}
