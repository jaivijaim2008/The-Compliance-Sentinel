# 🛡️ AI Compliance Copilot

An AI-powered contract analysis copilot that detects compliance risks, provides simplified explanations, and offers an executive summary and risk heatmap. It features a multi-agent debate system, an AI Fix Agent, and a full compliance dashboard.

**Live Demo:** [https://414df58ad0824d7a872680dc829a20d1.vercel.app/](https://414df58ad0824d7a872680dc829a20d1.vercel.app/)

---

## ✨ Features

- **PDF Contract Upload** — Upload any contract PDF for instant AI-powered analysis
- **Multi-Agent Risk Analysis** — Four specialized AI agents analyze different risk dimensions:
  - 🏛️ **Legal Agent** — Identifies termination clauses, liability limits, and legal risks
  - 🔒 **Privacy Agent** — Detects GDPR and data protection risks
  - 💰 **Finance Agent** — Flags financial risks in fees, payment terms, and obligations
  - 🛡️ **Security Agent** — Uncovers cybersecurity and data security concerns
- **AI Debate System** — Agents discuss conflicting clauses to reach a balanced, well-reasoned verdict through a moderated debate
- **Auto-Fix Risky Clauses** — The Fix Agent automatically rewrites risky clauses to be more fair and balanced, with explanations for each change
- **Compliance Dashboard** — Visual overview of overall compliance score, risk breakdown, and agent insights
- **Overall Risk Score** — Aggregated risk assessment with a percentage score and risk level indicator

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│  React 18 + TypeScript + Vite + MUI v7           │
│  Redux Toolkit · React Router v7                 │
└──────────────────────┬──────────────────────────┘
                       │ POST /api/analyze/upload
                       ▼
┌─────────────────────────────────────────────────┐
│                Backend (FastAPI)                  │
│  PDF Text Extraction (PyPDF2)                    │
│  ┌─────────────────────────────────────────────┐ │
│  │  Multi-Agent Pipeline                       │ │
│  │  Legal Agent ──┐                            │ │
│  │  Privacy Agent ├──► Debate Moderator ──► Fix │ │
│  │  Finance Agent ─┤                            │ │
│  │  Security Agent─┘                            │ │
│  └─────────────────────────────────────────────┘ │
│  LLM: Gemini 1.5 Flash (primary)                │
│       Groq Llama 3.3 70B (fallback)             │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

- Node.js (v18+)
- Python 3.10+
- A Google Gemini API key or Groq API key

### Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### Installation

```bash
# Install frontend dependencies
cd frontend
npm install

# Install backend dependencies
cd ../backend
pip install -r ../requirements.txt
```

### Running the App

```bash
# Start the frontend
cd frontend
npm run dev

# Start the backend (in a separate terminal)
cd backend
python main.py
```

The app will be available at `http://localhost:5173` (Vite dev server).

---

## 📁 Project Structure

```
├── frontend/                  # React 18 + TypeScript + Vite frontend
│   ├── src/
│   │   ├── components/        # Reusable UI components (PixelBlast, etc.)
│   │   ├── pages/             # File-based routes
│   │   ├── shared/            # State management, hooks, theme
│   │   │   ├── state/         # Redux store & slices
│   │   │   └── styles/        # Theme tokens (useClaudeTokens)
│   │   └── app/               # App shell, layout, routing
│   ├── package.json
│   └── vite.config.ts
├── backend/                   # FastAPI backend
│   ├── apps/
│   │   ├── analyze/           # Contract analysis endpoint
│   │   └── health/            # Health check endpoint
│   ├── config/                # SubApp framework
│   ├── main.py                # FastAPI app entry point
│   └── pyproject.toml
├── src/                       # Legacy/root-level app entry
├── meta.json                  # App metadata
├── requirements.txt           # Python dependencies
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Vite 6 |
| **UI Library** | MUI (Material UI) v7 |
| **State** | Redux Toolkit |
| **Routing** | React Router v7 (file-based) |
| **Animation** | Framer Motion |
| **Backend** | FastAPI, Python 3 |
| **PDF Parsing** | PyPDF2 |
| **AI (Primary)** | Google Gemini 1.5 Flash |
| **AI (Fallback)** | Groq Llama 3.3 70B Versatile |
| **Deployment** | Vercel (frontend) |

---

## 🔑 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/analyze/upload` | Upload a PDF contract for multi-agent analysis |
| `GET` | `/api/health/check` | Health check endpoint |

---

## 🤖 How the Multi-Agent System Works

1. **Upload** — User uploads a contract PDF
2. **Extraction** — Backend extracts text from the PDF using PyPDF2
3. **Parallel Analysis** — Four specialized agents analyze the contract simultaneously:
   - Legal, Privacy, Finance, and Security agents each return risk levels and descriptions
4. **Debate** — A Moderator agent synthesizes the agents' findings into a balanced debate summary
5. **Auto-Fix** — The Fix Agent rewrites risky clauses to be fairer and more balanced
6. **Scoring** — An overall compliance score is calculated from the aggregate risk levels
7. **Dashboard** — Results are presented in a step-by-step visual dashboard

---

## 📄 License

This project was built for the OpenSwarm App Builder challenge.

---

## 🙏 Acknowledgments

- Built with the [OpenSwarm](https://freebuff.com) App Builder
- Powered by Google Gemini and Groq for multi-agent AI analysis
- UI design system inspired by Anthropic's editorial aesthetic
