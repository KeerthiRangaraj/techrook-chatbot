"""
rag_engine.py — LangChain RAG with Self-Correction Loop
=========================================================
Pipeline:
  1. Load & chunk the TechRook Employee Handbook
  2. Embed chunks → FAISS vector store
  3. Per query: retrieve top-k relevant chunks
  4. Build role-filtered context
  5. Generate answer via the configured LLM (Groq or Anthropic)
  6. SELF-CORRECTION: verify answer against source chunks
  7. If verification fails → regenerate with stricter prompt
  8. Return final answer + sources + verification status
"""

import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")   # load backend/.env regardless of where you run from

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.documents import Document

# Embeddings — sentence-transformers (free, runs locally)
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        EMBEDDINGS_AVAILABLE = True
    except ImportError:
        EMBEDDINGS_AVAILABLE = False

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()   # "groq" or "anthropic"
VERIFY_ANSWERS = os.getenv("VERIFY_ANSWERS", "true").strip().lower() in ("1", "true", "yes")
HANDBOOK_PATH = Path(__file__).parent.parent / "handbook" / "techrook_handbook.txt"


def build_llm():
    """Create the chat model from environment variables."""
    if LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not key or "your" in key:
            raise RuntimeError("ANTHROPIC_API_KEY is missing in backend/.env")
        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
            api_key=key, max_tokens=1024, temperature=0.1,
        )
    if LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq
        key = os.getenv("GROQ_API_KEY", "").strip()
        if not key or "your_key" in key:
            raise RuntimeError("GROQ_API_KEY is missing in backend/.env (get one at console.groq.com/keys)")
        return ChatGroq(
            # NOTE: Groq retired llama-3.3-70b-versatile on 16 Aug 2026.
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            api_key=key, max_tokens=4096, temperature=0.1,
        )
    raise RuntimeError(f"Unknown LLM_PROVIDER '{LLM_PROVIDER}' — use 'groq' or 'anthropic'")


def _text(response) -> str:
    """Return plain text from an LLM response (content may be a str or a list of blocks)."""
    content = getattr(response, "content", response)
    if isinstance(content, list):
        content = "".join(
            b.get("text", "") if isinstance(b, dict) else str(b) for b in content
        )
    # Some reasoning models wrap thoughts in <think> tags — strip them
    content = re.sub(r"<think>.*?</think>", "", str(content), flags=re.S)
    return content.strip()


# ── Role access control map ───────────────────────────────────────────────────
ROLE_RESTRICTED_TOPICS = {
    "L0": [
        "recruitment", "hiring", "offer letter drafting", "salary negotiation",
        "disciplinary administration", "termination process", "performance calibration",
        "ICC administration", "team excellence nomination", "BGV administration"
    ],
    "L1-L2": [
        "recruitment strategy", "offer letter drafting", "ICC composition administration",
        "disciplinary hearing", "performance calibration"
    ],
    "L3+": []  # Managers can see everything
}


class TechRookRAGEngine:
    def __init__(self):
        self.vectorstore: Optional[Any] = None
        self.llm = build_llm()
        self._initialized = False
        self._initialize()

    def _initialize(self):
        """Load handbook, chunk it, create vector store."""
        print("🔄 Initializing TechRook RAG engine...")

        # Load handbook text
        if HANDBOOK_PATH.exists():
            with open(HANDBOOK_PATH, "r", encoding="utf-8") as f:
                handbook_text = f.read()
        else:
            # Fallback: use embedded handbook summary
            handbook_text = self._get_embedded_handbook()
            print("⚠️  Handbook file not found — using embedded knowledge base")

        # Chunk the document — larger chunks reduce boundary gaps where answers
        # span section boundaries; overlap ensures no sentence is lost at a split
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " "]
        )
        chunks = splitter.create_documents([handbook_text])
        print(f"✅ Created {len(chunks)} document chunks")

        # Create embeddings and vector store
        self.chunks = chunks   # always kept for the keyword fallback
        if EMBEDDINGS_AVAILABLE:
            try:
                embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    model_kwargs={"device": "cpu"}
                )
                self.vectorstore = FAISS.from_documents(chunks, embeddings)
                print("✅ FAISS vector store created with sentence-transformers embeddings")
            except Exception as e:
                print(f"⚠️  Embedding model failed to load ({type(e).__name__}: {e}) — using keyword retrieval fallback")
        else:
            print("⚠️  langchain-huggingface not installed — using keyword retrieval fallback")

        self._initialized = True
        print("✅ RAG engine ready!")

    def _retrieve(self, query: str, k: int = 7) -> List[Document]:
        """Retrieve top-k relevant chunks for the query."""
        if self.vectorstore:
            return self.vectorstore.similarity_search(query, k=k)
        else:
            # Keyword fallback
            query_words = set(query.lower().split())
            scored = []
            for chunk in self.chunks:
                chunk_words = set(chunk.page_content.lower().split())
                score = len(query_words & chunk_words)
                scored.append((score, chunk))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [c for _, c in scored[:k]]

    def _is_role_restricted(self, question: str, role: str) -> bool:
        """Check if the question asks about role-restricted content."""
        restricted = ROLE_RESTRICTED_TOPICS.get(role, [])
        question_lower = question.lower()
        return any(topic in question_lower for topic in restricted)

    def _build_system_prompt(self, role: str, grade: str, context_chunks: List[Document]) -> str:
        role_instructions = {
            "L0": """You are assisting an L0 Trainee/Intern.
ALLOWED TOPICS: onboarding, joining documents, certifications, basic leave (CL/SL),
attendance, security basics, POSH awareness, dress code, cafeteria, accommodation.
BLOCKED TOPICS: recruitment administration, disciplinary process administration,
performance calibration, ICC administration, manager-only awards nomination.""",

            "L1-L2": """You are assisting an L1/L2 Employee (Executive or Senior/Manager level).
ALLOWED TOPICS: All standard employee policies — full leave entitlements, salary components,
travel entitlements by grade, referral bonuses, performance appraisal (as ratee),
BYOD (L2A/L2B), WFH stipend (L1+), grievance redressal, POSH, assets, non-compete.
BLOCKED TOPICS: Recruitment strategy/administration, disciplinary hearing administration.""",

            "L3+": """You are assisting an L3+ Director/Manager.
ALLOWED TOPICS: ALL policies — recruitment, BGV, offer letters, performance rating
administration, calibration, disciplinary process (all 4 levels), POSH ICC roles,
Spot Award administration, Team Excellence nomination, all travel/financial entitlements."""
        }

        context_text = "\n\n---\n\n".join([
            f"[CHUNK {i+1}]\n{doc.page_content}"
            for i, doc in enumerate(context_chunks)
        ])

        return f"""You are the TechRook Policy Assistant — a zero-hallucination HR chatbot for TechRook Technologies Pvt. Ltd. (Employee Handbook 2026).

ROLE CONTEXT:
{role_instructions.get(role, role_instructions["L0"])}
Current user grade: {grade}

STRICT RULES:
1. Answer ONLY using the RETRIEVED CONTEXT provided below. Never invent, extrapolate, or assume information not in the context.
2. Every response MUST end with: "📋 Source: [Chapter Name/Number], TechRook Employee Handbook 2026."
3. If the context does not contain the answer, say: "I don't have specific information on that in the handbook. Please contact hr@techrook.in for clarification. 📋 Source: Chapter 40 — HR Portal and Contacts."
4. For off-topic or abusive questions: "I am a dedicated TechRook Policy Assistant. I cannot answer that, but I can help you with your benefits or onboarding."
5. For role-restricted topics: "This policy area is not applicable to your current grade. Please speak with your Buddy Manager or HR."
6. Be concise, precise, and professional. Use bullet points for multi-item answers.
7. Always state exact numbers (INR amounts, days, %) as given in the context.
8. Do not add warnings, disclaimers, or suggestions beyond what is in the handbook.

RETRIEVED CONTEXT FROM TECHROOK EMPLOYEE HANDBOOK 2026:
{context_text}"""

    def _build_verification_prompt(self, question: str, answer: str, context: str) -> str:
        return f"""You are a fact-checker for a corporate HR chatbot.

ORIGINAL QUESTION: {question}

GENERATED ANSWER: {answer}

SOURCE CONTEXT: {context}

Task: Verify if the answer is:
1. Fully supported by the source context (no invented facts)
2. Contains no numbers/dates/policies not present in the context
3. Does not answer a question the context doesn't cover

Respond with ONLY one of:
- "VERIFIED: [brief reason]" — if the answer is accurate and grounded
- "FAILED: [specific issue]" — if any part of the answer is not supported

Be strict. Even one unsupported claim = FAILED."""

    async def query(self, question: str, role: str, grade: str, history: List[Dict]) -> Dict:
        """Full RAG pipeline with self-correction."""

        # 1. Role restriction check
        if self._is_role_restricted(question, role):
            return {
                "answer": "This policy area is not applicable to your current grade level. Please speak with your Buddy Manager or HR Department for more information.\n\n📋 Source: Chapter 6 — Employee Grade Classification, TechRook Employee Handbook 2026.",
                "sources": [],
                "verified": True,
                "role_filtered": True
            }

        # 2. Retrieve relevant chunks — k=7 gives broader coverage for multi-part answers
        docs = self._retrieve(question, k=7)
        sources = [doc.page_content[:120] + "..." for doc in docs]

        # 3. Build messages for LLM
        system_prompt = self._build_system_prompt(role, grade, docs)

        # Build conversation history (last 6 messages for context window efficiency)
        messages = []
        for msg in history[-6:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=question))

        # 4. Generate initial answer
        response = await self.llm.ainvoke(
            [SystemMessage(content=system_prompt)] + messages
        )
        initial_answer = _text(response)
        if not initial_answer:
            raise RuntimeError("The language model returned an empty answer")

        if not VERIFY_ANSWERS:
            return {"answer": initial_answer, "sources": sources, "verified": True, "self_corrected": False}

        # 5. SELF-CORRECTION LOOP — verify answer against source chunks
        context_text = "\n".join([doc.page_content for doc in docs])
        final_answer = initial_answer
        verified = False
        self_corrected = False

        try:
            verification = await self.llm.ainvoke([
                HumanMessage(content=self._build_verification_prompt(question, initial_answer, context_text))
            ])
            verified = _text(verification).upper().startswith("VERIFIED")

            # 6. If verification failed → regenerate with stricter prompt, then re-verify
            if not verified:
                print(f"⚠️  Self-correction triggered: {_text(verification)[:200]}")
                strict_system = system_prompt + (
                    "\n\nCRITICAL: Your previous answer contained unverified information. "
                    "Regenerate the answer using ONLY the exact facts in the retrieved context. "
                    "If unsure, direct the user to hr@techrook.in."
                )
                retry = await self.llm.ainvoke([SystemMessage(content=strict_system)] + messages)
                retry_answer = _text(retry)
                if retry_answer:
                    final_answer = retry_answer
                    self_corrected = True
                    recheck = await self.llm.ainvoke([
                        HumanMessage(content=self._build_verification_prompt(question, final_answer, context_text))
                    ])
                    verified = _text(recheck).upper().startswith("VERIFIED")
        except Exception as e:
            # Verification is best-effort: never lose a good answer because the checker failed
            print(f"⚠️  Verification step failed ({type(e).__name__}: {e}) — returning unverified answer")

        return {
            "answer": final_answer,
            "sources": sources,
            "verified": verified,
            "self_corrected": self_corrected
        }

    def _get_embedded_handbook(self) -> str:
        """Fallback embedded handbook content if file not present."""
        return """
TechRook Technologies Pvt. Ltd. — Employee Handbook 2026

Chapter 1: Company Overview
TechRook Technologies Pvt. Ltd. was founded on 14 March 2018. HQ: TechRook Tower, Plot No. 12, Phase II, HITEC City, Madhapur, Hyderabad – 500 081. Products: OmniStream AI and CyberVault 360. Employees: 800+.

Chapter 6: Grade Classification
L0: Trainee/Intern (Fixed-term). L1: Executive/Consultant (Permanent/Contract). L2A: Senior Executive (Permanent). L2B: Manager/Lead (Permanent). L3: Director/SBU Head (Permanent). L4: Executive Leadership (Permanent).

Chapter 8: Joining Documents
Mandatory for all: Aadhaar Card, PAN Card, Degree/Diploma Certificates, Relieving Letter (previous employer), 3 salary slips, UAN, 2 passport photos, Bank account details (IFSC + cancelled cheque), Form 12B (if mid-year joiner). Deadline: 3 working days. Salary held until documents received.

Chapter 9: Mandatory Certifications (First 15 Days)
CyberVault Basics – Information Security Fundamentals: 6 hours, 40-question MCQ, 70% minimum, university.techrook.in, valid 12 months, all grades.
AI Ethics 101 – Responsible AI at TechRook: 4 hours, 25-question MCQ + case study, 65% minimum, university.techrook.in, valid 12 months, all grades.

Chapter 11: Induction Schedule
Day 1: IT setup, ICICI salary account activation. Day 2: Product demos. Day 3: HR policies, POSH, Zero-Trust. Day 4: Department orientation. Day 5: CEO Welcome Session, TechRook University enrollment.

Chapter 12: Leave Entitlements
Casual Leave: 12 days/year, no carry-forward, not encashable, 1 day/month accrual.
Privilege Leave: 15 days/year, max 30 days carry-forward, encashable on separation, 3.75 days/quarter after confirmation.
Sick Leave: 10 days/year, max 15 days carry-forward, not encashable.

Chapter 14: Attendance
Core hours: 09:00–18:30 IST, Mon–Fri. Weekly off: Saturday and Sunday. Min 8.5 hours/day. Late after 09:15 IST. 3 lates = 1 CL deducted. 7+ consecutive AWOL = automatic termination.

Chapter 15: Salary
Credited last working day each month to ICICI Bank salary account. Components: Basic (40-50% CTC), HRA (50% Basic metro), Special Allowance, LTA (1 month Basic/year), Performance Bonus (0-30% CTC semi-annually).

Chapter 16: Statutory Benefits
PF: 12% employee + 12% TechRook. ESIC: if gross ≤ INR 21,000. Gratuity: after 5 years continuous service; (Last Basic/26) × 15 × years. GPA Insurance: INR 25 Lakhs all employees. Mediclaim: INR 5 Lakhs for L1+ (not ESIC), employee + 3 dependents.

Chapter 17: Additional Benefits
Referral Bonus: L0=INR 15,000; L1=INR 25,000; L2A=INR 40,000; L2B+=INR 60,000. Wedding Gift: L0-L1=INR 15,000; L2A+=INR 25,000. WFH Stipend: INR 50,000 one-time for L1+ remote/hybrid.

Chapter 18: Probation
L0: per Internship Agreement. L1-L2B: 6 months. L3-L4: 3 months. Extension: max 3 months, once only.

Chapter 19: Notice Period
L0: 30 days. L1-L2A: 30 days. L2B-L4 confirmed: 60 days. Buyout = monthly gross / 30 per day.

Chapter 23: Security Policy
Zero-Trust model. MFA mandatory (2 devices within 3 working days). Password: min 14 chars, change every 90 days. VPN required for external access. Session timeout: 15 min. BYOD: L0-L1 not permitted; L2A with approval; L2B+ via MDM.

Chapter 26: POSH Policy
ICC at each office. Complaint to posh.icc@techrook.in within 90 days of incident. Inquiry within 60 days. Findings within 10 working days. Full confidentiality.

Chapter 28: Conduct & Discipline
Level 1: Verbal Warning. Level 2: Written Warning (HR). Level 3: Final Warning + deduction/suspension. Level 4: Termination.

Chapter 31: Travel Policy
Accommodation (INR/night): L0: Tier1=1500, Tier2=1000, Tier3=750. L1: 3000/2000/1500. L2A: 4500/3000/2000. L2B: 6000/4000/2500. L3: 8000/5500/3500.
Transport: L0=Sleeper train; L1=3AC; L2A=2AC; L2B=economy air>500km; L3=1AC+economy; L4=business class.

Chapter 33: Performance
Year: April–March. Ratings: 5=Exceptional(100% bonus); 4=High Performer(75%); 3=Meets Expectations(50%); 2=Needs Improvement(0%+PIP); 1=Below Expectations(0%+termination review).

Chapter 38: Special Leave
Maternity: 26 weeks paid. Paternity: 10 working days paid (after 6 months service). Bereavement: 5 working days paid.

Chapter 40: Key Contacts
HR: hr@techrook.in | +91-40-6800-1250. IT Support: itsupport@techrook.in | +91-40-6800-1300. POSH/ICC: posh.icc@techrook.in. EAP: eap@techrook.in | +91-80-4500-2299. Security: security@techrook.in.
"""