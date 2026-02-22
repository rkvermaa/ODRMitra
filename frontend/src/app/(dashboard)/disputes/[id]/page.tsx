"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  FileText,
  Upload,
  User,
  Building,
  IndianRupee,
  Calendar,
  MapPin,
  Phone,
  Mail,
  Hash,
  TrendingUp,
  MessageSquare,
  CheckCircle,
  Circle,
  AlertCircle,
} from "lucide-react";
import * as api from "@/lib/api";
import {
  formatINR,
  formatDate,
  statusLabel,
  statusColor,
  categoryLabel,
} from "@/lib/format";
import ChatPanel from "@/components/chat/ChatPanel";
import toast from "react-hot-toast";

const WORKFLOW_STEPS = [
  { key: "filed", label: "Filed", step: 1 },
  { key: "intimation_sent", label: "Intimation", step: 2 },
  { key: "sod_filed", label: "SOD Filed", step: 3 },
  { key: "pre_msefc", label: "Pre-MSEFC", step: 4 },
  { key: "dgp", label: "DGP", step: 5 },
  { key: "negotiation", label: "Negotiation", step: 6 },
  { key: "msefc", label: "MSEFC", step: 7 },
  { key: "conciliation", label: "Conciliation", step: 8 },
  { key: "arbitration", label: "Arbitration", step: 9 },
  { key: "resolution", label: "Resolution", step: 10 },
  { key: "closed", label: "Closed", step: 11 },
];

const DOC_TYPES = [
  { value: "invoice", label: "Invoice" },
  { value: "purchase_order", label: "Purchase Order" },
  { value: "contract", label: "Contract" },
  { value: "delivery_challan", label: "Delivery Challan" },
  { value: "udyam_certificate", label: "Udyam Certificate" },
  { value: "affidavit", label: "Affidavit" },
  { value: "legal_notice", label: "Legal Notice" },
  { value: "correspondence", label: "Correspondence" },
  { value: "bank_statement", label: "Bank Statement" },
  { value: "other", label: "Other" },
];

export default function DisputeDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [dispute, setDispute] = useState<api.Dispute | null>(null);
  const [documents, setDocuments] = useState<api.Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"details" | "documents" | "chat">("details");
  const [uploading, setUploading] = useState(false);
  const [uploadType, setUploadType] = useState("invoice");

  useEffect(() => {
    Promise.all([
      api.getDispute(id),
      api.listDocuments(id),
    ])
      .then(([d, docs]) => {
        setDispute(d);
        setDocuments(docs);
      })
      .catch(() => toast.error("Failed to load case"))
      .finally(() => setLoading(false));
  }, [id]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const doc = await api.uploadDocument(id, file, uploadType);
      setDocuments((prev) => [doc, ...prev]);
      toast.success("Document uploaded!");
    } catch {
      toast.error("Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  if (loading || !dispute) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-navy-600 border-t-transparent" />
      </div>
    );
  }

  const currentStepIdx = WORKFLOW_STEPS.findIndex((s) => s.key === dispute.status);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <button
            onClick={() => router.push("/disputes")}
            className="mb-2 flex items-center gap-1 text-sm text-gray-500 hover:text-navy-600"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to cases
          </button>
          <h1 className="text-xl font-bold text-gray-900 lg:text-2xl">
            {dispute.title}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-gray-500">
            <span className="font-mono">{dispute.case_number}</span>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColor(dispute.status)}`}
            >
              {statusLabel(dispute.status)}
            </span>
            <span>{categoryLabel(dispute.category)}</span>
          </div>
        </div>
        {dispute.status === "dgp" && (
          <Link
            href={`/dgp/${dispute.id}`}
            className="flex items-center gap-2 rounded-lg bg-saffron-500 px-4 py-2 text-sm font-semibold text-white hover:bg-saffron-600"
          >
            <TrendingUp className="h-4 w-4" />
            View DGP Prediction
          </Link>
        )}
      </div>

      {/* Timeline */}
      <div className="rounded-xl border border-gray-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-semibold text-gray-700">Case Progress</h3>
        <div className="flex items-center gap-0 overflow-x-auto pb-2">
          {WORKFLOW_STEPS.map((step, i) => {
            const done = i <= currentStepIdx;
            const current = i === currentStepIdx;
            return (
              <div key={step.key} className="flex items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                      current
                        ? "bg-saffron-500 text-white ring-4 ring-saffron-100"
                        : done
                        ? "bg-green-500 text-white"
                        : "bg-gray-200 text-gray-500"
                    }`}
                  >
                    {done && !current ? (
                      <CheckCircle className="h-4 w-4" />
                    ) : (
                      step.step
                    )}
                  </div>
                  <span
                    className={`mt-1 whitespace-nowrap text-[10px] font-medium ${
                      current ? "text-saffron-600" : done ? "text-green-600" : "text-gray-400"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
                {i < WORKFLOW_STEPS.length - 1 && (
                  <div
                    className={`mx-1 h-0.5 w-6 shrink-0 ${
                      i < currentStepIdx ? "bg-green-400" : "bg-gray-200"
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 rounded-lg border border-gray-200 bg-white p-1">
        {(["details", "documents", "chat"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium capitalize transition-colors ${
              activeTab === t
                ? "bg-navy-600 text-white"
                : "text-gray-600 hover:bg-gray-50"
            }`}
          >
            {t === "chat" ? "AI Chat" : t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "details" && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Respondent info */}
          <InfoCard title="Respondent (Buyer)" icon={Building}>
            <InfoRow icon={User} label="Name" value={dispute.respondent_name} />
            <InfoRow icon={Phone} label="Mobile" value={dispute.respondent_mobile} />
            <InfoRow icon={Mail} label="Email" value={dispute.respondent_email} />
            <InfoRow icon={Hash} label="GSTIN" value={dispute.respondent_gstin} />
            <InfoRow icon={MapPin} label="State" value={dispute.respondent_state} />
          </InfoCard>

          {/* Financial */}
          <InfoCard title="Financial Summary" icon={IndianRupee}>
            <InfoRow icon={IndianRupee} label="Invoice Amount" value={formatINR(dispute.invoice_amount)} />
            <InfoRow icon={IndianRupee} label="Amount Received" value={formatINR(dispute.amount_received)} />
            <InfoRow icon={IndianRupee} label="Principal" value={formatINR(dispute.principal_amount)} />
            <InfoRow icon={TrendingUp} label="Interest Rate" value={dispute.interest_rate ? `${dispute.interest_rate}% p.a.` : null} />
            <InfoRow icon={IndianRupee} label="Interest Amount" value={formatINR(dispute.interest_amount)} />
            <div className="mt-2 rounded-lg bg-navy-50 px-4 py-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-navy-700">Total Claimed</span>
                <span className="text-lg font-bold text-navy-800">
                  {formatINR(dispute.claimed_amount)}
                </span>
              </div>
            </div>
          </InfoCard>

          {/* Transaction */}
          <InfoCard title="Transaction Details" icon={FileText}>
            <InfoRow icon={Hash} label="PO Number" value={dispute.po_number} />
            <InfoRow icon={Calendar} label="PO Date" value={formatDate(dispute.po_date)} />
            <InfoRow icon={FileText} label="Payment Terms" value={dispute.payment_terms} />
            <InfoRow icon={FileText} label="Goods/Services" value={dispute.goods_services_description} />
          </InfoCard>

          {/* SOC Narrative */}
          <InfoCard title="Statement of Claim" icon={FileText}>
            {dispute.cause_of_action && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-gray-500">Cause of Action</p>
                <p className="text-sm text-gray-800 whitespace-pre-wrap">{dispute.cause_of_action}</p>
              </div>
            )}
            {dispute.relief_sought && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-gray-500">Relief Sought</p>
                <p className="text-sm text-gray-800 whitespace-pre-wrap">{dispute.relief_sought}</p>
              </div>
            )}
            {!dispute.cause_of_action && !dispute.relief_sought && (
              <p className="text-sm text-gray-400 italic">No SOC narrative provided yet</p>
            )}
          </InfoCard>
        </div>
      )}

      {activeTab === "documents" && (
        <div className="space-y-4">
          {/* Upload */}
          <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-200 bg-white p-4">
            <select
              value={uploadType}
              onChange={(e) => setUploadType(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              {DOC_TYPES.map((dt) => (
                <option key={dt.value} value={dt.value}>
                  {dt.label}
                </option>
              ))}
            </select>
            <label className="flex cursor-pointer items-center gap-2 rounded-lg bg-navy-600 px-4 py-2 text-sm font-medium text-white hover:bg-navy-700">
              <Upload className="h-4 w-4" />
              {uploading ? "Uploading..." : "Upload Document"}
              <input
                type="file"
                className="hidden"
                onChange={handleUpload}
                disabled={uploading}
                accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
              />
            </label>
          </div>

          {/* Document list */}
          {documents.length === 0 ? (
            <div className="rounded-xl border border-gray-200 bg-white p-12 text-center">
              <FileText className="mx-auto h-10 w-10 text-gray-300" />
              <p className="mt-3 font-medium text-gray-600">No documents uploaded yet</p>
            </div>
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-4"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy-50">
                    <FileText className="h-5 w-5 text-navy-600" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-900">
                      {doc.original_filename}
                    </p>
                    <p className="text-xs text-gray-500">
                      {DOC_TYPES.find((t) => t.value === doc.doc_type)?.label || doc.doc_type}
                      {" · "}
                      {(doc.file_size / 1024).toFixed(1)} KB
                      {" · "}
                      {formatDate(doc.created_at)}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      doc.analysis_status === "completed"
                        ? "bg-green-100 text-green-700"
                        : doc.analysis_status === "processing"
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {doc.analysis_status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "chat" && (
        <div style={{ height: "calc(100vh - 360px)" }}>
          <ChatPanel
            disputeId={dispute.id}
            placeholder={`Ask about case ${dispute.case_number}...`}
          />
        </div>
      )}
    </div>
  );
}

function InfoCard({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center gap-2">
        <Icon className="h-5 w-5 text-navy-600" />
        <h3 className="font-semibold text-gray-900">{title}</h3>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" />
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-sm text-gray-800">{value || "—"}</p>
      </div>
    </div>
  );
}
