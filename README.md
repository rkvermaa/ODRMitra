# ODRMitra — ओडीआर मित्र

**AI-Enabled Virtual Negotiation Assistant for MSME Delayed Payment Disputes**

Built for the [IndiaAI Innovation Challenge 2026](https://indiaai.gov.in) — Ministry of MSME + MeitY (Problem Statement 1)

---

## The Problem

India has **63 million+ registered MSMEs** — the backbone of the economy. Yet every year, over **₹10 lakh crore** remains stuck in delayed payments. Less than **1% of eligible MSMEs** file disputes because:

- Complex legal procedures
- English-only portals (language barrier)
- Form-heavy processes
- Resolution takes 18-24 months in court

## The Solution

**One phone call.** An MSME seller can file a payment dispute by simply making a voice call — in Hindi, English, or Hinglish. ODRMitra's AI agent collects case details via voice, creates the dispute, and sends a legal intimation notice to the buyer via WhatsApp — all under the MSMED Act 2006.

**5 minutes** to file a case. **10x faster** than traditional forms. **Any phone works** — no smartphone required.

---

## Architecture

```
                    ┌─── Next.js Frontend (Web + Voice)
User (Voice/Chat) ──┤
                    └─── WhatsApp (Baileys)
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
      (disputes, users)  (session cache) (legal RAG)
```

## 6 Core AI Capabilities

1. **Voice-based case filing** — Speech-to-text → auto-populate Statement of Claim
2. **Document analysis** — Extract entities, amounts, dates from invoices/POs
3. **Dispute classification** — Classify sub-category with confidence score
4. **Missing document detection** — Compare uploaded vs required documents
5. **Outcome prediction (DGP)** — Predict resolution based on case details + statutory provisions
6. **AI-guided negotiation + settlement** — Chat-based negotiation with auto-drafted settlement agreements

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.12, async) |
| Frontend | Next.js 15 + React 19 + Tailwind CSS 4 |
| Database | PostgreSQL + SQLAlchemy (async) |
| Cache | Redis |
| Vector DB | Qdrant (legal knowledge RAG) |
| LLM | DeepSeek (model-agnostic, OpenAI-compatible) |
| Voice | Sarvam AI (STT/TTS) + Web Speech API |
| WhatsApp | Baileys (open-source WhatsApp Web API) |
| Auth | JWT (role-based access) |
| Config | Dynaconf (multi-environment) |

---

## Prerequisites

- **Python 3.12+**
- **Node.js 18+** (for frontend and baileys-service)
- **PostgreSQL 15+**
- **Redis 7+**
- **Qdrant** (vector database, optional for RAG)

### API Keys Required

| Service | Purpose | Get it from |
|---|---|---|
| DeepSeek | LLM for agent reasoning | [platform.deepseek.com](https://platform.deepseek.com) |
| Sarvam AI | Voice STT/TTS (Indian languages) | [sarvam.ai](https://www.sarvam.ai) |
| LlamaParse | Document parsing (PDF/images) | [cloud.llamaindex.ai](https://cloud.llamaindex.ai) |
| Cloudinary | Document storage | [cloudinary.com](https://cloudinary.com) |

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/rkvermaa/ODRMitra.git
cd ODRMitra
```

### 2. Start infrastructure services

**Option A: Using Docker (recommended)**

```bash
docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=odrmitra postgres:15
docker run -d --name redis -p 6379:6379 redis:7
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest
```

**Option B: Install natively** — Install PostgreSQL, Redis, and Qdrant on your system.

### 3. Backend Setup

```bash
cd backend

# Create virtual environment (using uv — recommended)
uv venv
source .venv/bin/activate   # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
uv sync
# or: pip install -e .

# Configure secrets
cp config/.secrets.toml.example config/.secrets.toml
# Edit config/.secrets.toml with your API keys and database credentials
```

**Edit `backend/config/.secrets.toml`:**

```toml
[default]
database_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/odrmitra"
redis_url = "redis://localhost:6379/0"
jwt_secret = "your-random-secret-key-here"
deepseek_api_key = "sk-your-deepseek-api-key"
llama_cloud_api_key = "llx-your-llamaparse-key"
cloudinary_cloud_name = "your-cloud-name"
cloudinary_api_key = "your-api-key"
cloudinary_api_secret = "your-api-secret"
sarvam_api_key = "sk_your_sarvam_api_key"
```

**Run database migrations:**

```bash
alembic upgrade head
```

**Seed demo data (optional):**

```bash
python scripts/seed_demo.py
```

This creates demo users including:
| Name | Mobile | Role |
|---|---|---|
| Rajesh Kumar | 7409210692 | Claimant (Seller) |
| Priya Sharma | 9876543211 | Claimant (Seller) |
| Vikram Singh | 9876543220 | Respondent (Buyer) |
| Admin User | 9876543200 | Admin |

**Start the backend server:**

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be running at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be running at `http://localhost:3000`.

### 5. Baileys WhatsApp Service (optional — for WhatsApp channel)

```bash
cd baileys-service

# Install dependencies
npm install

# Start the service
npm run dev
```

WhatsApp service runs at `http://localhost:3001`. On first start, scan the QR code with WhatsApp to authenticate.

### 6. Legal Documents for RAG (optional — for legal knowledge search)

Create an `odr-docs/rag-index/` folder at the project root and place your legal PDFs there:

```
ODRMitra/
└── odr-docs/
    └── rag-index/
        ├── MSMED2006act.pdf
        ├── MSEFC.pdf
        ├── Mediation Act.pdf
        └── ... (any MSME/ODR related PDFs)
```

These documents are used for RAG-based legal knowledge search. You can download them from official government sources:
- [MSMED Act 2006](https://msme.gov.in) — The core statute for MSME delayed payments
- [MSEFC Rules](https://msme.gov.in) — Facilitation Council rules
- [Arbitration & Conciliation Act](https://legislative.gov.in) — A&C Act reference

Then index them into Qdrant:

```bash
cd backend
python -m src.rag.indexer
```

---

## Usage

### Login

1. Open `http://localhost:3000` in your browser
2. Enter a demo user's mobile number (e.g., `7409210692` for Rajesh Kumar)
3. OTP is auto-verified in development mode

### File a Case (Voice)

1. Click **"File Case"** from the dashboard
2. Select **"New Complaint"** → Click **"Start Voice Call"**
3. Speak naturally in Hindi/English — the AI agent will:
   - Verify your identity
   - Collect case details (buyer name, company, mobile, goods/services, amount)
   - Extract structured fields in real-time
4. After the call ends, the case is automatically created
5. WhatsApp notifications are sent to both seller and buyer

### File a Case (Chat)

1. Click **"File Case"** → Use the chat interface
2. The AI agent guides you through the same process via text

### Check Case Status

1. Go to **"My Disputes"** from the dashboard
2. Click on any case to see the 16-step progress timeline
3. View AI analysis, documents, and party details

### Digital Guided Pathway (DGP)

1. Open a filed case → Click **"AI Analysis"**
2. View outcome prediction with statutory basis and probability scores

### Negotiation

1. Open a case in DGP/Negotiation stage
2. Use the AI-guided negotiation room with interest calculations

---

## Project Structure

```
ODRMitra/
├── backend/
│   ├── config/
│   │   ├── settings.toml          # App configuration
│   │   └── .secrets.toml          # API keys (gitignored)
│   ├── migrations/                # Alembic DB migrations
│   ├── scripts/
│   │   └── seed_demo.py           # Demo data seeder
│   ├── src/
│   │   ├── main.py                # FastAPI entry point
│   │   ├── agent/                 # ReAct agent engine + prompts
│   │   ├── api/routes/            # REST API endpoints
│   │   ├── chat/                  # Chat session management
│   │   ├── db/models/             # SQLAlchemy models
│   │   ├── llm/                   # LLM client (DeepSeek)
│   │   ├── rag/                   # RAG pipeline (Qdrant)
│   │   ├── skills/builtin/        # 5 ODR skills (SKILL.md)
│   │   ├── tasks/                 # Background task dispatcher
│   │   └── tools/                 # 8 agent tools
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                   # Next.js pages
│   │   ├── components/            # React components
│   │   ├── lib/api.ts             # API client
│   │   └── store/                 # Zustand state
│   ├── package.json
│   └── tailwind.config.ts
├── baileys-service/               # WhatsApp integration
│   ├── src/index.js               # Express + Baileys server
│   └── package.json
├── CLAUDE.md                      # Detailed project documentation
└── README.md                      # This file
```

## ODR Process Flow (16 Steps)

ODRMitra covers the complete MSME dispute lifecycle:

| Phase | Steps | AI Role |
|---|---|---|
| **Filing** | 1. Registration → 2. Statement of Claim → 3. Intimation | Active — voice filing, doc analysis, auto-intimation |
| **Response** | 4. Statement of Defense → 5. Pre-MSEFC | Active — guided defense, settlement suggestions |
| **Resolution** | 6. Digital Guided Pathway → 7. Unmanned Negotiation | Active — outcome prediction, AI-guided negotiation |
| **Formal** | 8-16. MSEFC → Conciliation → Arbitration → Resolution | Passive — status tracking |

---

## Environment Variables

All sensitive configuration goes in `backend/config/.secrets.toml` (Dynaconf format).

| Variable | Required | Description |
|---|---|---|
| `database_url` | Yes | PostgreSQL connection string |
| `redis_url` | Yes | Redis connection string |
| `jwt_secret` | Yes | JWT signing secret |
| `deepseek_api_key` | Yes | DeepSeek LLM API key |
| `sarvam_api_key` | Yes | Sarvam AI voice API key |
| `llama_cloud_api_key` | Optional | LlamaParse document parsing |
| `cloudinary_*` | Optional | Document cloud storage |

---

## Compliance

- **DPDP Act 2023** — Digital Personal Data Protection compliant
- **NITI Aayog AI Principles** — Responsible AI, bias mitigation, explainability
- **IT Act 2000** — Information Technology Act compliance
- **100% Data Residency** — All data stored on Indian servers
- **Government Cybersecurity Guidelines** — End-to-end encryption, audit logging

---

## Team

Built by a team with **13+ years** of combined government and GenAI experience:

- **AI/ML Engineer** (Team Lead) — IIT Roorkee, 6 years govt (BSNL) + ML deployment
- **Full Stack Developer** (Technical Lead) — Next.js, FastAPI, Docker
- **Domain Expert** (Legal Research) — MSMED Act, MSEFC procedures, MSME insights

---

## License

This project is built for the IndiaAI Innovation Challenge 2026. All rights reserved.

---

*ODRMitra — "Your AI companion for MSME justice"*
