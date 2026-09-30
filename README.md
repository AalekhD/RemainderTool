# TaskTrack Pro — Task Assignment & Proof Submission Portal

TaskTrack Pro is a mobile-responsive, aesthetic task management and proof verification web application built with Streamlit and SQLite. It provides separate role-based workspaces for **Administrators / Supervisors** and **Workers**, complete with **Telegram notification integration** (1-click direct link sharing and optional Telegram Bot API dispatch).

---

## 🌟 Key Features

### 👑 Administrator Role
- **Secure Authentication**: Dedicated admin login credentials.
- **Worker Management**:
  - Register workers with Name, Employee ID, Mobile Number, Email, and **Telegram Handle / Chat ID**.
  - Generate unique User IDs (e.g., `W-1001`) and temporary passwords.
  - Require password change on first worker login.
  - 1-Click **Telegram Dispatch** of credentials to workers.
  - Enable / Disable worker accounts at any time.
- **Dynamic Task Assignment**:
  - Set Title, detailed instructions, Priority (`Low`, `Medium`, `High`, `Urgent`), and Due Date/Time.
  - Configurable proof requirement templates (Photos, Inspection logs, PDFs, Short videos, Documents).
  - 1-Click **Telegram Task Alert** with pre-filled Markdown notification.
- **Verification & Review Hub**:
  - Real-time dashboard metrics (Overdue, Pending Review, In Progress, Approved).
  - Built-in media proof inspector (Inline Photos, Video clips, Audio, PDF & Document downloaders).
  - **Approve or Reject**: Add feedback notes and request instant resubmission.
  - 1-Click **Telegram Approval / Rejection** dispatch with comments.

### 👷 Worker Role
- **Frictionless Mobile-First Experience**: Works smoothly on mobile browsers and desktop without app store installation.
- **Account Security**: Mandatory password reset upon first login.
- **Assigned Tasks Workspace**:
  - View only tasks assigned to the logged-in worker.
  - Clear priority indicators, overdue badges, and supervisor instructions.
- **Task Lifecycle**:
  - `Assigned` $\rightarrow$ `Accepted` $\rightarrow$ `In Progress` $\rightarrow$ `Submitted` $\rightarrow$ `Approved` / `Rejected`.
- **Rich Proof Upload**:
  - Upload Photos, PDF documents, Office files, or short video records.
  - Add completion comments and notes.
- **Revision & Resubmission**: View rejection comments from supervisor and submit corrected proof.

---

## 🚀 Quick Start

### 1. Set Up Environment & Run
```powershell
# Create & activate virtual environment (if not already done)
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start TaskTrack Pro
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 🔑 Default Demo Credentials

| Role | User ID / Login | Default Password |
| :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` |
| **Sample Worker** | `W-1001` | `worker123` |

*(Workers created with temporary passwords will be prompted to set their permanent private password upon first sign in).*

---

## ✈️ Telegram Integration

- **Direct Link Sharing**: When creating workers, assigning tasks, or reviewing submissions, click **✈️ Send via Telegram** to immediately open Telegram with pre-formatted Markdown notification cards.
- **Telegram Bot API (Optional)**: If you set `TELEGRAM_BOT_TOKEN` in your environment or [ .env ](.env.example), TaskTrack Pro can also dispatch notifications directly via Telegram Bot API to workers' chat IDs.
