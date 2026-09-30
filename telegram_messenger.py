from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv


DEFAULT_PORTAL_URL = "http://localhost:8501"
load_dotenv(Path(__file__).with_name(".env"), override=False)


def clean_telegram_handle(handle: str) -> str:
    """Cleans a telegram handle or username, stripping leading @ if present."""
    if not handle:
        return ""
    return handle.strip().lstrip("@")


def get_telegram_share_url(message: str, portal_url: str = DEFAULT_PORTAL_URL, username: str = "") -> str:
    """Generates direct Telegram share or chat URL."""
    encoded_text = urllib.parse.quote(message)
    encoded_url = urllib.parse.quote(portal_url)
    clean_user = clean_telegram_handle(username)
    if clean_user and not clean_user.startswith("-") and not clean_user.isdigit():
        # Share directly targeting telegram link
        return f"https://t.me/{clean_user}"
    return f"https://t.me/share/url?url={encoded_url}&text={encoded_text}"


def send_telegram_bot_message(chat_id: str, message: str) -> Tuple[bool, str]:
    """
    Sends automated message using Telegram Bot API if TELEGRAM_BOT_TOKEN is set.
    Uses standard library urllib.request without external dependencies.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        return False, "TELEGRAM_BOT_TOKEN is not configured in environment."
    if not chat_id:
        return False, "Recipient Telegram Chat ID or username is empty."

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id.strip(),
        "text": message,
        "parse_mode": "Markdown",
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("ok"):
                return True, "Message sent successfully."
            return False, result.get("description", "Telegram API returned error.")
    except Exception as e:
        return False, str(e)


# Message formatters for Telegram

def create_worker_welcome_message(
    full_name: str,
    user_id: str,
    temp_password: str,
    portal_url: str = DEFAULT_PORTAL_URL
) -> str:
    return (
        f"👋 *Welcome to TaskTrack, {full_name}!* \n\n"
        f"Your worker account has been created. Here are your login credentials:\n"
        f"🔹 *User ID:* `{user_id}`\n"
        f"🔹 *Temporary Password:* `{temp_password}`\n"
        f"🔗 *Login Portal:* {portal_url}\n\n"
        f"⚠️ *Important:* You will be asked to set your permanent private password during first login.\n"
        f"Please do not share your temporary credentials."
    )


def create_task_assignment_message(
    task_uid: str,
    title: str,
    priority: str,
    due_datetime: str,
    proof_requirements: str,
    description: str = "",
    portal_url: str = DEFAULT_PORTAL_URL
) -> str:
    priority_emojis = {
        "Low": "🟢",
        "Medium": "🟡",
        "High": "🟠",
        "Urgent": "🔴"
    }
    p_emoji = priority_emojis.get(priority, "📌")
    desc_snippet = f"\n📝 *Details:* {description}" if description else ""

    return (
        f"📋 *New Task Assigned: {title}*\n\n"
        f"🆔 *Task ID:* `{task_uid}`\n"
        f"{p_emoji} *Priority:* {priority}\n"
        f"⏰ *Due Date & Time:* {due_datetime}\n"
        f"📸 *Proof Required:* {proof_requirements}"
        f"{desc_snippet}\n\n"
        f"👉 *Action:* Please log in to accept the task and upload your proof when finished:\n"
        f"🔗 {portal_url}"
    )


def create_rejection_message(
    task_uid: str,
    title: str,
    rejection_comment: str,
    portal_url: str = DEFAULT_PORTAL_URL
) -> str:
    return (
        f"⚠️ *Task Resubmission Requested: {title}*\n\n"
        f"🆔 *Task ID:* `{task_uid}`\n"
        f"❌ *Status:* Rejected / Revision Needed\n"
        f"💬 *Supervisor Comments:*\n\"{rejection_comment}\"\n\n"
        f"🔄 Please log in to review feedback and upload updated proof:\n"
        f"🔗 {portal_url}"
    )


def create_approval_message(
    task_uid: str,
    title: str,
    review_comment: str = ""
) -> str:
    comment_part = f"\n💬 *Supervisor Feedback:* {review_comment}" if review_comment else ""
    return (
        f"✅ *Task Approved: {title}*\n\n"
        f"🆔 *Task ID:* `{task_uid}`\n"
        f"🎉 *Status:* Approved & Verified!{comment_part}\n\n"
        f"Thank you for your prompt submission."
    )
