"use client";

/**
 * ODRMitra pitch deck — in-app slides for the IndiaAI Challenge presentation.
 *
 * Present from the deployed URL (/deck): ← → keys, edge clicks, or the
 * on-screen controls. Print-to-PDF renders every slide as one 16:9 page
 * (the PMU email copy is generated exactly from this page).
 */

import { useCallback, useEffect, useState } from "react";
import {
  Scale,
  Mic,
  MessageSquare,
  Globe,
  FileSearch,
  TrendingUp,
  Calculator,
  FileSignature,
  ShieldCheck,
  Landmark,
  Bot,
  Database,
  BookOpen,
  Zap,
  CheckCircle2,
  ArrowRight,
  Phone,
  UserCheck,
  Timer,
  IndianRupee,
  Layers,
  GitBranch,
  Users,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const LIVE_URL = "odrmitra.147-182-186-207.sslip.io";

/* ── Building blocks ─────────────────────────────────────────────── */

function Kicker({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-sm font-semibold uppercase tracking-[0.25em] text-[#d9b36a]">
      {children}
    </p>
  );
}

function SlideTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mt-3 text-[44px] font-bold leading-tight text-white">
      {children}
    </h2>
  );
}

function LivePill({ label = "LIVE" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-green-500/15 px-2.5 py-0.5 text-[11px] font-bold tracking-wide text-green-400 ring-1 ring-green-500/40">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-400" />
      {label}
    </span>
  );
}

function GlowBox({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-2xl border border-[#93a5c4]/15 bg-[#1c2740]/40 p-5 backdrop-blur ${className}`}
    >
      {children}
    </div>
  );
}

/* ── Slides ──────────────────────────────────────────────────────── */

function TitleSlide() {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <div className="flex items-center gap-3 rounded-full border border-[#93a5c4]/25 bg-[#1c2740]/40 px-5 py-2 text-sm text-[#cbd4e2]">
        <Landmark className="h-4 w-4 text-[#d9b36a]" />
        IndiaAI Innovation Challenge 2026 · Problem Statement 1 · Ministry of MSME
      </div>

      <div className="mt-10 flex items-center gap-5">
        <div className="flex h-24 w-24 items-center justify-center rounded-3xl bg-gradient-to-br from-[#dcb877] to-[#a87f3d] shadow-2xl shadow-[#c9a45c]/40">
          <Scale className="h-12 w-12 text-white" />
        </div>
        <div className="text-left">
          <h1 className="text-[84px] font-bold leading-none tracking-tight text-white">
            ODRMitra
          </h1>
          <p className="mt-1 text-2xl text-[#a3aec3]">ओडीआर मित्र</p>
        </div>
      </div>

      <p className="mt-8 max-w-3xl text-2xl leading-relaxed text-[#cbd4e2]">
        AI-enabled virtual negotiation assistant for resolving MSME
        delayed-payment disputes — <span className="text-[#e8cd9a]">by voice,
        WhatsApp, and web</span>
      </p>

      <div className="mt-10 flex items-center gap-4">
        <LivePill label="WORKING PoC · LIVE" />
        <span className="font-mono text-lg text-[#e8cd9a]">{LIVE_URL}</span>
      </div>
    </div>
  );
}

function ProblemSlide() {
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker>1 · Overview — The Problem</Kicker>
      <SlideTitle>India&apos;s MSMEs are owed a fortune they can&apos;t collect</SlideTitle>

      <div className="mt-12 grid grid-cols-3 gap-6">
        {[
          ["₹10L Cr+", "stuck in delayed payments every year", IndianRupee],
          ["< 1%", "of eligible MSMEs ever file a dispute", Users],
          ["18–24 mo", "for conventional resolution in courts", Timer],
        ].map(([v, l, Icon]) => {
          const I = Icon as React.ComponentType<{ className?: string }>;
          return (
            <GlowBox key={l as string} className="text-center">
              <I className="mx-auto h-8 w-8 text-[#d9b36a]" />
              <p className="mt-4 text-[52px] font-bold leading-none text-white">
                {v as string}
              </p>
              <p className="mt-3 text-lg text-[#a3aec3]">{l as string}</p>
            </GlowBox>
          );
        })}
      </div>

      <p className="mt-12 text-xl leading-relaxed text-[#cbd4e2]">
        The MSMED Act 2006 gives sellers strong rights — 45-day payment deadline,
        3× bank-rate compound interest — but{" "}
        <span className="font-semibold text-white">
          English-only portals, form-heavy filings, and legal complexity
        </span>{" "}
        keep those rights out of reach for the 80% of MSMEs in tier-2/3 India.
      </p>
    </div>
  );
}

function SolutionSlide() {
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker>1 · Overview — The Solution</Kicker>
      <SlideTitle>
        File a dispute by{" "}
        <span className="bg-gradient-to-r from-[#eedbaa] to-[#c9a45c] bg-clip-text text-transparent">
          just speaking
        </span>
      </SlideTitle>

      <div className="mt-10 grid grid-cols-3 gap-6">
        {[
          [Mic, "Voice", "Speak in Hindi, English, or Hinglish. The assistant asks, listens, and fills the Statement of Claim itself."],
          [MessageSquare, "WhatsApp", "The case continues on the platform MSMEs already use — documents, defenses, and updates, one message at a time."],
          [Globe, "Web Dashboard", "Every case tracked across the full 16-step ODR journey with AI analysis at each stage."],
        ].map(([Icon, title, desc]) => {
          const I = Icon as React.ComponentType<{ className?: string }>;
          return (
            <GlowBox key={title as string}>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-[#dcb877] to-[#a87f3d] shadow-lg shadow-[#c9a45c]/30">
                <I className="h-6 w-6 text-white" />
              </div>
              <p className="mt-4 text-xl font-semibold text-white">
                {title as string}
              </p>
              <p className="mt-2 text-[15px] leading-relaxed text-[#a3aec3]">
                {desc as string}
              </p>
            </GlowBox>
          );
        })}
      </div>

      <div className="mt-10 flex items-center gap-3 text-lg text-[#cbd4e2]">
        <CheckCircle2 className="h-5 w-5 text-green-400" />
        Three channels, one AI brain — every action aligned with the MSMED Act 2006
        <LivePill label="WORKING IN THE PoC" />
      </div>
    </div>
  );
}

function DemoMapSlide() {
  const steps = [
    [Mic, "Ravi (seller) files by voice", "4 questions answered aloud — the case creates itself"],
    [Phone, "Buyer's phone buzzes", "Section 18 intimation notice delivered on WhatsApp in seconds"],
    [UserCheck, "Gaurav (buyer) defends in chat", "States his side in one message — SOD recorded, seller notified"],
    [TrendingUp, "Dashboard advances live", "Filing → Intimation → SOD, with AI outcome prediction ready"],
  ];
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker>4 · Live Demonstration</Kicker>
      <SlideTitle>Watch a real dispute travel both directions</SlideTitle>

      <div className="mt-10 grid grid-cols-4 gap-4">
        {steps.map(([Icon, title, desc], i) => {
          const I = Icon as React.ComponentType<{ className?: string }>;
          return (
            <div key={title as string} className="relative">
              <GlowBox className="h-full">
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#c9a45c] text-sm font-bold text-white">
                    {i + 1}
                  </span>
                  <I className="h-6 w-6 text-[#e8cd9a]" />
                </div>
                <p className="mt-3 text-lg font-semibold leading-snug text-white">
                  {title as string}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-[#a3aec3]">
                  {desc as string}
                </p>
              </GlowBox>
              {i < 3 && (
                <ArrowRight className="absolute -right-4 top-1/2 z-10 h-5 w-5 -translate-y-1/2 text-[#d9b36a]" />
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-10 flex items-center justify-center gap-8 text-[#cbd4e2]">
        <span className="text-lg">
          Cast — <span className="font-semibold text-white">Ravi</span>: seller ·{" "}
          <span className="font-semibold text-white">Gaurav</span>: buyer ·{" "}
          <span className="font-semibold text-white">Assistant</span>:{" "}
          <span className="font-mono text-[#e8cd9a]">+91 70173 81728</span>
        </span>
        <LivePill label="LIVE ON REAL PHONES" />
      </div>
    </div>
  );
}

function DemoHighlightsSlide() {
  const moments = [
    [Mic, "A natural voice conversation", "The assistant asks in Hindi/Hinglish, listens, and responds — like talking to a helpful clerk"],
    [Layers, "The form fills itself", "Watch case fields populate on screen in real time as the seller speaks"],
    [MessageSquare, "Phones buzz across the room", "Intimation and follow-ups land on real WhatsApp numbers, live"],
    [TrendingUp, "The timeline moves on its own", "Filing → Intimation → Defense — the 16-step tracker advances as it happens"],
    [FileSearch, "AI reads the case like a lawyer", "Outcome prediction with statutory grounding and a suggested settlement range"],
    [FileSignature, "A settlement, drafted", "Section 16 interest computed and written into a ready agreement"],
  ];
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker>4 · Live Demonstration — Highlights</Kicker>
      <SlideTitle>Six moments to watch for</SlideTitle>

      <div className="mt-10 grid grid-cols-3 gap-5">
        {moments.map(([Icon, title, desc]) => {
          const I = Icon as React.ComponentType<{ className?: string }>;
          return (
            <GlowBox key={title as string}>
              <I className="h-7 w-7 text-[#d9b36a]" />
              <p className="mt-3 text-lg font-semibold leading-snug text-white">
                {title as string}
              </p>
              <p className="mt-1.5 text-sm leading-relaxed text-[#a3aec3]">
                {desc as string}
              </p>
            </GlowBox>
          );
        })}
      </div>
    </div>
  );
}

function TechTag({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-[#93a5c4]/20 bg-[#0b1120]/70 px-2 py-0.5 font-mono text-[10.5px] text-[#76839f]">
      {children}
    </span>
  );
}

function ArchitectureSlide() {
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker>2 · Solution Architecture</Kicker>
      <SlideTitle>One assistant listens, thinks in law, and acts</SlideTitle>

      <div className="mt-10 grid grid-cols-[1fr_auto_1.3fr_auto_1fr] items-stretch gap-4">
        {/* Users reach it */}
        <GlowBox>
          <p className="text-sm font-semibold uppercase tracking-wider text-[#76839f]">
            How sellers reach it
          </p>
          <div className="mt-3 space-y-2.5 text-lg text-white">
            <p className="flex items-center gap-2.5"><Mic className="h-5 w-5 text-[#d9b36a]" /> A phone conversation</p>
            <p className="flex items-center gap-2.5"><MessageSquare className="h-5 w-5 text-[#d9b36a]" /> A WhatsApp message</p>
            <p className="flex items-center gap-2.5"><Globe className="h-5 w-5 text-[#d9b36a]" /> A simple website</p>
          </div>
          <div className="mt-4 flex flex-wrap gap-1.5">
            <TechTag>Sarvam saarika (STT)</TechTag>
            <TechTag>Sarvam bulbul (TTS)</TechTag>
            <TechTag>Next.js</TechTag>
          </div>
        </GlowBox>

        <ArrowRight className="h-6 w-6 self-center text-[#d9b36a]" />

        {/* The brain */}
        <GlowBox className="border-[#c9a45c]/35 bg-[#c9a45c]/10">
          <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-[#e8cd9a]">
            <Bot className="h-4 w-4" /> The AI Assistant
          </p>
          <p className="mt-2 text-[15px] leading-relaxed text-[#cbd4e2]">
            One assistant understands the conversation and acts only through{" "}
            <span className="font-semibold text-white">
              14 approved legal actions
            </span>{" "}
            — file the case, notify the buyer, record the defense, predict the
            outcome, calculate interest, draft the settlement.
          </p>
          <p className="mt-2 text-[15px] text-[#cbd4e2]">
            The underlying AI model is{" "}
            <span className="font-semibold text-white">swappable</span> — the
            government can choose any model, Indian or open-source.
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <TechTag>LangChain agent</TechTag>
            <TechTag>DeepSeek LLM (API)</TechTag>
            <TechTag>FastAPI</TechTag>
          </div>
        </GlowBox>

        <ArrowRight className="h-6 w-6 self-center text-[#d9b36a]" />

        {/* Knowledge */}
        <GlowBox>
          <p className="text-sm font-semibold uppercase tracking-wider text-[#76839f]">
            What it thinks with
          </p>
          <div className="mt-3 space-y-2.5 text-lg text-white">
            <p className="flex items-center gap-2.5"><BookOpen className="h-5 w-5 text-[#d9b36a]" /> An indexed law library</p>
            <p className="flex items-center gap-2.5"><Database className="h-5 w-5 text-[#d9b36a]" /> Secure case records</p>
            <p className="flex items-center gap-2.5"><ShieldCheck className="h-5 w-5 text-[#d9b36a]" /> Answers quote the Act</p>
          </div>
          <div className="mt-4 flex flex-wrap gap-1.5">
            <TechTag>PostgreSQL</TechTag>
            <TechTag>Qdrant vector search</TechTag>
            <TechTag>OpenRouter embeddings</TechTag>
          </div>
        </GlowBox>
      </div>

      <p className="mt-10 text-center text-lg text-[#a3aec3]">
        The law library holds the MSMED Act 2006, MSEFC rules, the Mediation
        Act, and Supreme Court judgments — the assistant quotes the law, it
        never invents it
      </p>
    </div>
  );
}

function PipelineSlide() {
  const stages = [
    [Mic, "Voice collects the basics", "A short conversation — buyer, amount, what was supplied. No form ever appears."],
    [Zap, "Every answer saved instantly", "Call drops? Battery dies? Nothing is lost — the case holds everything said so far."],
    [Phone, "Case files, buyer notified", "The claim is registered and the buyer's Section 18 notice goes out on WhatsApp within seconds."],
    [MessageSquare, "The case lives on WhatsApp", "Remaining details, documents, status updates, the buyer's defense, negotiation — one familiar chat thread."],
  ];
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker>2 · Architecture — System Workflow</Kicker>
      <SlideTitle>From a voice call to a living WhatsApp case</SlideTitle>

      <div className="mt-10 grid grid-cols-4 gap-4">
        {stages.map(([Icon, title, desc], i) => {
          const I = Icon as React.ComponentType<{ className?: string }>;
          return (
            <div key={title as string} className="relative">
              <GlowBox className="h-full">
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#31405f] text-sm font-bold text-white">
                    {i + 1}
                  </span>
                  <I className="h-6 w-6 text-[#e8cd9a]" />
                </div>
                <p className="mt-3 text-lg font-semibold leading-snug text-white">
                  {title as string}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-[#a3aec3]">
                  {desc as string}
                </p>
              </GlowBox>
              {i < 3 && (
                <ArrowRight className="absolute -right-4 top-1/2 z-10 h-5 w-5 -translate-y-1/2 text-[#d9b36a]" />
              )}
            </div>
          );
        })}
      </div>

      <p className="mt-10 text-center text-xl text-[#cbd4e2]">
        One case, one thread —{" "}
        <span className="font-semibold text-white">
          the seller never repeats themselves and never fills a form
        </span>
      </p>
    </div>
  );
}

function JourneySlide() {
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker>2 · Architecture — ODR Workflow Coverage</Kicker>
      <SlideTitle>The Section 18 journey, working end to end</SlideTitle>

      <div className="mt-10 grid grid-cols-2 gap-6">
        <GlowBox>
          <p className="flex items-center gap-2 text-lg font-semibold text-white">
            <Zap className="h-5 w-5 text-[#d9b36a]" /> Steps 1–7 · AI-active
          </p>
          <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-[15px] text-[#cbd4e2]">
            {[
              "Registration (Udyam)",
              "Statement of Claim",
              "Buyer intimation",
              "Statement of Defense",
              "Pre-MSEFC settlement",
              "AI outcome prediction",
              "Unmanned negotiation",
              "Settlement drafting",
            ].map((s) => (
              <p key={s} className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-green-400" /> {s}
              </p>
            ))}
          </div>
        </GlowBox>

        <div className="space-y-4">
          <GlowBox className="border-[#c9a45c]/35 bg-[#c9a45c]/10">
            <p className="text-lg font-semibold text-white">
              💬 SOD filed inside WhatsApp chat
            </p>
            <p className="mt-1.5 text-[15px] leading-relaxed text-[#cbd4e2]">
              The buyer states their side in plain language — the agent records
              a structured defense (admit / partial / deny + amount) and
              notifies the seller. No forms, no login.
            </p>
          </GlowBox>
          <GlowBox className="border-[#c9a45c]/35 bg-[#c9a45c]/10">
            <p className="text-lg font-semibold text-white">
              ⏱️ Ex-parte auto-advance
            </p>
            <p className="mt-1.5 text-[15px] leading-relaxed text-[#cbd4e2]">
              Buyer silent past the statutory window? The case advances
              automatically with an ex-parte record —{" "}
              <span className="font-semibold text-white">
                a non-cooperating party can never stall justice
              </span>.
            </p>
          </GlowBox>
        </div>
      </div>

      <p className="mt-6 text-center text-lg text-[#a3aec3]">
        Steps 8–16 (MSEFC, conciliation, arbitration) tracked on the dashboard —
        humans decide, the platform keeps everyone informed
      </p>
      <p className="mt-3 text-center text-[15px] text-[#76839f]">
        PoC scope: exact document requirements, MSEFC formats, and state-level
        variations will be refined with the Ministry in Stage 1 — the
        architecture absorbs them without redesign
      </p>
    </div>
  );
}

function CapabilitiesSlide() {
  // Only what the live demo actually shows — nothing aspirational.
  const caps = [
    [Mic, "Voice-based case filing", "Speak in Hindi/English/Hinglish — the Statement of Claim fills itself, no form"],
    [MessageSquare, "The case lives on WhatsApp", "Buyer intimation, status updates, missing details, and the buyer's own defense — one chat thread for both parties"],
    [TrendingUp, "AI outcome prediction", "Probable resolution grounded in statutory provisions, with Section 16 interest computed"],
    [FileSignature, "Settlement drafted & delivered", "On mutual agreement, the formal agreement is generated and sent to both parties automatically"],
  ];
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker>1 · Overview — Alignment with the Use Case</Kicker>
      <SlideTitle>What you&apos;ll see working today</SlideTitle>

      <div className="mt-10 grid grid-cols-2 gap-5">
        {caps.map(([Icon, title, desc]) => {
          const I = Icon as React.ComponentType<{ className?: string }>;
          return (
            <GlowBox key={title as string}>
              <div className="flex items-start justify-between">
                <I className="h-7 w-7 text-[#d9b36a]" />
                <LivePill />
              </div>
              <p className="mt-3 text-xl font-semibold text-white">
                {title as string}
              </p>
              <p className="mt-2 text-[15px] leading-relaxed text-[#a3aec3]">
                {desc as string}
              </p>
            </GlowBox>
          );
        })}
      </div>
    </div>
  );
}

function DatasetsSlide() {
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker>3 · Datasets & Methodology</Kicker>
      <SlideTitle>Grounded in law, validated against real cases</SlideTitle>

      <div className="mt-10 grid grid-cols-2 gap-6">
        <GlowBox>
          <p className="flex items-center gap-2.5 text-lg font-semibold text-white">
            <Database className="h-5 w-5 shrink-0 text-[#d9b36a]" /> Datasets
          </p>
          <ul className="mt-4 space-y-3 text-[15px] leading-relaxed text-[#a3aec3]">
            <li>
              <span className="font-semibold text-white">Statutory corpus (indexed):</span>{" "}
              MSMED Act 2006, MSEFC rules & draft revisions, Mediation Act,
              Arbitration & Conciliation Act, Supreme Court MSME judgments —
              208 searchable sections from 8 documents
            </li>
            <li>
              <span className="font-semibold text-white">Case data (PoC):</span>{" "}
              synthetic and volunteer-filed disputes exercised across all three
              channels
            </li>
            <li>
              <span className="font-semibold text-white">Stage 1:</span>{" "}
              validation against AIKosh MSME-SAMADHAAN datasets, with published
              methodology
            </li>
          </ul>
        </GlowBox>

        <GlowBox>
          <p className="flex items-center gap-2.5 text-lg font-semibold text-white">
            <GitBranch className="h-5 w-5 shrink-0 text-[#d9b36a]" /> Methodology
          </p>
          <ul className="mt-4 space-y-3 text-[15px] leading-relaxed text-[#a3aec3]">
            <li>
              <span className="font-semibold text-white">Retrieval-grounded answers:</span>{" "}
              legal responses are retrieved from the indexed Acts and quoted —
              never generated from memory
            </li>
            <li>
              <span className="font-semibold text-white">Deterministic statutory math:</span>{" "}
              Section 16 compound interest is computed by formula, not
              estimated by AI
            </li>
            <li>
              <span className="font-semibold text-white">Tool-scoped agent:</span>{" "}
              every action flows through one of 14 approved, auditable legal
              actions with verified outcomes
            </li>
          </ul>
        </GlowBox>
      </div>
    </div>
  );
}

function ComplianceSlide() {
  const points = [
    [ShieldCheck, "Scoped tools, never raw data access", "The agent acts only through 14 audited tools — it cannot query the database freely or touch another user's case. By design, not by prompt."],
    [Users, "Humans own the judgment calls", "AI drives steps 1–7 (filing & facilitation); MSEFC, conciliation, and arbitration (8–16) stay entirely with human authorities."],
    [BookOpen, "Grounded, not generative law", "Every statutory answer is retrieved from indexed Act text — the model cites provisions, it doesn't invent them."],
    [FileSignature, "Verified, auditable actions", "Intimations and defenses are delivery-verified and timestamped; the agent may never claim an action it didn't complete."],
  ];
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker>3 · Methodology — Responsible AI · DPDP Act 2023</Kicker>
      <SlideTitle>Trustworthy by architecture</SlideTitle>

      <div className="mt-10 grid grid-cols-2 gap-5">
        {points.map(([Icon, title, desc]) => {
          const I = Icon as React.ComponentType<{ className?: string }>;
          return (
            <GlowBox key={title as string}>
              <p className="flex items-center gap-2.5 text-lg font-semibold text-white">
                <I className="h-5 w-5 shrink-0 text-[#d9b36a]" /> {title as string}
              </p>
              <p className="mt-2 text-[15px] leading-relaxed text-[#a3aec3]">
                {desc as string}
              </p>
            </GlowBox>
          );
        })}
      </div>

      <p className="mt-8 text-center text-[15px] text-[#76839f]">
        Stage 2 hardening: row-level security for per-tenant isolation · PII
        minimization · security audit per IndiaAI requirements
      </p>
    </div>
  );
}

function ResilienceSlide() {
  const items = [
    [GitBranch, "Swappable AI — proven, not promised", "Our AI provider retired a model mid-build week. We switched to its successor the same day with a one-line change and zero downtime."],
    [MessageSquare, "Survives platform shifts", "WhatsApp changed how it identifies users this year, silently breaking most bots — ODRMitra handles the change transparently."],
    [Zap, "Zero data loss", "Every answer is saved the moment it's given. A dropped call or dead battery never costs the filer their progress."],
    [Users, "Two-sided by design", "The same person can be seller in one case and buyer in another — the agent always knows which hat you're wearing."],
  ];
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker>3 · Methodology — Engineering Robustness</Kicker>
      <SlideTitle>Built to survive the real world</SlideTitle>

      <div className="mt-10 grid grid-cols-2 gap-5">
        {items.map(([Icon, title, desc]) => {
          const I = Icon as React.ComponentType<{ className?: string }>;
          return (
            <GlowBox key={title as string}>
              <p className="flex items-center gap-2.5 text-lg font-semibold text-white">
                <I className="h-5 w-5 shrink-0 text-[#d9b36a]" /> {title as string}
              </p>
              <p className="mt-2 text-[15px] leading-relaxed text-[#a3aec3]">
                {desc as string}
              </p>
            </GlowBox>
          );
        })}
      </div>
    </div>
  );
}

function RoadmapSlide() {
  return (
    <div className="flex h-full flex-col justify-center">
      <Kicker>Roadmap</Kicker>
      <SlideTitle>From working PoC to national scale</SlideTitle>

      <div className="mt-10 grid grid-cols-3 gap-5">
        <GlowBox className="border-green-500/30">
          <p className="text-sm font-bold uppercase tracking-wider text-green-400">
            Today — Live PoC
          </p>
          <ul className="mt-3 space-y-2 text-[15px] text-[#cbd4e2]">
            <li>✓ Voice + WhatsApp + web filing</li>
            <li>✓ Intimation, SOD, ex-parte flow</li>
            <li>✓ DGP prediction & settlement drafts</li>
            <li>✓ Deployed & publicly reachable</li>
          </ul>
        </GlowBox>
        <GlowBox className="border-[#c9a45c]/40">
          <p className="text-sm font-bold uppercase tracking-wider text-[#d9b36a]">
            Stage 1 — Pilot
          </p>
          <ul className="mt-3 space-y-2 text-[15px] text-[#cbd4e2]">
            <li>· Validate on AIKosh SAMADHAAN data</li>
            <li>· Toll-free calling (Twilio)</li>
            <li>· 10+ Indian languages via Sarvam</li>
            <li>· MSEFC pilot across states</li>
          </ul>
        </GlowBox>
        <GlowBox className="border-blue-500/30">
          <p className="text-sm font-bold uppercase tracking-wider text-blue-400">
            Stage 2 — Scale
          </p>
          <ul className="mt-3 space-y-2 text-[15px] text-[#cbd4e2]">
            <li>· Integration with MSME ODR portal</li>
            <li>· Security audit + RLS hardening</li>
            <li>· Streaming voice (~4s turns)</li>
            <li>· 63M+ MSMEs addressable</li>
          </ul>
        </GlowBox>
      </div>

    </div>
  );
}

function ClosingSlide() {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-[#dcb877] to-[#a87f3d] shadow-2xl shadow-[#c9a45c]/40">
        <Scale className="h-8 w-8 text-white" />
      </div>

      <p className="mt-12 max-w-4xl text-[40px] font-medium leading-snug text-white">
        “Every MSME seller in India should be able to file a payment dispute by{" "}
        <span className="bg-gradient-to-r from-[#eedbaa] to-[#c9a45c] bg-clip-text text-transparent">
          simply making a phone call
        </span>.”
      </p>

      <div className="mt-16 flex flex-col items-center gap-4">
        <LivePill label="TRY IT NOW" />
        <a
          href={`https://${LIVE_URL}`}
          target="_blank"
          rel="noopener noreferrer"
          className="font-mono text-2xl text-[#e8cd9a] underline decoration-[#c9a45c]/50 underline-offset-8 transition-colors hover:text-white"
        >
          https://{LIVE_URL}
        </a>
      </div>
    </div>
  );
}

const SLIDES: React.ComponentType[] = [
  // Ordered to mirror the PMU's requested structure:
  // 1 Overview & use-case alignment · 2 Architecture & workflow ·
  // 3 Datasets & methodology · 4 Live demonstration
  TitleSlide,
  ProblemSlide,
  SolutionSlide,
  CapabilitiesSlide,
  ArchitectureSlide,
  PipelineSlide,
  JourneySlide,
  DatasetsSlide,
  ComplianceSlide,
  ResilienceSlide,
  RoadmapSlide,
  DemoMapSlide,
  DemoHighlightsSlide,
  ClosingSlide,
];

/* ── Deck shell ──────────────────────────────────────────────────── */

const W = 1280;
const H = 720;

export default function DeckPage() {
  const [idx, setIdx] = useState(0);
  const [scale, setScale] = useState(1);

  const next = useCallback(
    () => setIdx((i) => Math.min(i + 1, SLIDES.length - 1)),
    []
  );
  const prev = useCallback(() => setIdx((i) => Math.max(i - 1, 0)), []);

  useEffect(() => {
    const fit = () =>
      setScale(Math.min(window.innerWidth / W, window.innerHeight / H));
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (["ArrowRight", "PageDown", " "].includes(e.key)) next();
      else if (["ArrowLeft", "PageUp"].includes(e.key)) prev();
      else if (e.key === "Home") setIdx(0);
      else if (e.key === "End") setIdx(SLIDES.length - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [next, prev]);

  return (
    <div className="deck-viewport fixed inset-0 flex items-center justify-center overflow-hidden bg-[#04070d]">
      {/* Edge click zones (screen only) */}
      <button
        aria-label="Previous slide"
        onClick={prev}
        className="nav-ui absolute inset-y-0 left-0 z-20 w-1/5 cursor-w-resize"
      />
      <button
        aria-label="Next slide"
        onClick={next}
        className="nav-ui absolute inset-y-0 right-0 z-20 w-1/5 cursor-e-resize"
      />

      {/* Stage */}
      <div
        className="deck-stage relative shrink-0"
        style={{ width: W, height: H, transform: `scale(${scale})` }}
      >
        {SLIDES.map((Slide, i) => (
          <section
            key={i}
            className={`slide absolute inset-0 overflow-hidden bg-gradient-to-br from-[#141c2e] via-[#0d1424] to-[#070b15] px-20 py-14 transition-all duration-500 ${
              i === idx
                ? "z-10 translate-x-0 opacity-100"
                : i < idx
                ? "-translate-x-8 opacity-0"
                : "translate-x-8 opacity-0"
            }`}
          >
            {/* ambient glow */}
            <div
              className="pointer-events-none absolute -right-40 -top-40 h-[500px] w-[500px] rounded-full opacity-15"
              style={{ background: "radial-gradient(circle, #c9a45c, transparent 70%)" }}
            />
            <div className="relative h-full">
              <Slide />
            </div>
            {/* footer brand */}
            <div className="absolute bottom-6 left-20 flex items-center gap-2 text-xs text-[#535f78]">
              <Scale className="h-3.5 w-3.5 text-[#c9a45c]/70" />
              ODRMitra · IndiaAI Innovation Challenge 2026
            </div>
            <div className="absolute bottom-6 right-20 text-xs text-[#535f78]">
              {i + 1} / {SLIDES.length}
            </div>
          </section>
        ))}
      </div>

      {/* Controls */}
      <div className="nav-ui absolute bottom-5 left-1/2 z-30 flex -translate-x-1/2 items-center gap-3 rounded-full border border-[#93a5c4]/20 bg-[#0b1120]/80 px-4 py-2 backdrop-blur">
        <button onClick={prev} className="text-[#a3aec3] transition-colors hover:text-white">
          <ChevronLeft className="h-5 w-5" />
        </button>
        <span className="min-w-[3.5rem] text-center text-sm font-medium text-[#cbd4e2]">
          {idx + 1} / {SLIDES.length}
        </span>
        <button onClick={next} className="text-[#a3aec3] transition-colors hover:text-white">
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>

      {/* Print: one page per slide, nav hidden, slides un-stacked */}
      <style jsx global>{`
        @media print {
          @page {
            size: 1280px 720px;
            margin: 0;
          }
          body {
            background: #0b1627;
          }
          .deck-viewport {
            position: static !important;
            display: block !important;
            overflow: visible !important;
            height: auto !important;
          }
          .deck-stage {
            transform: none !important;
            width: ${W}px !important;
            height: auto !important;
          }
          .slide {
            position: relative !important;
            opacity: 1 !important;
            transform: none !important;
            width: ${W}px;
            height: ${H}px;
            break-after: page;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
          .nav-ui {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
}
