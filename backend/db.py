
"""
db.py — Data layer for TechRook Policy Chatbot
==============================================
Handles:
    - User accounts
    - Onboarding checklists
    - Conversation sessions
    - Persistent chat history

Uses Supabase when SUPABASE_URL and SUPABASE_KEY are configured.
Otherwise falls back to an in-memory store.

IMPORTANT:
The in-memory store loses data when the backend restarts.
"""

import os
from pathlib import Path
from typing import Optional, Dict
from uuid import uuid4
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from auth import hash_password


# ── Supabase configuration ────────────────────────────────────────────────────

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()


# ── Demo users ────────────────────────────────────────────────────────────────

DEMO_USERS = [
    {
        "name": "Alice Sharma",
        "email": "alice@techrook.in",
        "grade": "L0",
        "role": "L0",
        "dept": "Engineering"
    },
    {
        "name": "Bob Iyer",
        "email": "bob@techrook.in",
        "grade": "L2A",
        "role": "L1-L2",
        "dept": "Product"
    },
    {
        "name": "Carol Menon",
        "email": "carol@techrook.in",
        "grade": "L3",
        "role": "L3+",
        "dept": "Cybersecurity"
    },
]


DEMO_CHECKLISTS = {
    "alice@techrook.in": {},

    "bob@techrook.in": {
        "docs": True,
        "icici": True
    },

    "carol@techrook.in": {
        "docs": True,
        "icici": True,
        "cybervault": True,
        "aiethics": True,
        "posh": True,
        "mfa": True
    },
}


def _demo_user(user: dict) -> dict:
    return {
        **user,
        "password_hash": hash_password("pass123")
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── In-memory database ────────────────────────────────────────────────────────

class MemoryStore:

    name = "in-memory (data resets on restart)"

    def __init__(self):

        self.users: Dict[str, dict] = {
            user["email"]: _demo_user(user)
            for user in DEMO_USERS
        }

        self.checklists: Dict[str, dict] = {
            email: dict(items)
            for email, items in DEMO_CHECKLISTS.items()
        }

        self.conversations: Dict[str, dict] = {}

        self.chats = []

    # ── Users ─────────────────────────────────────────────────────────────────

    def get_user(self, email: str) -> Optional[dict]:
        return self.users.get(email)

    def create_user(self, user: dict) -> None:

        self.users[user["email"]] = user

        self.checklists[user["email"]] = {}

    # ── Checklist ─────────────────────────────────────────────────────────────

    def get_checklist(self, email: str) -> dict:

        return dict(
            self.checklists.get(email, {})
        )

    def set_checklist_item(
        self,
        email: str,
        item_id: str,
        completed: bool
    ) -> dict:

        self.checklists.setdefault(email, {})

        self.checklists[email][item_id] = completed

        return dict(self.checklists[email])

    # ── Conversations ─────────────────────────────────────────────────────────

    def create_conversation(
        self,
        email: str,
        title: str = "New Chat"
    ) -> dict:

        conversation_id = str(uuid4())

        now = utc_now()

        conversation = {
            "id": conversation_id,
            "email": email,
            "title": title,
            "created_at": now,
            "updated_at": now
        }

        self.conversations[conversation_id] = conversation

        return dict(conversation)

    def list_conversations(self, email: str) -> list:

        conversations = [
            dict(conversation)
            for conversation in self.conversations.values()
            if conversation["email"] == email
        ]

        return sorted(
            conversations,
            key=lambda c: c["updated_at"],
            reverse=True
        )

    def get_conversation(
        self,
        email: str,
        conversation_id: str
    ) -> Optional[dict]:

        conversation = self.conversations.get(conversation_id)

        if not conversation:
            return None

        if conversation["email"] != email:
            return None

        return dict(conversation)

    # ── Chat history ──────────────────────────────────────────────────────────

    def get_chat_messages(
        self,
        email: str,
        conversation_id: str
    ) -> list:

        conversation = self.get_conversation(
            email,
            conversation_id
        )

        if not conversation:
            return []

        return [
            dict(message)
            for message in self.chats
            if message["email"] == email
            and message["conversation_id"] == conversation_id
        ]

    def add_chat(
        self,
        email: str,
        role: str,
        message: str,
        verified: Optional[bool] = None,
        conversation_id: Optional[str] = None
    ) -> None:

        conversation = self.get_conversation(
            email,
            conversation_id
        )

        if not conversation:
            raise ValueError(
                "Conversation not found or access denied"
            )

        self.chats.append({
            "id": len(self.chats) + 1,
            "email": email,
            "conversation_id": conversation_id,
            "role": role,
            "message": message,
            "verified": verified,
            "created_at": utc_now()
        })

        self.conversations[conversation_id]["updated_at"] = utc_now()


# ── Supabase database ─────────────────────────────────────────────────────────

class SupabaseStore:

    name = "Supabase"

    def __init__(self, url: str, key: str):

        from supabase import create_client

        self.sb = create_client(url, key)

        # Check that the users table exists
        self.sb.table("users") \
            .select("email") \
            .limit(1) \
            .execute()

        # Check that the conversations table exists
        self.sb.table("conversations") \
            .select("id") \
            .limit(1) \
            .execute()

        self._seed_demo_users()

    # ── Demo data ─────────────────────────────────────────────────────────────

    def _seed_demo_users(self):

        for user in DEMO_USERS:

            if not self.get_user(user["email"]):

                self.create_user(
                    _demo_user(user)
                )

                for item_id, completed in DEMO_CHECKLISTS[
                    user["email"]
                ].items():

                    self.set_checklist_item(
                        user["email"],
                        item_id,
                        completed
                    )

    # ── Users ─────────────────────────────────────────────────────────────────

    def get_user(self, email: str) -> Optional[dict]:

        result = (
            self.sb.table("users")
            .select("*")
            .eq("email", email)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    def create_user(self, user: dict) -> None:

        row = {
            key: user[key]
            for key in (
                "email",
                "name",
                "password_hash",
                "grade",
                "role",
                "dept"
            )
        }

        self.sb.table("users") \
            .insert(row) \
            .execute()

    # ── Checklist ─────────────────────────────────────────────────────────────

    def get_checklist(self, email: str) -> dict:

        result = (
            self.sb.table("checklist")
            .select("item_id,completed")
            .eq("email", email)
            .execute()
        )

        return {
            row["item_id"]: row["completed"]
            for row in result.data
        }

    def set_checklist_item(
        self,
        email: str,
        item_id: str,
        completed: bool
    ) -> dict:

        self.sb.table("checklist").upsert(
            {
                "email": email,
                "item_id": item_id,
                "completed": completed
            },
            on_conflict="email,item_id"
        ).execute()

        return self.get_checklist(email)

    # ── Conversations ─────────────────────────────────────────────────────────

    def create_conversation(
        self,
        email: str,
        title: str = "New Chat"
    ) -> dict:

        result = (
            self.sb.table("conversations")
            .insert({
                "email": email,
                "title": title
            })
            .execute()
        )

        return result.data[0]

    def list_conversations(self, email: str) -> list:

        result = (
            self.sb.table("conversations")
            .select("*")
            .eq("email", email)
            .order("updated_at", desc=True)
            .execute()
        )

        return result.data

    def get_conversation(
        self,
        email: str,
        conversation_id: str
    ) -> Optional[dict]:

        result = (
            self.sb.table("conversations")
            .select("*")
            .eq("email", email)
            .eq("id", conversation_id)
            .limit(1)
            .execute()
        )

        return result.data[0] if result.data else None

    # ── Chat history ──────────────────────────────────────────────────────────

    def get_chat_messages(
        self,
        email: str,
        conversation_id: str
    ) -> list:

        conversation = self.get_conversation(
            email,
            conversation_id
        )

        if not conversation:
            return []

        result = (
            self.sb.table("chat_history")
            .select("*")
            .eq("email", email)
            .eq("conversation_id", conversation_id)
            .order("id")
            .execute()
        )

        return result.data

    def add_chat(
        self,
        email: str,
        role: str,
        message: str,
        verified: Optional[bool] = None,
        conversation_id: Optional[str] = None
    ) -> None:

        conversation = self.get_conversation(
            email,
            conversation_id
        )

        if not conversation:
            raise ValueError(
                "Conversation not found or access denied"
            )

        self.sb.table("chat_history").insert({
            "email": email,
            "conversation_id": conversation_id,
            "role": role,
            "message": message,
            "verified": verified
        }).execute()

        self.sb.table("conversations").update({
            "updated_at": utc_now()
        }).eq(
            "id", conversation_id
        ).eq(
            "email", email
        ).execute()


# ── Store initialization ──────────────────────────────────────────────────────

def create_store():

    if (
        SUPABASE_URL
        and SUPABASE_KEY
        and "your-" not in SUPABASE_URL
    ):

        try:

            database = SupabaseStore(
                SUPABASE_URL,
                SUPABASE_KEY
            )

            print("Database: connected to Supabase")

            return database

        except Exception as error:

            print(
                f"Supabase unavailable: "
                f"{type(error).__name__}: {error}"
            )

            print(
                "Check your Supabase credentials "
                "and database schema."
            )

            print(
                "Using in-memory store instead."
            )

    else:

        print(
            "SUPABASE_URL or SUPABASE_KEY not configured."
        )

        print(
            "Using in-memory store."
        )

    return MemoryStore()


store = create_store()
