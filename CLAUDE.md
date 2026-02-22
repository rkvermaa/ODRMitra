# CLAUDE.md — ODRMitra Project

## What is ODRMitra?

**ODRMitra** (Hindi: "ODR Friend/Companion") is an AI-enabled virtual negotiation assistant for resolving MSME delayed payment disputes through Online Dispute Resolution (ODR). Built for the **IndiaAI Innovation Challenge 2026** (Problem Statement 1, Ministry of MSME).

MSMEs face delayed payments from buyers — conventional dispute resolution (conciliation, arbitration) is slow and expensive. ODRMitra provides a digital-first, AI-powered alternative: voice/chat-based case filing, automated document analysis, dispute classification, outcome prediction, guided negotiation, and settlement drafting — all aligned with the MSMED Act 2006.

## Competition Context

- **IndiaAI Innovation Challenge 2026** — Ministry of MSME + MeitY
- **Problem Statement 1**: AI-Enabled Virtual Negotiation Assistance
- **Stage 1**: Build working PoC, submit by **22 Feb 2026**
- **Stage 1 Prize**: INR 25 Lakhs (up to 3 teams shortlisted)
- **Stage 2 Prize**: INR 1 Crore (work contract for 2 years)
- **Compliance**: DPDP Act 2023, Responsible AI principles, cybersecurity guidelines

## ODR Process Flow (16 Steps)

AI-active stages (1-7) where ODRMitra provides assistance:
1. **Registration** — Seller signs up via Udyam Registration Number
2. **Filing of SOC** — Seller files Statement of Claim (voice/chat + doc upload)
3. **Intimation** — Buyer notified via WhatsApp/Telegram/SMS/Email
4. **Filing of SOD** — Buyer files Statement of Defense
5. **Pre-MSEFC Stage** — Parties try mutual settlement
6. **Digital Guided Pathway (DGP)** — AI predicts outcome to facilitate settlement
7. **Unmanned Negotiation** — AI-guided negotiation via virtual room

AI-passive stages (8-16) — status tracking only, humans handle:
8-16. MSEFC Stage → Scrutiny → Notice → Conciliation → Arbitration → Resolution

See: `.claude/project-docs/odr-workflow.md` for full details.

## 6 Core AI Capabilities

1. **Voice-based case filing** — Speech-to-text (Web Speech API) → auto-populate SOC/SOD
2. **Document analysis** — Extract entities, amounts, dates from invoices/POs/contracts via LLM
3. **Dispute classification** — Classify sub-category with confidence score using MSMED Act context
4. **Missing document detection** — Compare uploaded docs against required docs per category
5. **Outcome prediction (DGP)** — Predict resolution based on case details + statutory provisions
6. **AI-guided negotiation + settlement** — Chat-based negotiation with interest calculations → auto-draft settlement agreement

## Architecture

```
                    ┌─── Next.js Frontend (Web)
User (Voice/Chat) ──┤
                    ├─── WhatsApp (Baileys)
                    └─── Telegram Bot
                              │
                              ▼
                     FastAPI Backend → DeepSeek LLM
                         │                │
                    Skills System    Tool Registry
                         │                │
                    ┌────┴────┐     ┌─────┴──────┐
                    │ SKILL.md │     │  8 ODR Tools │
                    │  files   │     │             │
                    └─────────┘     └─────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         PostgreSQL        Redis          Qdrant
      (disputes, users,  (session      (legal knowledge
       sessions, docs)    cache)        RAG + embeddings)
```

## Skill-Based Agent Architecture

Agent discovers and activates skills based on user's query. Each skill has its own system prompt + allowed tools via `SKILL.md` files.

| Skill | Workflow Steps | Tools |
|---|---|---|
| `registration` | Step 1 | search_knowledge, get_statutory_provision |
| `case-filing` | Steps 2, 4 | classify_dispute, analyze_document, check_missing_docs, search_knowledge |
| `digital-guided-pathway` | Steps 5, 6 | predict_outcome, calculate_interest, get_statutory_provision, search_knowledge |
| `negotiation` | Step 7 | calculate_interest, draft_settlement, predict_outcome, search_knowledge |
| `legal-info` | Any step | search_knowledge, get_statutory_provision |

## 8 Agent Tools

1. `classify_dispute` — Classify dispute sub-category via LLM + MSMED Act
2. `analyze_document` — Extract entities/amounts/dates from docs
3. `check_missing_docs` — Compare uploaded vs required documents
4. `predict_outcome` — Predict resolution outcome with statutory basis
5. `draft_settlement` — Generate settlement agreement markdown
6. `calculate_interest` — Section 16 compound interest (3x bank rate)
7. `get_statutory_provision` — Look up MSMED Act sections
8. `search_knowledge` — RAG search on legal knowledge base

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | FastAPI (async) | High-performance Python API |
| Frontend | Next.js 16 + React 19 | SSR, modern UI |
| Database | PostgreSQL + SQLAlchemy (async) | Relational data, dispute records |
| Cache | Redis | Session cache, fast reads |
| Vector DB | Qdrant | Legal knowledge RAG |
| LLM | DeepSeek (via LangChain) | Cost-effective, OpenAI-compatible |
| Embeddings | sentence-transformers (local) | No API cost for embeddings |
| Auth | JWT (python-jose) | Stateless auth |
| Config | Dynaconf | Multi-env config |
| State (FE) | Zustand | Lightweight state management |
| Voice | Web Speech API (browser) | Free, multilingual, zero cost |
| Channels | Baileys (WhatsApp) + Telegram Bot API | Multi-channel access |

## Project Structure

```
ODRMitra/
├── CLAUDE.md                            # This file
├── .claude/
│   ├── project-docs/
│   │   ├── guidelines.pdf               # IndiaAI challenge guidelines
│   │   ├── implementation-plan.md       # Implementation plan
│   │   └── odr-workflow.md              # 16-step ODR process flow
│   └── assets/                          # Reference screenshots
├── backend/
│   ├── config/
│   │   ├── settings.toml                # App configuration
│   │   └── .secrets.toml                # API keys (gitignored)
│   ├── migrations/versions/             # Alembic migrations
│   ├── src/
│   │   ├── main.py                      # FastAPI entry point
│   │   ├── config/settings.py           # Dynaconf setup
│   │   ├── core/                        # exceptions, logging, security (JWT)
│   │   ├── db/
│   │   │   ├── base.py                  # SQLAlchemy async engine
│   │   │   ├── session.py               # Session factory
│   │   │   └── models/                  # User, Dispute, Document, Session, Message, etc.
│   │   ├── llm/client.py               # LangChain LLM client (DeepSeek)
│   │   ├── agent/
│   │   │   ├── engine.py               # ReAct loop (max 5 iterations)
│   │   │   ├── context/loader.py       # Load dispute context + RAG
│   │   │   └── prompt/                 # Base prompt + builder
│   │   ├── skills/
│   │   │   ├── loader.py               # SKILL.md parser (from reference)
│   │   │   ├── manager.py              # Skill activation
│   │   │   ├── sync.py                 # Sync skills to DB
│   │   │   └── builtin/               # 5 ODR skills (SKILL.md + tools/)
│   │   │       ├── registration/
│   │   │       ├── case-filing/
│   │   │       ├── digital-guided-pathway/
│   │   │       ├── negotiation/
│   │   │       └── legal-info/
│   │   ├── tools/
│   │   │   ├── base.py                 # BaseTool ABC
│   │   │   ├── registry.py             # Tool registry
│   │   │   └── core/                   # Core tools (search_knowledge, etc.)
│   │   ├── rag/                        # Chunker, Qdrant search, indexer
│   │   ├── chat/                       # Session management (Redis + PostgreSQL)
│   │   ├── api/routes/
│   │   │   ├── auth.py                 # Registration, login, JWT
│   │   │   ├── chat.py                 # Chat endpoint
│   │   │   ├── disputes.py             # Dispute CRUD
│   │   │   ├── documents.py            # Document upload/analysis
│   │   │   ├── negotiation.py          # Negotiation rounds
│   │   │   ├── settlement.py           # Settlement drafting
│   │   │   └── channel/               # WhatsApp + Telegram (from reference)
│   │   └── data/                       # Static legal data (MSMED Act, templates)
│   └── pyproject.toml
├── frontend/
│   ├── src/app/
│   │   ├── (auth)/login/               # Login/Register
│   │   └── (dashboard)/
│   │       ├── dashboard/              # Stats + recent cases
│   │       ├── file-case/              # SOC filing (voice + chat + form)
│   │       ├── file-defense/           # SOD filing
│   │       ├── disputes/               # Case list
│   │       ├── disputes/[id]/          # Case detail + status timeline
│   │       ├── dgp/[id]/              # Digital Guided Pathway (outcome prediction)
│   │       ├── negotiate/[id]/         # Unmanned Negotiation room
│   │       ├── settlement/[id]/        # Settlement preview + accept/reject
│   │       └── knowledge/              # MSMED Act browser
│   ├── src/components/                 # Chat, Voice, UI components
│   ├── src/lib/api.ts                  # API client
│   └── src/store/                      # Zustand stores (auth, disputes)
└── docker-compose.yml                  # PostgreSQL + Redis + Qdrant
```

## Database Models

| Model | Purpose |
|---|---|
| **User** | Claimant/respondent/conciliator with Udyam registration, org details |
| **Skill** | Skill definitions synced from SKILL.md files |
| **UserSkill** | Many-to-many: which skills are enabled per user |
| **Dispute** | Case with amounts, dates, status (maps to 16-step workflow), AI analysis results |
| **DisputeDocument** | Uploaded docs with analysis status/results |
| **Session** | Chat session linked to user + dispute + channel (web/whatsapp/telegram) |
| **Message** | Chat messages (user/assistant/system/tool_call/tool_result) |
| **NegotiationRound** | Offers, counter-offers, AI suggestions per round |
| **SettlementAgreement** | Generated agreement with terms and payment schedule |

## Frontend Pages → Workflow Mapping

| Page | Workflow Steps | Shows |
|---|---|---|
| Registration/Login | Step 1 | Udyam-based signup, role selection |
| File Case (SOC) | Step 2 | Split-screen: form + voice/chat, doc upload |
| Dashboard | All steps | Case list, status tracker, stats |
| Case Detail | Steps 2-16 | Party info, docs, AI analysis, status timeline |
| File Defense (SOD) | Step 4 | Same as SOC but for respondent |
| DGP / Outcome | Steps 5-6 | AI prediction, statutory interest, settlement suggestion |
| Negotiation Room | Step 7 | Chat + offers panel + interest calculator |
| Settlement | After 6 or 7 | Rendered agreement, accept/reject, download |
| Knowledge Base | Any | Browsable MSMED Act, FAQs |

## Reference Project

Adapted from `assistant-marketpalce/` (in parent directory). Key adaptations:
- Multi-tenant marketplace → single-purpose MSME ODR platform
- Tenant model → User model (claimant/respondent roles)
- Generic skills → 5 ODR-specific skills (registration, case-filing, DGP, negotiation, legal-info)
- Keep WhatsApp (Baileys) + Telegram integration
- Sessions linked to disputes via `dispute_id`

## Branding

- **Primary**: Navy `#1a365d`
- **Accent**: Saffron `#f97316`
- **Background**: White
- **Name**: ODRMitra (ओडीआर मित्र)

## Development Rules

### General
- Do NOT edit files without explicit permission
- Do NOT create/delete/rename files unless instructed
- Ask before structural changes
- Follow existing code patterns from the reference project
- Type hints mandatory on all function signatures

### Documentation
- Project docs live in `.claude/project-docs/`
- CLAUDE.md stays at project root
- Update docs when structure changes

### Code Quality
- No dead code — remove unused imports/functions immediately
- Keep functions small and focused
- Docstrings on all public functions/classes
- No `.env`, API keys, or `__pycache__` in git

### Git
- Clear, descriptive commit messages
- One logical change per commit
- Never commit secrets
