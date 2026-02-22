"use client";

import { useState } from "react";
import {
  BookOpen,
  Scale,
  Clock,
  IndianRupee,
  FileText,
  ChevronDown,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import ChatPanel from "@/components/chat/ChatPanel";

const SECTIONS = [
  {
    title: "MSMED Act 2006 — Key Provisions",
    icon: Scale,
    items: [
      {
        heading: "Section 2 — Definitions",
        content:
          "Defines 'supplier' (micro/small enterprise), 'buyer' (any entity purchasing goods/services), 'appointed day' (day agreed for payment or, if no agreement, the day of acceptance).",
      },
      {
        heading: "Section 15 — Payment Timeline",
        content:
          "Buyer must pay the supplier on or before the agreed date. If no agreement, payment must be made within 45 days of acceptance of goods/services. This is the core provision that triggers delayed payment disputes.",
      },
      {
        heading: "Section 16 — Interest on Delayed Payment",
        content:
          "If buyer fails to pay within Section 15 timeline, buyer is liable to pay compound interest at 3× the bank rate notified by RBI. Interest is calculated monthly on the outstanding amount.",
      },
      {
        heading: "Section 17 — Buyer's Liability",
        content:
          "Buyer cannot contest the interest liability. Interest accrues from the appointed day until actual date of payment.",
      },
      {
        heading: "Section 18 — Reference to MSEFC",
        content:
          "Either party can refer the dispute to Micro and Small Enterprises Facilitation Council (MSEFC). The council first attempts conciliation; if that fails, it proceeds to arbitration.",
      },
    ],
  },
  {
    title: "ODR Process Flow",
    icon: Clock,
    items: [
      {
        heading: "Step 1-2: Registration & Filing",
        content:
          "Seller registers using Udyam Registration Number. Files Statement of Claim (SOC) with invoices, PO, delivery proof, and affidavit.",
      },
      {
        heading: "Step 3-4: Intimation & Defense",
        content:
          "Buyer is notified via WhatsApp/Email/SMS. Buyer files Statement of Defense (SOD) within stipulated time.",
      },
      {
        heading: "Step 5-7: Pre-MSEFC, DGP & Negotiation",
        content:
          "AI predicts outcome (Digital Guided Pathway). Parties attempt settlement through AI-guided unmanned negotiation before formal proceedings.",
      },
      {
        heading: "Step 8-16: Formal Proceedings",
        content:
          "If negotiation fails: MSEFC scrutiny → notice → conciliation → arbitration → resolution. These steps involve human conciliators/arbitrators.",
      },
    ],
  },
  {
    title: "Interest Calculation",
    icon: IndianRupee,
    items: [
      {
        heading: "Formula",
        content:
          "Compound interest at 3× RBI bank rate (currently ~8% → 24% p.a.), compounded monthly. Formula: P × (1 + r/12)^n - P, where P = principal, r = annual rate, n = months overdue.",
      },
      {
        heading: "Example",
        content:
          "Invoice: ₹8,50,000 | Overdue: 6 months | Rate: 24% p.a.\nMonthly rate: 2%\nInterest = 8,50,000 × (1.02^6 - 1) = ₹1,07,297\nTotal due = ₹9,57,297",
      },
    ],
  },
  {
    title: "Required Documents",
    icon: FileText,
    items: [
      {
        heading: "Mandatory Documents",
        content:
          "1. Invoice / Bill (original or copy)\n2. Udyam Registration Certificate\n3. Affidavit (notarized)\n4. Identity proof of authorized signatory",
      },
      {
        heading: "Supporting Documents (Recommended)",
        content:
          "1. Purchase Order / Work Order\n2. Delivery Challan / Proof of Delivery\n3. Contract / Agreement\n4. Payment reminder correspondence\n5. Bank statement showing non-receipt\n6. Legal notice (if sent)",
      },
    ],
  },
];

export default function KnowledgePage() {
  const [expandedSection, setExpandedSection] = useState<number>(0);
  const [expandedItem, setExpandedItem] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Legal Knowledge Base</h1>
        <p className="mt-1 text-sm text-gray-500">
          MSMED Act 2006 provisions, ODR process, and filing requirements
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Left: Knowledge sections */}
        <div className="space-y-4 lg:col-span-3">
          {SECTIONS.map((section, si) => {
            const Icon = section.icon;
            const expanded = expandedSection === si;
            return (
              <div
                key={si}
                className="rounded-xl border border-gray-200 bg-white overflow-hidden"
              >
                <button
                  onClick={() => setExpandedSection(expanded ? -1 : si)}
                  className="flex w-full items-center gap-3 px-5 py-4 text-left hover:bg-gray-50"
                >
                  <Icon className="h-5 w-5 text-navy-600" />
                  <span className="flex-1 font-semibold text-gray-900">
                    {section.title}
                  </span>
                  {expanded ? (
                    <ChevronDown className="h-5 w-5 text-gray-400" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  )}
                </button>
                {expanded && (
                  <div className="border-t border-gray-100 px-5 py-3 space-y-2">
                    {section.items.map((item, ii) => {
                      const itemKey = `${si}-${ii}`;
                      const itemExpanded = expandedItem === itemKey;
                      return (
                        <div key={ii} className="rounded-lg border border-gray-100">
                          <button
                            onClick={() =>
                              setExpandedItem(itemExpanded ? null : itemKey)
                            }
                            className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm hover:bg-gray-50"
                          >
                            <span className="flex-1 font-medium text-gray-800">
                              {item.heading}
                            </span>
                            {itemExpanded ? (
                              <ChevronDown className="h-4 w-4 text-gray-400" />
                            ) : (
                              <ChevronRight className="h-4 w-4 text-gray-400" />
                            )}
                          </button>
                          {itemExpanded && (
                            <div className="border-t border-gray-100 px-4 py-3">
                              <p className="whitespace-pre-wrap text-sm text-gray-700 leading-relaxed">
                                {item.content}
                              </p>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Right: Chat */}
        <div className="lg:col-span-2" style={{ height: "calc(100vh - 220px)" }}>
          <ChatPanel placeholder="Ask about MSMED Act, interest calculation, required docs..." />
        </div>
      </div>
    </div>
  );
}
