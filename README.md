# KARE Viva Evaluation System (V2)

**Kalasalingam Academy of Research and Education (Deemed to be University)**  
*Accredited by NAAC with "A++" Grade • Under sec. 3 of UGC Act 1956*

A production-ready oral viva examination web application built with:
- **Frontend**: React (Vite) + Tailwind CSS + Lucide React + Recharts
- **Backend**: Python Flask + SQLAlchemy + Alembic / Flask-Migrate
- **Database**: Neon PostgreSQL (Serverless Cloud PostgreSQL)
- **PDF Extraction**: PyMuPDF (`fitz`) — 100% Ground Truth Question Bank
- **ASR Speech-to-Text**: NVIDIA Nemotron ASR service abstraction with editable student transcripts
- **Grading & Scoring**: Strict Best 2-of-3 scoring (maximum 20 marks) computed in Python backend
- **Auditing & Governance**: Immutable Mark Audit Trail (ADMIN ONLY)

---

## 1. Core Architectural Rules

1. **The PDF is the ONLY Source of Questions:**
   - The system **never** generates questions using an LLM.
   - Questions and reference answers are extracted strictly from faculty-uploaded PDFs using PyMuPDF and stored in Neon PostgreSQL.
   - If a question lacks a reference answer, validation fails and faculty must re-upload.
2. **Best 2 of 3 Scoring (Max 20 Marks):**
   - Each student is assigned exactly 3 questions (10 marks each).
   - The final score is computed in backend Python using the top 2 question scores:
     $$\text{Final Score} = \text{Top Score}_1 + \text{Top Score}_2 \le 20$$
   - Scores are never calculated out of 30.
3. **Role-Based Access Control (RBAC):**
   - **STUDENT**: Answers 3 questions, records speech, edits transcript, views own result. Cannot see audit logs.
   - **FACULTY**: Creates vivas, uploads PDFs, reviews validated question banks, views attendance and student marks. Cannot edit marks or view audit logs.
   - **ADMIN**: Manages user accounts, views system metrics, edits student marks with mandatory reason, views immutable mark audit trail.
4. **Immutable Mark Audits (ADMIN ONLY):**
   - When an Admin edits a mark, the previous score, new score, editor ID, mandatory reason, and timestamp are written to an append-only `mark_audits` table.
   - Student and Faculty requests to audit endpoints (`/api/admin/audits` and `PATCH /api/admin/results/:id`) strictly return **HTTP 403 Forbidden**.
5. **Anti-Cheating Proctored Mode:**
   - Fullscreen enforcement.
   - Right-click, cut, copy, paste, and common shortcuts are prevented.
   - Window blur, tab switches, and fullscreen exits are logged to the database.

---

## 2. Directory Structure

```
Viva-System/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask application factory
│   │   ├── config.py            # Environment configurations
│   │   ├── extensions.py        # db, migrate, cors
│   │   ├── middleware/
│   │   │   └── auth.py          # JWT & RBAC decorators
│   │   ├── models/
│   │   │   ├── user.py          # User (STUDENT, FACULTY, ADMIN)
│   │   │   ├── viva.py          # Viva container
│   │   │   ├── document.py      # Uploaded PDF document
│   │   │   ├── question.py      # Extracted Q&A pairs
│   │   │   ├── viva_session.py  # Student viva attempt
│   │   │   ├── session_question.py # 3 assigned questions
│   │   │   ├── answer.py        # Audio + original & edited transcripts
│   │   │   ├── evaluation.py    # AI evaluation breakdown
│   │   │   ├── result.py        # Best-2-of-3 final score (/20)
│   │   │   ├── violation.py     # Anti-cheat infractions
│   │   │   └── mark_audit.py    # Immutable audit trail
│   │   ├── routes/
│   │   │   ├── auth.py          # Register, Login, Me
│   │   │   ├── student.py       # Vivas, Audio upload, Transcript, Submit
│   │   │   ├── faculty.py       # Vivas, PDF upload, Q&A review, Results
│   │   │   └── admin.py         # Users, Results override, Audits, Stats
│   │   ├── services/
│   │   │   ├── pdf_service.py   # PyMuPDF text & Q&A extraction
│   │   │   ├── asr_service.py   # NVIDIA Nemotron ASR abstraction
│   │   │   ├── llm_service.py   # Answer evaluation ONLY
│   │   │   └── viva_service.py  # Session workflow & Best-2 calculation
│   │   └── utils/
│   │       └── security.py      # PyJWT token encode/decode
│   ├── data/
│   │   ├── uploads/             # Faculty uploaded PDFs
│   │   └── audio/               # Student recorded voice answers
│   ├── migrations/              # Alembic / Flask-Migrate versions
│   ├── tests/
│   │   ├── test_viva_system.py  # Unit tests (Auth, PDF, Best-2, Security)
│   │   └── test_complete_scenario.py # Full 32-step end-to-end scenario
│   ├── run.py                   # Server entry point (port 5001)
│   ├── seed.py                  # Database bootstrap and demo seeder
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── public/
│   │   └── kare_logo.png        # Official KARE university logo banner
│   ├── src/
│   │   ├── components/          # Navbar, Sidebar, KAREHeader, UI primitives
│   │   ├── context/             # AuthContext (user, token, roles)
│   │   ├── layouts/             # AppLayout
│   │   ├── pages/
│   │   │   ├── auth/            # LoginPage (with 1-click demos), RegisterPage
│   │   │   ├── student/         # Dashboard, Vivas, VivaSession, Results
│   │   │   ├── faculty/         # Dashboard, Vivas, Q&A Review, Results
│   │   │   └── admin/           # Dashboard, Users, Results, Audits, Violations
│   │   ├── routes/              # AppRoutes with role guards
│   │   └── services/            # Axios API client
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## 3. Quick Start & Credentials

### Default Accounts
| Role | Email | Password |
|---|---|---|
| **Student** | `student@klu.ac.in` | `student123` |
| **Faculty** | `faculty@klu.ac.in` | `faculty123` |
| **Admin** | `admin@klu.ac.in` | `admin123` |

### Running the Application

1. **Backend (Flask)**:
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python seed.py      # Seeds Neon PostgreSQL tables and sample viva
   python run.py       # Runs backend on http://127.0.0.1:5001
   ```

2. **Frontend (React + Vite)**:
   ```bash
   cd frontend
   npm install
   npm run dev         # Runs frontend on http://localhost:5173
   ```

3. **Running Automated Verification Tests**:
   ```bash
   PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/test_complete_scenario.py
   ```

---

## 4. Key Endpoints

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/auth/login` | Public | Authenticates user and returns JWT token |
| `POST` | `/api/student/vivas/:id/start` | Student | Selects 3 questions from PDF bank |
| `POST` | `/api/student/session-questions/:id/audio` | Student | Uploads audio & calls Nemotron ASR |
| `POST` | `/api/student/session-questions/:id/submit` | Student | Evaluates answer against PDF reference |
| `POST` | `/api/student/sessions/:id/finalize` | Student | Calculates Best 2-of-3 score (max 20) |
| `POST` | `/api/faculty/vivas/:id/upload` | Faculty | Extracts and validates Q&A pairs from PDF |
| `POST` | `/api/faculty/vivas/:id/publish` | Faculty | Publishes viva if $\ge 3$ valid questions |
| `PATCH` | `/api/admin/results/:id` | Admin Only | Overrides final mark with mandatory reason |
| `GET` | `/api/admin/audits` | Admin Only | Immutable audit log (403 for Student/Faculty) |
| `GET` | `/api/health` | Public | Service health & Neon PostgreSQL status |
