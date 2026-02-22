/** Format INR currency */
export function formatINR(amount: number | null | undefined): string {
  if (amount == null) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

/** Format date to DD MMM YYYY */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

/** Human-readable status */
const STATUS_LABELS: Record<string, string> = {
  filed: "Filed",
  intimation_sent: "Intimation Sent",
  sod_filed: "SOD Filed",
  pre_msefc: "Pre-MSEFC",
  dgp: "Digital Guided Pathway",
  negotiation: "Negotiation",
  msefc: "MSEFC",
  scrutiny_soc: "Scrutiny (SOC)",
  notice: "Notice",
  scrutiny_sod: "Scrutiny (SOD)",
  conciliation_assigned: "Conciliation Assigned",
  conciliation_proceedings: "Conciliation Proceedings",
  conciliation: "Conciliation",
  arbitration: "Arbitration",
  resolution: "Resolution",
  closed: "Closed",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] || status;
}

/** Category labels */
const CATEGORY_LABELS: Record<string, string> = {
  delayed_payment: "Delayed Payment",
  non_payment: "Non-Payment",
  partial_payment: "Partial Payment",
  disputed_quality: "Disputed Quality",
  contractual_dispute: "Contractual Dispute",
  other: "Other",
};

export function categoryLabel(cat: string): string {
  return CATEGORY_LABELS[cat] || cat;
}

/** Status color classes */
export function statusColor(status: string): string {
  switch (status) {
    case "filed":
      return "bg-blue-100 text-blue-800";
    case "intimation_sent":
    case "sod_filed":
      return "bg-indigo-100 text-indigo-800";
    case "pre_msefc":
    case "dgp":
    case "negotiation":
      return "bg-saffron-100 text-saffron-800";
    case "msefc":
    case "scrutiny_soc":
    case "notice":
    case "scrutiny_sod":
      return "bg-purple-100 text-purple-800";
    case "conciliation_assigned":
    case "conciliation_proceedings":
    case "conciliation":
      return "bg-teal-100 text-teal-800";
    case "arbitration":
      return "bg-red-100 text-red-800";
    case "resolution":
    case "closed":
      return "bg-green-100 text-green-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}
