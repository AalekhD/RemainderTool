from __future__ import annotations

import os
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from db import (
    authenticate_user,
    change_user_password,
    create_task,
    create_task_submission,
    create_worker,
    delete_task,
    generate_temp_password,
    generate_unique_user_id,
    get_admin_dashboard_metrics,
    get_latest_submission_for_task,
    get_submissions_for_task,
    get_task_by_id,
    get_user_by_username,
    get_worker_dashboard_metrics,
    init_db,
    list_tasks,
    list_workers,
    reassign_task,
    reset_worker_password,
    review_submission,
    toggle_worker_status,
    update_task_status,
)
from emailer import send_notification
from telegram_messenger import (
    create_approval_message,
    create_rejection_message,
    create_task_assignment_message,
    create_worker_welcome_message,
    get_telegram_share_url,
    send_telegram_bot_message,
)


APP_DIR = Path(__file__).parent
UPLOAD_DIR = APP_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

STATUS_IN_PROGRESS = "In Progress"
DEFAULT_APP_PORTAL_URL = "http://localhost:8501"

st.set_page_config(
    page_title="TaskTrack Pro — Task & Proof Portal",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Auto refresh every 60s
st_autorefresh(interval=60_000, key="global-clock")
init_db()


def inject_custom_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');
        
        :root {
            --brand-primary: #24A1DE;
            --brand-secondary: #0088cc;
            --bg-canvas: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border-subtle: #e2e8f0;
            --border-hover: #cbd5e1;
            --radius-md: 12px;
            --radius-lg: 18px;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.03);
            --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
            --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.03);
        }

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            color: var(--text-main);
            background-color: var(--bg-canvas);
        }

        .stApp {
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%, #e2e8f0 100%);
        }

        h1, h2, h3, h4 {
            font-family: 'Space Grotesk', 'Plus Jakarta Sans', sans-serif;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: #0f172a;
        }

        /* Metric cards */
        .metric-card {
            background: #ffffff;
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 1.1rem 1.2rem;
            box-shadow: var(--shadow-sm);
            transition: all 0.2s ease-in-out;
            position: relative;
            overflow: hidden;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
            border-color: #cbd5e1;
        }
        .metric-card-accent {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
        }
        .metric-title {
            color: var(--text-muted);
            font-size: 0.82rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .metric-number {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2.1rem;
            font-weight: 700;
            margin-top: 0.25rem;
            color: #0f172a;
        }

        /* Status & Priority Badges */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 0.26rem 0.65rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.02em;
        }
        .status-assigned { background-color: #e0e7ff; color: #3730a3; }
        .status-accepted { background-color: #e0f2fe; color: #0369a1; }
        .status-in-progress { background-color: #f3e8ff; color: #6b21a8; }
        .status-submitted { background-color: #fef3c7; color: #92400e; }
        .status-approved { background-color: #d1fae5; color: #065f46; }
        .status-rejected { background-color: #ffe4e6; color: #9f1239; }

        .priority-low { background-color: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
        .priority-medium { background-color: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
        .priority-high { background-color: #fff7ed; color: #9a3412; border: 1px solid #fed7aa; }
        .priority-urgent { background-color: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }

        .overdue-pill {
            background-color: #dc2626;
            color: #ffffff;
            font-size: 0.7rem;
            font-weight: 800;
            padding: 0.15rem 0.5rem;
            border-radius: 9999px;
            text-transform: uppercase;
        }

        /* Telegram Direct Action Button */
        .telegram-btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            background: linear-gradient(135deg, #24A1DE, #0088cc);
            color: #ffffff !important;
            font-weight: 700;
            font-size: 0.88rem;
            padding: 0.55rem 1.1rem;
            border-radius: 8px;
            text-decoration: none;
            transition: all 0.2s ease;
            box-shadow: 0 2px 5px rgba(36, 161, 222, 0.3);
        }
        .telegram-btn:hover {
            background: linear-gradient(135deg, #2094cd, #0077b5);
            color: #ffffff !important;
            transform: translateY(-1px);
            box-shadow: 0 4px 10px rgba(36, 161, 222, 0.4);
        }

        /* Hero Headers */
        .page-header {
            margin-bottom: 1.5rem;
            padding-bottom: 0.8rem;
            border-bottom: 1px solid #e2e8f0;
        }
        .page-kicker {
            color: #24A1DE;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .page-title {
            font-size: 2rem;
            margin: 0.2rem 0 0.3rem 0;
            color: #0f172a;
        }
        .page-desc {
            color: var(--text-muted);
            font-size: 0.95rem;
            margin: 0;
        }

        /* Login Page */
        .brand-logo-pill {
            width: 54px;
            height: 54px;
            border-radius: 14px;
            background: linear-gradient(135deg, #24A1DE, #4f46e5);
            color: #ffffff;
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 800;
            font-size: 1.4rem;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 1rem auto;
            box-shadow: 0 4px 14px rgba(36, 161, 222, 0.35);
        }

        /* Premium Dark Glowing Sidebar matching mockup */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #070d24 0%, #0d173d 40%, #08102d 85%, #050b20 100%) !important;
            border-right: 1px solid rgba(59, 130, 246, 0.15) !important;
            padding-top: 1rem !important;
        }

        /* Brand Header in Sidebar */
        .sidebar-brand-box {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 0.4rem 0.2rem 1.2rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            margin-bottom: 1.2rem;
        }
        .sidebar-brand-icon {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: #ffffff;
            box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
            flex-shrink: 0;
        }
        .sidebar-brand-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.25rem;
            font-weight: 700;
            color: #ffffff !important;
            line-height: 1.2;
            letter-spacing: -0.01em;
        }
        .sidebar-brand-sub {
            font-size: 0.76rem;
            color: #94a3b8 !important;
            font-weight: 500;
            margin-top: 2px;
        }

        /* User Profile Glass Card */
        .sidebar-user-card {
            background: linear-gradient(145deg, rgba(29, 53, 110, 0.65) 0%, rgba(15, 30, 75, 0.8) 100%);
            border: 1.5px solid rgba(147, 197, 253, 0.45);
            border-radius: 16px;
            padding: 1.2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(10px);
        }
        .sidebar-user-top {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .sidebar-user-avatar {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #2563eb, #3b82f6);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: white;
            box-shadow: 0 0 16px rgba(37, 99, 235, 0.7);
            flex-shrink: 0;
            border: 1.5px solid rgba(255, 255, 255, 0.4);
        }
        .sidebar-user-name {
            font-size: 1.25rem;
            font-weight: 800;
            color: #ffffff !important;
            line-height: 1.2;
            text-shadow: 0 1px 4px rgba(0, 0, 0, 0.6);
        }
        .sidebar-user-status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.92rem;
            font-weight: 700;
            color: #86efac !important;
            margin-top: 4px;
        }
        .status-dot {
            width: 9px;
            height: 9px;
            background-color: #22c55e;
            border-radius: 50%;
            box-shadow: 0 0 10px #22c55e;
            display: inline-block;
        }
        .sidebar-user-divider {
            height: 1px;
            background: rgba(255, 255, 255, 0.2);
            margin: 0.85rem 0 0.65rem;
        }
        .sidebar-user-id {
            font-size: 0.92rem;
            font-weight: 600;
            color: #e2e8f0 !important;
        }

        /* =========================================================
           SIDEBAR MAIN MENU & NAVIGATION (CLEAN, MODERN & READABLE)
           ========================================================= */
        .sidebar-section-header {
            font-size: 0.85rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.1em !important;
            color: #94a3b8 !important;
            margin: 1.4rem 0 0.8rem 0.2rem !important;
            display: flex !important;
            align-items: center !important;
            gap: 10px !important;
        }
        .sidebar-section-header::after {
            content: '' !important;
            flex: 1 !important;
            height: 1px !important;
            background: rgba(255, 255, 255, 0.12) !important;
        }

        /* Target all radio containers in sidebar */
        section[data-testid="stSidebar"] [data-testid="stRadio"],
        section[data-testid="stSidebar"] div[role="radiogroup"] {
            display: flex !important;
            flex-direction: column !important;
            gap: 8px !important;
            width: 100% !important;
        }

        /* Target each radio option card */
        section[data-testid="stSidebar"] [data-testid="stRadio"] label,
        section[data-testid="stSidebar"] div[role="radiogroup"] label,
        section[data-testid="stSidebar"] label[data-baseweb="radio"] {
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 12px !important;
            padding: 12px 16px !important;
            margin: 0 !important;
            min-height: 48px !important;
            transition: all 0.2s ease !important;
            display: flex !important;
            align-items: center !important;
            cursor: pointer !important;
            width: 100% !important;
            box-shadow: none !important;
        }

        /* Hover effect */
        section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover,
        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover,
        section[data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
            background: rgba(59, 130, 246, 0.15) !important;
            border-color: rgba(96, 165, 250, 0.45) !important;
            transform: none !important;
        }

        /* Selected active state */
        section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked),
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked),
        section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
            background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%) !important;
            border: 1px solid #60a5fa !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3) !important;
            transform: none !important;
        }

        /* Radio Text Styling - Clean White & Balanced Size */
        section[data-testid="stSidebar"] [data-testid="stRadio"] label *,
        section[data-testid="stSidebar"] div[role="radiogroup"] label *,
        section[data-testid="stSidebar"] label[data-baseweb="radio"] *,
        section[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p,
        section[data-testid="stSidebar"] [data-testid="stRadio"] p,
        section[data-testid="stSidebar"] [data-testid="stRadio"] span,
        section[data-testid="stSidebar"] [data-testid="stRadio"] div {
            font-size: 0.96rem !important;
            font-weight: 600 !important;
            color: #ffffff !important;
            line-height: 1.3 !important;
            text-shadow: none !important;
        }

        /* Hide the ugly hidden widget label container if rendered as a box */
        section[data-testid="stSidebar"] [data-testid="stRadio"] > label:first-child:not([data-baseweb="radio"]) {
            display: none !important;
        }

        /* Sign Out Button */
        section[data-testid="stSidebar"] .stButton > button {
            background: rgba(239, 68, 68, 0.12) !important;
            color: #fca5a5 !important;
            border: 1px solid rgba(239, 68, 68, 0.3) !important;
            border-radius: 12px !important;
            padding: 10px 16px !important;
            min-height: 46px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.2s ease !important;
            box-shadow: none !important;
            text-shadow: none !important;
            width: 100% !important;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(239, 68, 68, 0.25) !important;
            color: #ffffff !important;
            border-color: #ef4444 !important;
            transform: none !important;
        }

        /* Sidebar Footer Mottos */
        .sidebar-footer {
            margin-top: 3.5rem;
            text-align: center;
            font-size: 0.68rem;
            letter-spacing: 0.2em;
            color: #475569 !important;
            text-transform: uppercase;
            font-weight: 700;
        }

        /* Rejection box */
        .feedback-box-rejected {
            background-color: #fff1f2;
            border-left: 4px solid #e11d48;
            padding: 0.8rem 1rem;
            border-radius: 0 8px 8px 0;
            margin: 0.6rem 0;
        }

        .feedback-box-approved {
            background-color: #f0fdf4;
            border-left: 4px solid #16a34a;
            padding: 0.8rem 1rem;
            border-radius: 0 8px 8px 0;
            margin: 0.6rem 0;
        }

        /* =========================================
           IMMERSIVE GLOWING LOGIN PAGE
           ========================================= */
        .stApp:has(.login-root-container) {
            background: radial-gradient(circle at 75% 20%, #1e40af 0%, #0f2356 35%, #08112c 70%, #040817 100%) !important;
            color: #f8fafc !important;
        }

        .login-top-bar {
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 16px;
            padding: 0.5rem 1rem 1.5rem;
            color: #94a3b8;
            font-size: 0.8rem;
            font-weight: 600;
            letter-spacing: 0.06em;
        }
        .login-top-bar span {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .login-brand-logo {
            width: 58px;
            height: 58px;
            background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.8rem;
            color: #ffffff;
            box-shadow: 0 8px 24px rgba(56, 189, 248, 0.4), inset 0 1px 0 rgba(255,255,255,0.4);
            margin-bottom: 1.2rem;
        }

        .login-hero-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2.8rem;
            font-weight: 800;
            color: #ffffff !important;
            line-height: 1.1;
            letter-spacing: -0.02em;
            margin-bottom: 0.35rem;
        }

        .login-hero-sub {
            font-size: 1.15rem;
            color: #93c5fd !important;
            font-weight: 500;
            margin-bottom: 0.6rem;
        }

        .login-hero-motto {
            font-size: 0.82rem;
            color: #64748b !important;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 2rem;
        }

        /* Feature Pills Stack */
        .login-features-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 2.2rem;
            max-width: 440px;
        }

        .login-feature-item {
            display: flex;
            align-items: center;
            gap: 14px;
            background: linear-gradient(135deg, rgba(20, 38, 86, 0.5) 0%, rgba(11, 23, 56, 0.65) 100%);
            border: 1px solid rgba(96, 165, 250, 0.16);
            border-radius: 14px;
            padding: 10px 14px;
            transition: all 0.2s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .login-feature-item:hover {
            transform: translateX(4px);
            border-color: rgba(96, 165, 250, 0.4);
            background: linear-gradient(135deg, rgba(30, 58, 126, 0.6) 0%, rgba(15, 30, 75, 0.75) 100%);
        }

        .login-feature-icon {
            width: 38px;
            height: 38px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.15rem;
            color: #ffffff;
            flex-shrink: 0;
            box-shadow: 0 4px 10px rgba(0,0,0,0.25);
        }

        .login-feature-text h5 {
            color: #ffffff !important;
            font-size: 0.92rem;
            font-weight: 700;
            margin: 0 0 2px 0;
        }
        .login-feature-text p {
            color: #94a3b8 !important;
            font-size: 0.78rem;
            margin: 0;
        }

        .login-quote-tag {
            font-style: italic;
            color: #60a5fa;
            font-size: 1rem;
            margin-top: 1.5rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        .login-script-text {
            font-family: 'Space Grotesk', cursive, sans-serif;
            font-size: 1.4rem;
            font-style: italic;
            color: #38bdf8;
            font-weight: 700;
            margin-top: 0.5rem;
            display: inline-block;
            border-bottom: 2px solid #38bdf8;
            padding-bottom: 4px;
        }

        /* Glassmorphic Login Form Card */
        .login-glass-card {
            background: linear-gradient(145deg, rgba(17, 34, 79, 0.65) 0%, rgba(8, 18, 48, 0.85) 100%) !important;
            border: 1px solid rgba(96, 165, 250, 0.3) !important;
            border-radius: 24px !important;
            padding: 2.4rem 2.2rem !important;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6), 0 0 35px rgba(37, 99, 235, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
            backdrop-filter: blur(20px) !important;
        }

        .login-glass-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2.1rem;
            font-weight: 800;
            color: #ffffff !important;
            margin-bottom: 0.3rem;
            text-align: center;
        }

        .login-glass-desc {
            color: #94a3b8 !important;
            font-size: 0.92rem;
            text-align: center;
            margin-bottom: 1.8rem;
        }

        /* Style Form Inputs inside Login Page */
        .stApp:has(.login-root-container) .stTextInput label p {
            color: #f1f5f9 !important;
            font-weight: 700 !important;
            font-size: 0.88rem !important;
            margin-bottom: 4px !important;
        }

        .stApp:has(.login-root-container) .stTextInput input {
            background: #ffffff !important;
            border: 2px solid #cbd5e1 !important;
            border-radius: 12px !important;
            color: #0f172a !important;
            height: 3.1rem !important;
            font-size: 0.98rem !important;
            font-weight: 500 !important;
            padding: 0 16px !important;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08) !important;
            transition: all 0.2s ease !important;
        }
        .stApp:has(.login-root-container) .stTextInput input::placeholder {
            color: #94a3b8 !important;
            font-size: 0.92rem !important;
        }
        .stApp:has(.login-root-container) .stTextInput input:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.35), 0 4px 12px rgba(0, 0, 0, 0.1) !important;
            background: #ffffff !important;
            color: #0f172a !important;
        }

        .stApp:has(.login-root-container) .stButton > button[kind="primary"],
        .stApp:has(.login-root-container) .stFormSubmitButton > button {
            background: linear-gradient(135deg, #2563eb 0%, #3b82f6 50%, #60a5fa 100%) !important;
            color: #ffffff !important;
            border: 1px solid rgba(147, 197, 253, 0.5) !important;
            border-radius: 12px !important;
            height: 3rem !important;
            font-weight: 700 !important;
            font-size: 1.05rem !important;
            letter-spacing: 0.02em !important;
            box-shadow: 0 8px 20px rgba(37, 99, 235, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
            transition: all 0.25s ease !important;
            margin-top: 0.5rem !important;
        }
        .stApp:has(.login-root-container) .stButton > button:hover,
        .stApp:has(.login-root-container) .stFormSubmitButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 12px 28px rgba(37, 99, 235, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.4) !important;
            border-color: #ffffff !important;
        }

        .login-divider-line {
            display: flex;
            align-items: center;
            text-align: center;
            color: #64748b;
            font-size: 0.8rem;
            margin: 1.4rem 0 1rem;
        }
        .login-divider-line::before,
        .login-divider-line::after {
            content: '';
            flex: 1;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12);
        }
        .login-divider-line::before { margin-right: 0.8em; }
        .login-divider-line::after { margin-left: 0.8em; }

        .stApp:has(.login-root-container) [data-testid="stExpander"] {
            background: rgba(11, 23, 56, 0.6) !important;
            border: 1px solid rgba(96, 165, 250, 0.2) !important;
            border-radius: 14px !important;
        }
        .stApp:has(.login-root-container) [data-testid="stExpander"] * {
            color: #cbd5e1 !important;
        }

        .login-page-footer {
            text-align: center;
            margin-top: 3rem;
            color: #475569 !important;
            font-size: 0.78rem;
            font-weight: 500;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def save_uploaded_proof(uploaded_file, submission_id: int) -> tuple[str, str]:
    suffix = Path(uploaded_file.name).suffix.lower() or ".bin"
    target = UPLOAD_DIR / f"proof-{submission_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}{suffix}"
    target.write_bytes(uploaded_file.getvalue())

    proof_type = "document"
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        proof_type = "image"
    elif suffix in {".mp4", ".mov", ".avi", ".webm", ".mkv"}:
        proof_type = "video"
    elif suffix in {".pdf"}:
        proof_type = "pdf"
    elif suffix in {".mp3", ".wav", ".m4a"}:
        proof_type = "audio"

    return str(target), proof_type


def remove_task_proof_files(proof_paths: list[str]) -> None:
    upload_root = UPLOAD_DIR.resolve()
    for stored_path in proof_paths:
        proof_path = Path(stored_path)
        try:
            resolved_path = proof_path.resolve()
            resolved_path.relative_to(upload_root)
        except (OSError, ValueError):
            continue
        if resolved_path.is_file():
            resolved_path.unlink(missing_ok=True)


def render_status_badge(status: str) -> str:
    css_class = f"status-{status.lower().replace(' ', '-')}"
    icons = {
        "Assigned": "📌",
        "Accepted": "👍",
        STATUS_IN_PROGRESS: "⏳",
        "Submitted": "📩",
        "Approved": "✅",
        "Rejected": "❌",
    }
    icon = icons.get(status, "•")
    return f'<span class="badge {css_class}">{icon} {status}</span>'


def render_priority_badge(priority: str) -> str:
    css_class = f"priority-{priority.lower()}"
    return f'<span class="badge {css_class}">{priority}</span>'


def check_is_overdue(due_datetime_str: str, status: str) -> bool:
    if status in {"Approved"}:
        return False
    try:
        due_dt = datetime.strptime(due_datetime_str, "%Y-%m-%d %H:%M:%S")
        return datetime.now() > due_dt
    except Exception:
        return False


# ==========================================
# AUTHENTICATION & LOGIN VIEWS
# ==========================================

def render_first_time_password_modal(user: dict) -> None:
    st.markdown(
        """
        <div style="max-width: 440px; margin: 4vh auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 20px; padding: 2.2rem 2rem; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.08);">
            <div class="brand-logo-pill">🔐</div>
            <h2 style="text-align: center; margin-bottom: 0.4rem;">Setup New Password</h2>
            <p style="text-align: center; color: #64748b; font-size: 0.9rem; margin-bottom: 1.5rem;">
                This is your first login. For security, please choose your permanent private password.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("first-time-pwd-form"):
        new_pwd = st.text_input("New Password", type="password", placeholder="At least 6 characters")
        confirm_pwd = st.text_input("Confirm New Password", type="password", placeholder="Re-enter password")
        submitted = st.form_submit_button("Save Password & Continue", use_container_width=True, type="primary")
        if submitted:
            if not new_pwd or len(new_pwd) < 6:
                st.error("Password must be at least 6 characters long.")
            elif new_pwd != confirm_pwd:
                st.error("Passwords do not match. Please verify.")
            else:
                success = change_user_password(user["username"], new_pwd)
                if success:
                    st.success("Password updated successfully! Redirecting...")
                    st.session_state["user"]["must_change_password"] = 0
                    st.rerun()
                else:
                    st.error("Failed to update password. Please try again.")


def login_view() -> None:
    inject_custom_styles()
    
    # Root container marker for scoped dark background
    st.markdown('<div class="login-root-container"></div>', unsafe_allow_html=True)
    
    # Top security badge header
    st.markdown(
        """
        <div class="login-top-bar">
            <span>🛡️ Secure</span> &nbsp;•&nbsp; <span>Reliable</span> &nbsp;•&nbsp; <span>Trusted</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_hero, _, col_form = st.columns([1.1, 0.1, 1.0])

    with col_hero:
        st.markdown(
            """
            <div class="login-brand-logo">📄</div>
            <div class="login-hero-title">TaskTrack Pro</div>
            <div class="login-hero-sub">Task & Proof Submission Portal</div>
            <div class="login-hero-motto">Assign &nbsp;•&nbsp; Track &nbsp;•&nbsp; Verify &nbsp;•&nbsp; Succeed</div>

            <div class="login-features-list">
                <div class="login-feature-item">
                    <div class="login-feature-icon" style="background: linear-gradient(135deg, #2563eb, #3b82f6);">📋</div>
                    <div class="login-feature-text">
                        <h5>Assign Tasks</h5>
                        <p>Easily create and assign tasks with specific proof requirements</p>
                    </div>
                </div>
                <div class="login-feature-item">
                    <div class="login-feature-icon" style="background: linear-gradient(135deg, #7c3aed, #a855f7);">👥</div>
                    <div class="login-feature-text">
                        <h5>Manage Workers</h5>
                        <p>Track worker accounts, access status, and performance</p>
                    </div>
                </div>
                <div class="login-feature-item">
                    <div class="login-feature-icon" style="background: linear-gradient(135deg, #059669, #10b981);">📊</div>
                    <div class="login-feature-text">
                        <h5>Proof Submission</h5>
                        <p>Verify completed work with live photos, videos, and documents</p>
                    </div>
                </div>
                <div class="login-feature-item">
                    <div class="login-feature-icon" style="background: linear-gradient(135deg, #0284c7, #38bdf8);">✈️</div>
                    <div class="login-feature-text">
                        <h5>Telegram Notifications</h5>
                        <p>Instant dispatch and real-time updates for assignments and reviews</p>
                    </div>
                </div>
                <div class="login-feature-item">
                    <div class="login-feature-icon" style="background: linear-gradient(135deg, #d97706, #f59e0b);">🛡️</div>
                    <div class="login-feature-text">
                        <h5>Monitor Progress</h5>
                        <p>Get real-time insights, overdue alerts, and quality verification</p>
                    </div>
                </div>
            </div>

            <div class="login-quote-tag">“ Small Tasks, Big Results ”</div>
            <div class="login-script-text">Work Smarter Together</div>
            """,
            unsafe_allow_html=True,
        )

    with col_form:
        st.markdown(
            """
            <div class="login-glass-card">
                <div class="login-glass-title">Welcome Back 👋</div>
                <div class="login-glass-desc">Sign in to your account to continue</div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login-form", border=False):
            username = st.text_input("User ID / Username", placeholder="e.g., admin or W-1001")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_btn = st.form_submit_button("Sign In →", use_container_width=True, type="primary")

            if login_btn:
                if not username or not password:
                    st.error("Please enter both User ID and Password.")
                else:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state["user"] = user
                        st.rerun()
                    else:
                        st.error("Invalid credentials or account is disabled.")

        st.markdown(
            """
            <div class="login-divider-line">or</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("💡 Demo Credentials / Quick Login Help", expanded=False):
            st.markdown(
                """
                - **Admin Portal**: User ID `admin` | Password: `admin123`
                - **Worker Portal**: User ID `W-1001` | Password: `worker123`
                """
            )

    # Footer
    st.markdown(
        """
        <div class="login-page-footer">
            © 2026 TaskTrack Pro. All rights reserved.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================
# ADMIN INTERFACE
# ==========================================

def render_admin_metrics() -> None:
    metrics = get_admin_dashboard_metrics()
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    cards = [
        (c1, "Total Tasks", metrics["total_tasks"], "#24A1DE"),
        (c2, "Needs Review", metrics["pending_review"], "#f59e0b"),
        (c3, "In Progress", metrics["in_progress"], "#8b5cf6"),
        (c4, "Approved", metrics["approved"], "#10b981"),
        (c5, "Overdue", metrics["overdue"], "#ef4444"),
        (c6, "Active Workers", metrics["active_workers"], "#06b6d4"),
    ]

    for col, title, value, color in cards:
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-card-accent" style="background-color: {color};"></div>
                    <div class="metric-title">{title}</div>
                    <div class="metric-number">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_admin_task_card(task: dict, current_user: dict, active_workers: list[dict]) -> None:
    is_overdue = check_is_overdue(task["due_datetime"], task["status"])
    overdue_badge = '<span class="overdue-pill">OVERDUE</span>' if is_overdue else ""

    with st.container(border=True):
        header_col, action_badge_col = st.columns([3, 1.2])
        with header_col:
            st.markdown(
                f"### `{task['task_uid']}` — {task['title']} {overdue_badge}",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"**Assignee:** {task['assignee_name']} (`{task['assigned_to_user_id']}`) &nbsp;|&nbsp; "
                f"**Due:** `{task['due_datetime']}` &nbsp;|&nbsp; "
                f"**Priority:** {render_priority_badge(task['priority'])} &nbsp;|&nbsp; "
                f"**Status:** {render_status_badge(task['status'])}",
                unsafe_allow_html=True,
            )
        with action_badge_col:
            worker_chat_id = str(task.get("assignee_telegram") or "").strip()
            if st.button(
                "Send Reminder",
                key=f"task-reminder-{task['id']}",
                use_container_width=True,
                disabled=not worker_chat_id.isdigit() or task["status"] == "Approved",
            ):
                reminder_message = (
                    f"TaskTrack reminder for task {task['task_uid']}\n"
                    f"Due: {task['due_datetime']}\n"
                    "Please sign in to TaskTrack Pro to review your task."
                )
                sent, detail = send_telegram_bot_message(worker_chat_id, reminder_message)
                if sent:
                    st.success(f"Reminder sent to {task['assignee_name']}.")
                else:
                    st.error(f"Telegram reminder failed: {detail}")

        st.markdown(f"**Instructions / Description:** {task['description'] or '*(No description provided)*'}")
        st.markdown(f"**Required Proof:** `{task['proof_requirements']}`")

        task_action_col, delete_action_col = st.columns([1, 1])
        with task_action_col:
            if task["status"] != "Approved":
                with st.expander("Reassign task"):
                    available_workers = [
                        worker for worker in active_workers
                        if worker["username"].lower() != task["assigned_to_user_id"].lower()
                    ]
                    if not available_workers:
                        st.info("No other active workers are available.")
                    else:
                        with st.form(f"reassign-task-{task['id']}"):
                            new_assignee = st.selectbox(
                                "Assign to worker",
                                available_workers,
                                format_func=lambda worker: f"{worker['full_name']} ({worker['username']})",
                            )
                            if st.form_submit_button("Reassign and reset to Assigned"):
                                if reassign_task(task["id"], new_assignee["username"]):
                                    st.success("Task reassigned. Existing submission history is retained.")
                                    st.rerun()
                                else:
                                    st.error("Task could not be reassigned.")

        with delete_action_col:
            if st.button("Delete task", key=f"delete-task-{task['id']}", use_container_width=True):
                st.session_state["pending_delete_task"] = task["id"]
                st.rerun()

            if st.session_state.get("pending_delete_task") == task["id"]:
                st.warning("Permanently delete this task, its submissions, and uploaded proof files?")
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button("Confirm delete", key=f"confirm-delete-{task['id']}", type="primary"):
                        deleted, proof_paths = delete_task(task["id"])
                        if deleted:
                            remove_task_proof_files(proof_paths)
                            st.session_state.pop("pending_delete_task", None)
                            st.success("Task and submission history permanently deleted.")
                            st.rerun()
                        else:
                            st.error("Task could not be deleted.")
                with cancel_col:
                    if st.button("Cancel", key=f"cancel-delete-{task['id']}"):
                        st.session_state.pop("pending_delete_task", None)
                        st.rerun()

        # Submissions & Proof Inspection
        submissions = get_submissions_for_task(task["id"])
        if submissions:
            st.divider()
            st.markdown("#### 📁 Submitted Proof & Verification")
            latest_sub = submissions[0]

            p_col1, p_col2 = st.columns([1.6, 1.4])
            with p_col1:
                st.markdown(f"**Submitted by:** {latest_sub['submitted_by']} on `{latest_sub['submitted_at']}`")
                if latest_sub["submitted_by"].lower() != task["assigned_to_user_id"].lower():
                    st.caption("Historical submission from a previous assignee; retained for the task record.")
                if latest_sub["notes"]:
                    st.info(f"**Worker Completion Notes:**\n\n{latest_sub['notes']}")

                proof_file = Path(latest_sub["proof_path"]) if latest_sub["proof_path"] else None
                if proof_file and proof_file.exists():
                    p_type = latest_sub.get("proof_type", "image")
                    if p_type == "image":
                        st.image(str(proof_file), caption=f"Proof: {latest_sub['proof_name']}", use_container_width=True)
                    elif p_type == "video":
                        st.video(str(proof_file))
                    elif p_type == "audio":
                        st.audio(str(proof_file))
                    else:
                        st.markdown(f"📄 **Document Attached:** `{latest_sub['proof_name']}`")
                        st.download_button(
                            "⬇️ Download & Open Document",
                            data=proof_file.read_bytes(),
                            file_name=latest_sub["proof_name"] or proof_file.name,
                            key=f"dl-proof-{latest_sub['id']}",
                        )
                else:
                    st.warning("Proof file attachment not found on disk.")

            with p_col2:
                st.markdown("##### Decision & Review Actions")
                if (
                    task["status"] == "Submitted"
                    and latest_sub["status"] == "Submitted"
                    and latest_sub["submitted_by"].lower() == task["assigned_to_user_id"].lower()
                ):
                    review_feedback = st.text_area(
                        "Feedback / Comments (Optional for Approval, Required for Rejection)",
                        key=f"feedback-{task['id']}",
                        placeholder="Add clear feedback or specific instructions...",
                        height=90,
                    )

                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("✅ Approve Proof", key=f"appr-{task['id']}", type="primary", use_container_width=True):
                            review_submission(
                                submission_id=latest_sub["id"],
                                task_id=task["id"],
                                status="Approved",
                                review_comment=review_feedback,
                                reviewed_by=current_user["username"],
                            )
                            # Optional Telegram bot dispatch
                            if task.get("assignee_telegram"):
                                send_telegram_bot_message(
                                    task["assignee_telegram"],
                                    create_approval_message(task["task_uid"], task["title"], review_feedback)
                                )
                            if task["assignee_email"]:
                                send_notification(
                                    f"Task Approved: {task['title']}",
                                    f"Your task '{task['title']}' ({task['task_uid']}) has been approved.\n{review_feedback}",
                                    task["assignee_email"],
                                )
                            st.success("Task Approved!")
                            st.rerun()

                    with btn_col2:
                        if st.button("❌ Reject & Request Resubmission", key=f"rej-{task['id']}", use_container_width=True):
                            if not review_feedback.strip():
                                st.error("Please provide rejection reason comments so the worker knows what to correct.")
                            else:
                                review_submission(
                                    submission_id=latest_sub["id"],
                                    task_id=task["id"],
                                    status="Rejected",
                                    review_comment=review_feedback,
                                    reviewed_by=current_user["username"],
                                )
                                if task.get("assignee_telegram"):
                                    send_telegram_bot_message(
                                        task["assignee_telegram"],
                                        create_rejection_message(task["task_uid"], task["title"], review_feedback)
                                    )
                                if task["assignee_email"]:
                                    send_notification(
                                        f"Task Revision Needed: {task['title']}",
                                        f"Your submission for task '{task['title']}' requires corrections:\n\n{review_feedback}",
                                        task["assignee_email"],
                                    )
                                st.warning("Task marked as Rejected. Resubmission requested.")
                                st.rerun()

                    # Telegram Quick Action Share Links for Supervisor
                    st.write("")
                    st.caption("Telegram Quick Link Dispatch:")
                    appr_tg = get_telegram_share_url(
                        create_approval_message(task["task_uid"], task["title"], review_feedback),
                        username=task.get("assignee_telegram", "")
                    )
                    rej_tg = get_telegram_share_url(
                        create_rejection_message(task["task_uid"], task["title"], review_feedback or "Please review feedback and resubmit"),
                        username=task.get("assignee_telegram", "")
                    )
                    tcol1, tcol2 = st.columns(2)
                    with tcol1:
                        st.markdown(f'<a href="{appr_tg}" target="_blank" class="telegram-btn" style="font-size: 0.76rem; width:100%;">✈️ Telegram Approval</a>', unsafe_allow_html=True)
                    with tcol2:
                        st.markdown(f'<a href="{rej_tg}" target="_blank" class="telegram-btn" style="background: linear-gradient(135deg, #e11d48, #be123c); font-size: 0.76rem; width:100%;">✈️ Telegram Rejection</a>', unsafe_allow_html=True)

                elif latest_sub["status"] == "Approved":
                    st.markdown(
                        f"""
                        <div class="feedback-box-approved">
                            <strong>Status: Approved</strong><br>
                            Reviewed by <em>{latest_sub.get('reviewed_by', 'Admin')}</em> on {latest_sub.get('reviewed_at', '')}<br>
                            <strong>Feedback:</strong> {latest_sub.get('review_comment') or 'Verified and approved.'}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                elif latest_sub["status"] == "Rejected":
                    st.markdown(
                        f"""
                        <div class="feedback-box-rejected">
                            <strong>Status: Rejected (Awaiting Correction)</strong><br>
                            Reviewed by <em>{latest_sub.get('reviewed_by', 'Admin')}</em> on {latest_sub.get('reviewed_at', '')}<br>
                            <strong>Rejection Reason:</strong> {latest_sub.get('review_comment')}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("Submission history is retained; no review is pending.")
        else:
            st.caption("No proof submitted yet for this task.")


def admin_dashboard_view(current_user: dict) -> None:
    st.markdown(
        """
        <div class="page-header">
            <div class="page-kicker">Admin Control Center</div>
            <h1 class="page-title">Operations & Proof Monitor</h1>
            <p class="page-desc">Track real-time task progress, inspect submitted evidence, and approve or request revisions.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_admin_metrics()
    st.write("")
    workers = list_workers(include_disabled=True)
    all_tasks = list_tasks()
    tasks_by_worker: dict[str, list[dict]] = {}
    for task in all_tasks:
        tasks_by_worker.setdefault(task["assigned_to_user_id"].lower(), []).append(task)

    selected_username = st.session_state.get("operations_selected_worker")
    selected_worker = next(
        (worker for worker in workers if worker["username"].lower() == (selected_username or "").lower()),
        None,
    )
    if selected_username and not selected_worker:
        st.session_state.pop("operations_selected_worker", None)

    if not selected_worker:
        st.subheader("Workers")
        if not workers:
            st.info("No workers have been created yet.")
            return

        worker_columns = st.columns(2)
        for index, worker in enumerate(workers):
            worker_tasks = tasks_by_worker.get(worker["username"].lower(), [])
            awaiting_review = sum(task["status"] == "Submitted" for task in worker_tasks)
            in_progress = sum(task["status"] in {"Accepted", STATUS_IN_PROGRESS} for task in worker_tasks)
            with worker_columns[index % 2]:
                with st.container(border=True):
                    if st.button(
                        f"{worker['full_name']}  ·  {worker['username']}",
                        key=f"open-worker-{worker['id']}",
                        use_container_width=True,
                    ):
                        st.session_state["operations_selected_worker"] = worker["username"]
                        st.rerun()
                    st.caption(
                        f"{len(worker_tasks)} tasks  ·  {in_progress} in progress  ·  "
                        f"{awaiting_review} awaiting review"
                    )
        return

    if st.button("← All workers", key="operations-back-to-workers"):
        st.session_state.pop("operations_selected_worker", None)
        st.rerun()

    st.subheader(f"{selected_worker['full_name']} · Tasks")
    worker_tasks = tasks_by_worker.get(selected_worker["username"].lower(), [])
    status_counts = {
        status: sum(task["status"] == status for task in worker_tasks)
        for status in ["Assigned", "Accepted", STATUS_IN_PROGRESS, "Submitted", "Approved", "Rejected"]
    }
    count_columns = st.columns(4)
    count_items = [
        ("Assigned", status_counts["Assigned"]),
        ("In Progress", status_counts["Accepted"] + status_counts[STATUS_IN_PROGRESS]),
        ("Awaiting Review", status_counts["Submitted"]),
        ("Approved", status_counts["Approved"]),
    ]
    for column, (label, value) in zip(count_columns, count_items):
        with column:
            st.metric(label, value)

    status_filter = st.selectbox(
        "Filter by status",
        ["All", "Assigned", "Accepted", STATUS_IN_PROGRESS, "Submitted", "Approved", "Rejected"],
        key=f"worker-task-status-{selected_worker['id']}",
    )
    filtered_tasks = [
        task for task in worker_tasks
        if status_filter == "All" or task["status"] == status_filter
    ]

    if not filtered_tasks:
        st.info("This worker has no tasks matching the selected status.")
        return

    active_workers = list_workers(include_disabled=False)
    for task in filtered_tasks:
        render_admin_task_card(task, current_user, active_workers)


def admin_assign_task_view(current_user: dict) -> None:
    st.markdown(
        """
        <div class="page-header">
            <div class="page-kicker">New Assignment</div>
            <h1 class="page-title">Create & Assign Task</h1>
            <p class="page-desc">Define task objectives, due dates, proof requirements, and assign to a team member.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    workers = list_workers(include_disabled=False)
    if not workers:
        st.warning("⚠️ No active workers found. Please create a worker account in 'Worker Management' first.")
        return

    with st.container(border=True):
        with st.form("create-task-form"):
            t_col1, t_col2 = st.columns([2, 1.2])
            with t_col1:
                title = st.text_input("Task Title *", placeholder="e.g., Clean Room Sterilization & Audit")
            with t_col2:
                worker_choices = {f"{w['full_name']} (ID: {w['username']})": w for w in workers}
                selected_worker_label = st.selectbox("Assign To Worker *", list(worker_choices.keys()))
                assigned_worker = worker_choices[selected_worker_label]

            description = st.text_area(
                "Detailed Instructions / Scope of Work",
                placeholder="Specify step-by-step procedures, safety guidelines, and key requirements...",
                height=110,
            )

            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                priority = st.selectbox("Priority Level", ["Medium", "High", "Urgent", "Low"], index=0)
            with p_col2:
                due_date = st.date_input("Due Date", value=date.today())
            with p_col3:
                due_time = st.time_input("Due Time", value=time(18, 0))

            proof_presets = [
                "Photograph of completed work",
                "Photograph of inspection log & gauge readings",
                "PDF Audit Checklist / Form",
                "Short video walkthrough (< 30s)",
                "Document / Signed Delivery Slip",
                "Custom specification",
            ]
            selected_proof_preset = st.selectbox("Proof Requirement Template", proof_presets)
            
            if selected_proof_preset == "Custom specification":
                proof_reqs = st.text_input("Custom Proof Requirements *", placeholder="e.g., 2 photos of clean filters + signed checklist")
            else:
                proof_reqs = selected_proof_preset

            submit_btn = st.form_submit_button("Create & Dispatch Task 🚀", type="primary", use_container_width=True)

            if submit_btn:
                if not title.strip():
                    st.error("Please enter a Task Title.")
                else:
                    due_dt_str = f"{due_date.strftime('%Y-%m-%d')} {due_time.strftime('%H:%M:00')}"
                    success, task_uid = create_task(
                        title=title,
                        description=description,
                        priority=priority,
                        due_datetime=due_dt_str,
                        proof_requirements=proof_reqs,
                        assigned_to_user_id=assigned_worker["username"],
                        created_by=current_user["username"],
                    )

                    if success:
                        st.session_state["last_created_task"] = {
                            "task_uid": task_uid,
                            "title": title,
                            "priority": priority,
                            "due_datetime": due_dt_str,
                            "proof_requirements": proof_reqs,
                            "description": description,
                            "worker_name": assigned_worker["full_name"],
                            "worker_telegram": assigned_worker.get("telegram_handle", ""),
                            "worker_email": assigned_worker.get("email", ""),
                        }
                        st.success(f"Task **{title}** (`{task_uid}`) successfully created and assigned to **{assigned_worker['full_name']}**!")
                        st.rerun()
                    else:
                        st.error(f"Failed to create task: {task_uid}")

    if "last_created_task" in st.session_state:
        lt = st.session_state["last_created_task"]
        st.write("")
        with st.container(border=True):
            st.markdown(f"#### ✈️ Instant Telegram Notification for `{lt['task_uid']}`")
            st.markdown(f"Task assigned to **{lt['worker_name']}**.")

            tg_msg = create_task_assignment_message(
                task_uid=lt["task_uid"],
                title=lt["title"],
                priority=lt["priority"],
                due_datetime=lt["due_datetime"],
                proof_requirements=lt["proof_requirements"],
                description=lt["description"],
            )
            tg_link = get_telegram_share_url(tg_msg, username=lt["worker_telegram"])

            w_col1, w_col2 = st.columns([1.5, 2])
            with w_col1:
                st.markdown(f'<a href="{tg_link}" target="_blank" class="telegram-btn">✈️ Send via Telegram Now</a>', unsafe_allow_html=True)
            with w_col2:
                if lt["worker_telegram"]:
                    if st.button("🤖 Dispatch via Telegram Bot", key="send-bot-assign"):
                        sent_ok, bot_resp = send_telegram_bot_message(lt["worker_telegram"], tg_msg)
                        if sent_ok:
                            st.success(f"Bot message dispatched to {lt['worker_telegram']}.")
                        else:
                            st.info(f"Bot dispatch status: {bot_resp}")
                if lt["worker_email"]:
                    if st.button("📧 Send Notification via Email", key="send-email-assign"):
                        sent = send_notification(
                            f"New Task Assigned: {lt['title']} [{lt['task_uid']}]",
                            f"Hello {lt['worker_name']},\n\nYou have been assigned a new task: {lt['title']}.\nDue: {lt['due_datetime']}\nPriority: {lt['priority']}\nProof Required: {lt['proof_requirements']}\n\nLog in to TaskTrack Pro to view and complete it.",
                            lt["worker_email"],
                        )
                        if sent:
                            st.success(f"Email sent to {lt['worker_email']}.")


def admin_worker_management_view() -> None:
    st.markdown(
        """
        <div class="page-header">
            <div class="page-kicker">User Directory</div>
            <h1 class="page-title">Worker Account Management</h1>
            <p class="page-desc">Create worker credentials, distribute login info via Telegram, and manage access.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_create, tab_list = st.tabs(["➕ Create New Worker", "👥 Active & Registered Workers"])

    with tab_create:
        with st.container(border=True):
            st.markdown("#### Register a Worker Account")
            with st.form("create-worker-form"):
                w_col1, w_col2 = st.columns(2)
                with w_col1:
                    full_name = st.text_input("Worker Full Name *", placeholder="e.g., Alex Rivera")
                    employee_id = st.text_input("Employee / Worker ID", placeholder="e.g., EMP-1042")
                    telegram_handle = st.text_input("Telegram Username / Chat ID *", placeholder="e.g., @alex_worker or chat_id")
                    phone = st.text_input("Mobile Number (Optional)", placeholder="e.g., +1234567890")
                with w_col2:
                    email = st.text_input("Email Address (Optional)", placeholder="worker@company.com")
                    auto_uid = generate_unique_user_id("W")
                    custom_uid = st.text_input("User ID / Login Username", value=auto_uid, help="Unique identifier worker will use to log in")
                    auto_pwd = generate_temp_password(8)
                    temp_pwd = st.text_input("Temporary Password", value=auto_pwd, help="Password provided to worker for first login")

                must_change = st.checkbox("Require password change on first login", value=True)
                create_worker_btn = st.form_submit_button("Create Worker Account 👤", type="primary", use_container_width=True)

                if create_worker_btn:
                    if not full_name.strip():
                        st.error("Worker Full Name is required.")
                    else:
                        success, uid_res, pwd_res = create_worker(
                            full_name=full_name,
                            employee_id=employee_id,
                            phone=phone,
                            telegram_handle=telegram_handle,
                            email=email,
                            username=custom_uid,
                            temporary_password=temp_pwd,
                            must_change_pwd=must_change,
                        )
                        if success:
                            st.session_state["newly_created_worker"] = {
                                "name": full_name,
                                "user_id": uid_res,
                                "temp_pwd": pwd_res,
                                "telegram": telegram_handle,
                                "phone": phone,
                                "email": email,
                            }
                            st.success(f"Worker **{full_name}** successfully created with User ID `{uid_res}`!")
                            st.rerun()
                        else:
                            st.error(f"Error creating worker: {pwd_res}")

        if "newly_created_worker" in st.session_state:
            nw = st.session_state["newly_created_worker"]
            st.write("")
            with st.container(border=True):
                st.markdown("### 🎉 Account Created & Ready for Distribution")
                st.markdown(
                    f"""
                    **Worker Name:** {nw['name']}  
                    **User ID (Login):** `{nw['user_id']}`  
                    **Temporary Password:** `{nw['temp_pwd']}`  
                    **Telegram:** `{nw['telegram'] or 'N/A'}`
                    """
                )

                tg_welcome_text = create_worker_welcome_message(
                    full_name=nw["name"],
                    user_id=nw["user_id"],
                    temp_password=nw["temp_pwd"],
                )
                tg_welcome_url = get_telegram_share_url(tg_welcome_text, username=nw["telegram"])

                wbtn_col1, wbtn_col2 = st.columns([1.5, 2])
                with wbtn_col1:
                    st.markdown(
                        f'<a href="{tg_welcome_url}" target="_blank" class="telegram-btn">✈️ Send Credentials via Telegram</a>',
                        unsafe_allow_html=True,
                    )
                with wbtn_col2:
                    if nw["telegram"]:
                        if st.button("🤖 Send via Telegram Bot", key="bot-send-creds"):
                            bot_ok, bot_m = send_telegram_bot_message(nw["telegram"], tg_welcome_text)
                            if bot_ok:
                                st.success("Credentials sent via Telegram Bot.")
                            else:
                                st.info(f"Bot dispatch status: {bot_m}")
                    if nw["email"]:
                        if st.button("📧 Email Credentials to Worker", key="email-worker-creds"):
                            sent = send_notification(
                                "Your TaskTrack Pro Login Credentials",
                                tg_welcome_text.replace("*", "").replace("`", ""),
                                nw["email"],
                            )
                            if sent:
                                st.success("Credentials emailed successfully.")

    with tab_list:
        workers = list_workers(include_disabled=True)
        if not workers:
            st.info("No worker accounts registered yet.")
        else:
            for w in workers:
                with st.container(border=True):
                    w_left, w_mid, w_right = st.columns([2, 2, 1.2])
                    with w_left:
                        status_tag = '<span style="color:#10b981; font-weight:700;">🟢 Active</span>' if w["is_active"] else '<span style="color:#ef4444; font-weight:700;">🔴 Disabled</span>'
                        st.markdown(f"#### {w['full_name']} &nbsp; {status_tag}", unsafe_allow_html=True)
                        st.markdown(f"**User ID:** `{w['username']}` &nbsp;|&nbsp; **Emp ID:** `{w['employee_id'] or 'N/A'}`")
                    with w_mid:
                        st.markdown(f"✈️ **Telegram:** `{w.get('telegram_handle') or 'N/A'}`")
                        st.markdown(f"📞 **Phone:** `{w['phone'] or 'N/A'}` &nbsp;|&nbsp; ✉️ `{w['email'] or 'N/A'}`")
                    with w_right:
                        worker_chat_id = str(w.get("telegram_handle") or "").strip()
                        if st.button(
                            "Send Telegram Test",
                            key=f"telegram-test-{w['id']}",
                            use_container_width=True,
                            disabled=not worker_chat_id.isdigit(),
                        ):
                            sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            test_message = (
                                f"Hello {w['full_name']}, this is a TaskTrack Pro test message "
                                f"sent on {sent_at}."
                            )
                            sent, detail = send_telegram_bot_message(worker_chat_id, test_message)
                            if sent:
                                st.success(f"Test message sent to {w['full_name']}.")
                            else:
                                st.error(f"Telegram test failed: {detail}")

                        if not worker_chat_id.isdigit():
                            st.caption("Add a numeric Telegram chat ID to enable bot messages.")

                        if st.button(
                            "Reset & Send Credentials",
                            key=f"reset-send-credentials-{w['id']}",
                            use_container_width=True,
                            disabled=not worker_chat_id.isdigit() or not w["is_active"],
                        ):
                            temporary_password = reset_worker_password(w["username"])
                            if not temporary_password:
                                st.error("Could not reset credentials for this worker.")
                            else:
                                credentials_message = create_worker_welcome_message(
                                    full_name=w["full_name"],
                                    user_id=w["username"],
                                    temp_password=temporary_password,
                                    portal_url=os.getenv("TASKTRACK_PORTAL_URL", DEFAULT_APP_PORTAL_URL),
                                )
                                sent, detail = send_telegram_bot_message(
                                    worker_chat_id,
                                    credentials_message,
                                )
                                if sent:
                                    st.success(f"New temporary credentials sent to {w['full_name']}.")
                                else:
                                    st.error(f"Telegram delivery failed: {detail}")
                                    st.warning("The worker password was reset; share this temporary login securely:")
                                    st.code(f"User ID: {w['username']}\nTemporary password: {temporary_password}")

                        if w["is_active"]:
                            if st.button("Disable Access", key=f"disable-{w['id']}", use_container_width=True):
                                toggle_worker_status(w["username"], False)
                                st.rerun()
                        else:
                            if st.button("Enable Access", key=f"enable-{w['id']}", use_container_width=True):
                                toggle_worker_status(w["username"], True)
                                st.rerun()

                        if w.get("telegram_handle"):
                            direct_tg = get_telegram_share_url(f"Hello {w['full_name']}, this is TaskTrack Admin.", username=w["telegram_handle"])
                            st.markdown(f'<a href="{direct_tg}" target="_blank" class="telegram-btn" style="font-size:0.75rem; padding:0.35rem 0.6rem; width:100%; margin-top:4px;">✈️ Chat Telegram</a>', unsafe_allow_html=True)


# ==========================================
# WORKER INTERFACE
# ==========================================

def render_worker_metrics(username: str) -> None:
    metrics = get_worker_dashboard_metrics(username)
    c1, c2, c3, c4, c5 = st.columns(5)

    cards = [
        (c1, "Total Assigned", metrics["total_assigned"], "#24A1DE"),
        (c2, "Action Required", metrics["action_required"], "#f59e0b"),
        (c3, "Under Review", metrics["submitted"], "#8b5cf6"),
        (c4, "Approved", metrics["approved"], "#10b981"),
        (c5, "Overdue", metrics["overdue"], "#ef4444"),
    ]

    for col, title, value, color in cards:
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-card-accent" style="background-color: {color};"></div>
                    <div class="metric-title">{title}</div>
                    <div class="metric-number">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_worker_action_task(task: dict, user: dict) -> None:
    is_overdue = check_is_overdue(task["due_datetime"], task["status"])
    overdue_badge = '<span class="overdue-pill">OVERDUE</span>' if is_overdue else ""

    with st.container(border=True):
        st.markdown(
            f"### `{task['task_uid']}` — {task['title']} {overdue_badge}",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"**Due Date & Time:** `{task['due_datetime']}` &nbsp;|&nbsp; "
            f"**Priority:** {render_priority_badge(task['priority'])} &nbsp;|&nbsp; "
            f"**Current Status:** {render_status_badge(task['status'])}",
            unsafe_allow_html=True,
        )
        st.markdown(f"**Instructions:** {task['description'] or '*(No additional notes)*'}")
        st.markdown(f"📸 **Required Proof:** `{task['proof_requirements']}`")

        latest_sub = get_latest_submission_for_task(task["id"])
        if task["status"] == "Rejected" and latest_sub:
            st.markdown(
                f"""
                <div class="feedback-box-rejected">
                    <strong>⚠️ Correction Requested by Supervisor:</strong><br>
                    "{latest_sub.get('review_comment') or 'Please update the proof and resubmit.'}"
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.divider()

        if task["status"] == "Assigned":
            st.markdown("👉 **Step 1:** Acknowledge and accept this assignment.")
            if st.button("👍 Accept Task", key=f"accept-{task['id']}", type="primary", use_container_width=True):
                update_task_status(task["id"], "Accepted")
                st.success("Task accepted!")
                st.rerun()

        elif task["status"] == "Accepted":
            st.markdown("👉 **Step 2:** Start work when ready.")
            if st.button("⏳ Start Working (In Progress)", key=f"start-{task['id']}", type="primary", use_container_width=True):
                update_task_status(task["id"], STATUS_IN_PROGRESS)
                st.success("Task marked In Progress.")
                st.rerun()

        elif task["status"] in {STATUS_IN_PROGRESS, "Rejected"}:
            st.markdown("👉 **Step 3:** Upload proof and submit for supervisor approval.")
            with st.form(f"submit-proof-form-{task['id']}", border=False):
                uploaded = st.file_uploader(
                    "Attach Proof (Photo, PDF, Short Video, Document) *",
                    type=["jpg", "jpeg", "png", "webp", "pdf", "mp4", "mov", "docx", "txt"],
                    key=f"file-upload-{task['id']}",
                )
                completion_notes = st.text_area(
                    "Completion Comments / Notes",
                    placeholder="Describe the work done or explain any specific details...",
                    key=f"notes-input-{task['id']}",
                    height=80,
                )
                submit_proof_btn = st.form_submit_button(
                    "🚀 Submit Proof for Review",
                    type="primary",
                    use_container_width=True,
                )

                if submit_proof_btn:
                    if not uploaded:
                        st.error("Please attach a proof file (Photograph, PDF, Video, or Document) before submitting.")
                    else:
                        success, sub_id = create_task_submission(
                            task_id=task["id"],
                            submitted_by=user["username"],
                            notes=completion_notes,
                            proof_name=uploaded.name,
                            proof_path="",
                            proof_type="image",
                        )
                        if success:
                            saved_path, proof_type = save_uploaded_proof(uploaded, sub_id)
                            from db import connection
                            with connection() as conn:
                                conn.execute(
                                    "UPDATE submissions SET proof_path = ?, proof_type = ? WHERE id = ?",
                                    (saved_path, proof_type, sub_id)
                                )
                            
                            st.success("Proof submitted successfully! Your supervisor has been notified.")
                            st.rerun()
                        else:
                            st.error("Submission failed. Please try again.")


def worker_dashboard_view(user: dict) -> None:
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-kicker">Worker Workspace</div>
            <h1 class="page-title">Welcome back, {user['full_name']}</h1>
            <p class="page-desc">User ID: <code>{user['username']}</code> &nbsp;|&nbsp; View your assigned tasks, record progress, and upload completion proof.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_worker_metrics(user["username"])
    st.write("")

    tab_action, tab_review, tab_approved, tab_profile = st.tabs([
        "⚡ Action Required Tasks",
        "⏳ Under Review",
        "✅ Completed & Approved",
        "👤 Account & Security",
    ])

    with tab_action:
        tasks = list_tasks(assigned_to=user["username"])
        action_tasks = [t for t in tasks if t["status"] in {"Assigned", "Accepted", STATUS_IN_PROGRESS, "Rejected"}]

        if not action_tasks:
            st.success("🎉 You're all caught up! No pending tasks require action right now.")
        else:
            for task in action_tasks:
                render_worker_action_task(task, user)

    with tab_review:
        tasks = list_tasks(assigned_to=user["username"], status_filter="Submitted")
        if not tasks:
            st.info("No submissions currently waiting for supervisor review.")
        else:
            for task in tasks:
                with st.container(border=True):
                    st.markdown(f"### `{task['task_uid']}` — {task['title']}")
                    st.markdown(f"**Submitted on:** `{task['updated_at']}` &nbsp;|&nbsp; Status: {render_status_badge(task['status'])}", unsafe_allow_html=True)
                    st.markdown(f"**Proof Required:** `{task['proof_requirements']}`")
                    
                    latest_sub = get_latest_submission_for_task(task["id"])
                    if latest_sub and latest_sub["proof_path"]:
                        st.caption(f"Attached file: {latest_sub['proof_name']}")
                        p_file = Path(latest_sub["proof_path"])
                        if p_file.exists() and latest_sub.get("proof_type") == "image":
                            st.image(str(p_file), width=350)
                    st.info("⏳ Your submission is currently under review by the supervisor.")

    with tab_approved:
        tasks = list_tasks(assigned_to=user["username"], status_filter="Approved")
        if not tasks:
            st.info("No approved task records yet.")
        else:
            for task in tasks:
                with st.container(border=True):
                    st.markdown(f"### `{task['task_uid']}` — {task['title']}")
                    st.markdown(f"**Completed & Verified:** {render_status_badge('Approved')}", unsafe_allow_html=True)
                    latest_sub = get_latest_submission_for_task(task["id"])
                    if latest_sub:
                        st.markdown(
                            f"""
                            <div class="feedback-box-approved">
                                <strong>Reviewed by:</strong> {latest_sub.get('reviewed_by', 'Supervisor')}<br>
                                <strong>Feedback:</strong> {latest_sub.get('review_comment') or 'Approved without additional comments.'}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

    with tab_profile:
        with st.container(border=True):
            st.markdown("#### 👤 Account Profile Details")
            st.markdown(
                f"""
                - **Full Name:** {user['full_name']}
                - **User ID / Login:** `{user['username']}`
                - **Employee ID:** `{user.get('employee_id') or 'N/A'}`
                - **Telegram:** `{user.get('telegram_handle') or 'N/A'}`
                - **Mobile:** `{user.get('phone') or 'N/A'}`
                - **Email:** `{user.get('email') or 'N/A'}`
                """
            )
            st.divider()
            st.markdown("#### 🔒 Change Password")
            with st.form("worker-change-pwd-form"):
                new_p = st.text_input("New Password", type="password")
                confirm_p = st.text_input("Confirm New Password", type="password")
                change_btn = st.form_submit_button("Update Password", type="primary")

                if change_btn:
                    if not new_p or len(new_p) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif new_p != confirm_p:
                        st.error("Passwords do not match.")
                    else:
                        if change_user_password(user["username"], new_p):
                            st.success("Password updated successfully!")
                        else:
                            st.error("Failed to update password.")


# ==========================================
# MAIN APPLICATION ROUTER
# ==========================================

def render_sidebar(user: dict) -> str:
    with st.sidebar:
        # 1. Brand Header
        st.markdown(
            """
            <div class="sidebar-brand-box">
                <div class="sidebar-brand-icon">📄</div>
                <div>
                    <div class="sidebar-brand-title">TaskTrack Pro</div>
                    <div class="sidebar-brand-sub">Task & Proof Portal</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 2. User Profile Card
        role = user.get("role", "Worker")
        full_name = user.get("full_name", "System Administrator")
        username = user.get("username", "admin")

        st.markdown(
            f"""
            <div class="sidebar-user-card">
                <div class="sidebar-user-top">
                    <div class="sidebar-user-avatar">👤</div>
                    <div>
                        <div class="sidebar-user-name">{full_name}</div>
                        <div class="sidebar-user-status">
                            <span class="status-dot"></span> Online
                        </div>
                    </div>
                </div>
                <div class="sidebar-user-divider"></div>
                <div class="sidebar-user-id">User ID: {username} &nbsp;•&nbsp; {role}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 3. Main Menu Navigation
        st.markdown('<div class="sidebar-section-header">MAIN MENU</div>', unsafe_allow_html=True)

        if role == "Admin":
            nav_selection = st.radio(
                "Navigation",
                ["📊 Operations Dashboard", "📋 Assign New Task", "👥 Worker Management"],
                label_visibility="collapsed",
            )
        else:
            nav_selection = st.radio(
                "Navigation",
                ["⚡ My Tasks Workspace"],
                label_visibility="collapsed",
            )

        st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)

        # 4. Sign Out Button
        if st.button("🚪  Sign Out", use_container_width=True):
            st.session_state.pop("user", None)
            st.session_state.pop("last_created_task", None)
            st.session_state.pop("newly_created_worker", None)
            st.rerun()

        # 5. Footer Motto
        st.markdown(
            """
            <div class="sidebar-footer">
                PLAN &nbsp;•&nbsp; ASSIGN &nbsp;•&nbsp; TRACK &nbsp;•&nbsp; SUCCEED
            </div>
            """,
            unsafe_allow_html=True,
        )

    return nav_selection


def main() -> None:
    inject_custom_styles()

    if "user" not in st.session_state:
        login_view()
        return

    user = st.session_state["user"]

    if user.get("must_change_password") == 1:
        render_first_time_password_modal(user)
        return

    nav_choice = render_sidebar(user)

    if user.get("role") == "Admin":
        if "Operations Dashboard" in nav_choice:
            admin_dashboard_view(user)
        elif "Assign New Task" in nav_choice:
            admin_assign_task_view(user)
        elif "Worker Management" in nav_choice:
            admin_worker_management_view()
    else:
        worker_dashboard_view(user)


if __name__ == "__main__":
    main()
