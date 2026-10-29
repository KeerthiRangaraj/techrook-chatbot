
"""
TechRook Policy Chatbot — FastAPI Backend
=========================================
Authentication, RAG chat, persistent conversation history,
onboarding checklist, and health monitoring.
"""

import os
from pathlib import Path
from typing import Optional, List
from uuid import UUID

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from db import store
from rag_engine import TechRookRAGEngine


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="TechRook Policy Chatbot API",
    description="Role-based HR policy assistant with persistent chat history",
    version="1.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

rag = TechRookRAGEngine()


# ── Authentication helper ─────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    payload = decode_access_token(credentials.credentials)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    email = payload.get("sub")

    if not email:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user = store.get_user(email)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user


# ── Request models ────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    grade: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: Optional[UUID] = None
    # Kept for compatibility with the existing frontend.
    # Backend history is authoritative.
    history: List[ChatMessage] = Field(default_factory=list)


class ConversationRequest(BaseModel):
    title: str = Field(default="New Chat", min_length=1, max_length=120)


class ChecklistUpdate(BaseModel):
    item_id: str
    completed: bool


# ── Authentication routes ─────────────────────────────────────────────────────

@app.post("/api/auth/signup", status_code=201)
def signup(req: SignupRequest):

    email = req.email.strip().lower()

    if not email.endswith("@techrook.in"):
        raise HTTPException(
            status_code=400,
            detail="Must use a @techrook.in email address"
        )

    if store.get_user(email):
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    grade_to_role = {
        "L0": "L0",
        "L1": "L1-L2",
        "L2A": "L1-L2",
        "L2B": "L1-L2",
        "L3": "L3+",
        "L4": "L3+"
    }

    role = grade_to_role.get(req.grade, "L0")

    user = {
        "name": req.name,
        "email": email,
        "password_hash": hash_password(req.password),
        "grade": req.grade,
        "role": role,
        "dept": "Engineering"
    }

    store.create_user(user)

    token = create_access_token({"sub": email})

    return {
        "token": token,
        "user": {
            k: v for k, v in user.items()
            if k != "password_hash"
        }
    }


@app.post("/api/auth/login")
def login(req: LoginRequest):

    email = req.email.strip().lower()

    user = store.get_user(email)

    if not user or not verify_password(
        req.password, user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_access_token({"sub": email})

    return {
        "token": token,
        "user": {
            k: v for k, v in user.items()
            if k != "password_hash"
        }
    }


@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        k: v for k, v in current_user.items()
        if k != "password_hash"
    }


# ── Conversation routes ───────────────────────────────────────────────────────

@app.post("/api/conversations", status_code=201)
def create_conversation(
    req: ConversationRequest,
    current_user: dict = Depends(get_current_user)
):
    conversation = store.create_conversation(
        email=current_user["email"],
        title=req.title.strip() or "New Chat"
    )

    return {"conversation": conversation}


@app.get("/api/conversations")
def list_conversations(
    current_user: dict = Depends(get_current_user)
):
    conversations = store.list_conversations(
        current_user["email"]
    )

    return {"conversations": conversations}


@app.get("/api/conversations/{conversation_id}/messages")
def get_conversation_messages(
    conversation_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    conversation_id = str(conversation_id)
    email = current_user["email"]

    conversation = store.get_conversation(
        email, conversation_id
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    messages = store.get_chat_messages(
        email, conversation_id
    )

    return {
        "conversation": conversation,
        "messages": messages
    }


# ── Chat route ────────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    email = current_user["email"]
    question = req.message.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    # Use an existing conversation, or create one
    # for compatibility with older frontend clients.
    if req.conversation_id is not None:
        conversation_id = str(req.conversation_id)

        conversation = store.get_conversation(
            email, conversation_id
        )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )

    else:
        title = question[:80]

        try:
            conversation = store.create_conversation(
                email=email,
                title=title
            )
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail="Unable to create conversation"
            ) from e

        conversation_id = conversation["id"]

    # Load trusted history from the selected conversation.
    try:
        previous_messages = store.get_chat_messages(
            email, conversation_id
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Unable to load conversation history"
        ) from e

    history = [
        {
            "role": message["role"],
            "content": message["message"]
        }
        for message in previous_messages
        if message["role"] in ("user", "assistant")
    ]

    # Exclude any frontend-only welcome messages.
    # Limit context to the most recent exchanges.
    history = history[-12:]

    try:
        result = await rag.query(
            question=question,
            role=current_user["role"],
            grade=current_user["grade"],
            history=history
        )

    except Exception as e:
        print(
            f"Chat error: {type(e).__name__}: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to generate an answer"
        ) from e

    # Persist both messages in the same conversation.
    # Do not report success if persistence fails.
    try:
        store.add_chat(
            email=email,
            role="user",
            message=question,
            conversation_id=conversation_id
        )

        store.add_chat(
            email=email,
            role="assistant",
            message=result["answer"],
            verified=result.get("verified"),
            conversation_id=conversation_id
        )

    except Exception as e:
        print(
            f"Chat history save error: {type(e).__name__}: {e}"
        )

        raise HTTPException(
            status_code=503,
            detail="Answer generated but could not be saved. Check backend logs."
        ) from e

    return {
        "conversation_id": conversation_id,
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "verified": result.get("verified", False),
        "self_corrected": result.get("self_corrected", False),
        "role_filtered": result.get("role_filtered", False)
    }


# ── Checklist routes ───────────────────────────────────────────────────────────

@app.get("/api/checklist")
def get_checklist(
    current_user: dict = Depends(get_current_user)
):
    return {
        "checklist": store.get_checklist(
            current_user["email"]
        ),
        "email": current_user["email"]
    }


@app.put("/api/checklist")
def update_checklist(
    update: ChecklistUpdate,
    current_user: dict = Depends(get_current_user)
):
    return {
        "checklist": store.set_checklist_item(
            current_user["email"],
            update.item_id,
            update.completed
        )
    }


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "TechRook Policy Chatbot API v1.3",
        "database": store.name
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000"))
    )
