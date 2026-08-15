import requests
import os
import re
import io
from telegram.request import HTTPXRequest
import whisper
import edge_tts
WHISPER_MODEL = "base"
import ast
import math
import asyncio
import hashlib
import pytesseract
import os
os.makedirs(
    "uploads",
    exist_ok=True
)
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
from PIL import Image
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from google import genai

import ollama

import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

from PIL import Image

from PyPDF2 import PdfReader

from telegram import (
    Update,
    InputFile
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from database import (
    SessionLocal,
    User,
    Conversation
)
from sqlalchemy import text

# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen3:4b"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen3:1.7b"
)

ADMIN_USER_ID = os.getenv(
    "ADMIN_USER_ID"
)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


if not TELEGRAM_BOT_TOKEN:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN is missing"
    )


if not GEMINI_API_KEY:
    print(
        "⚠️ GEMINI_API_KEY missing"
    )


# =========================================================
# GEMINI
# =========================================================

client = None

if GEMINI_API_KEY:

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_INSTRUCTION = """
You are a professional AI Engineering Assistant.

You help users with:

Electrical Engineering
Electronics
Mathematics
Physics
Programming
Computer Science
Data Science
Engineering calculations
Education
Exam preparation
General knowledge
Writing
Research
Technical documentation

Rules:

1. Answer clearly and professionally.
2. Explain difficult topics step by step.
3. Show formulas when useful.
4. Include units in engineering calculations.
5. For programming questions provide runnable code.
6. For mathematics show calculation steps.
7. For engineering questions provide practical examples.
8. Do not invent facts.
9. If the question is ambiguous, ask for clarification.
10. Keep formatting clean and readable.
"""

MATH_INSTRUCTION = """
For mathematics questions, respond in a professional mathematical style
suitable for a textbook, university assignment, examination solution,
or professional AI tutoring response.

MATHEMATICAL FORMATTING RULES:

1. Use standard mathematical notation.
2. Use LaTeX for all mathematical expressions and equations.
3. Use \\( ... \\) for inline mathematics.
4. Use \\[ ... \\] or aligned display equations for important formulas
   and multi-step calculations.
5. Use standard symbols such as:
   \\alpha, \\beta, \\theta, \\phi, \\Delta, \\pi,
   \\in, \\notin, \\subset, \\cup, \\cap,
   \\leq, \\geq, \\neq, \\approx,
   \\Rightarrow, \\Longrightarrow,
   \\therefore, \\because,
   \\perp, \\parallel, \\angle,
   \\circ, \\Omega, \\sqrt{}, \\sum, \\int
6. Use proper superscripts and subscripts.
7. Use \\frac{}{} for fractions.
8. Use \\sqrt{} for roots.
9. Use aligned equations for derivations.
10. Keep equation notation consistent throughout the solution.
11. Define every variable or symbol before using it.
12. Use degree notation correctly, e.g. \\(90^\\circ\\).
13. Use proper geometric notation such as:
    \\(\\triangle ABC\\)
    \\(\\angle ABC\\)
    \\(\\overline{AB}\\)
    \\(\\widehat{AB}\\)
14. Name the relevant theorem, law, or property when appropriate.
15. Do not skip important logical steps.
16. Do not introduce assumptions that are not supported by the question.
17. For numerical problems, use this structure:

    Given:
    [Known quantities]

    Required:
    [Quantity to be determined]

    Formula:
    [Relevant formula]

    Substitution:
    [Values substituted into the formula]

    Calculation:
    [Step-by-step calculation]

    Therefore:
    [Final answer]

18. For geometry proofs, use:
    Given → Construction/Observation → Theorem/Property → Derivation → Conclusion.

19. For algebra, show each meaningful transformation on a separate line.

20. For calculus, clearly identify:
    Given function → Required quantity → Rule/formula → Differentiation/integration → Result.

21. For probability and statistics, clearly define events, variables,
    formulas, substitutions, and the final result.

22. Highlight the final answer using:
    \\boxed{...}

23. Never use raw or broken LaTeX such as:
    $$...$$
    \\text{}
    unclosed braces
    malformed fractions
    inconsistent delimiters

24. Keep the explanation professional and precise.
25. Avoid unnecessary repetition.
26. End with a clearly labeled final result when appropriate.

Example style:

### Given

\\[
\\angle ROS = \\theta
\\]

By the Inscribed Angle Theorem,

\\[
\\angle RPS
=
\\frac{1}{2}\\angle ROS
=
\\frac{\\theta}{2}.
\\]

Since

\\[
PS \\perp QT,
\\]

we obtain

\\[
\\angle PST = 90^\\circ.
\\]

Using the angle-sum property of triangle \\(\\triangle PST\\),

\\[
\\angle PTS + \\angle SPT + \\angle PST = 180^\\circ.
\\]

Therefore,

\\[
\\angle RTS + \\frac{\\theta}{2} + 90^\\circ = 180^\\circ.
\\]

Hence,

\\[
\\begin{aligned}
\\angle RTS
&= 180^\\circ - 90^\\circ - \\frac{\\theta}{2} \\\\
&= 90^\\circ - \\frac{\\theta}{2}.
\\end{aligned}
\\]

Thus,

\\[
\\boxed{
\\angle RTS
=
90^\\circ - \\frac{\\theta}{2}
=
\\frac{180^\\circ-\\theta}{2}
}
\\]

The final answer must be mathematically rigorous, logically justified,
and professionally formatted.
"""
OLLAMA_SYSTEM = """
You are a helpful AI assistant.
Answer clearly and professionally.
For mathematics use readable symbols.
For coding provide correct runnable code.
For engineering include formulas and units.
Do not use LaTeX.
"""

SYSTEM_INSTRUCTION = """
You are a professional AI Engineering Assistant.

You help users with:
• Engineering
• Coding
• Mathematics
• Physics
• Education
• General knowledge

Give accurate, clear, professional answers.
Do not invent information.
"""

SYSTEM_INSTRUCTION += MATH_INSTRUCTION

#=====
import re


def telegram_math(text: str) -> str:
    if not text:
        return ""

    # --------------------------------------------------
    # Remove LaTeX delimiters
    # --------------------------------------------------
    text = re.sub(r"\$\$(.*?)\$\$", r"\1", text, flags=re.S)
    text = re.sub(r"\$(.*?)\$", r"\1", text, flags=re.S)

    text = text.replace(r"\(", "")
    text = text.replace(r"\)", "")
    text = text.replace(r"\[", "")
    text = text.replace(r"\]", "")

    # --------------------------------------------------
    # Basic LaTeX commands -> Unicode
    # --------------------------------------------------
    replacements = {
        r"\times": "×",
        r"\cdot": "·",
        r"\div": "÷",
        r"\pm": "±",
        r"\mp": "∓",
        r"\leq": "≤",
        r"\geq": "≥",
        r"\neq": "≠",
        r"\approx": "≈",
        r"\equiv": "≡",
        r"\propto": "∝",

        r"\rightarrow": "→",
        r"\Rightarrow": "⇒",
        r"\leftarrow": "←",
        r"\Leftarrow": "⇐",

        r"\angle": "∠",
        r"\triangle": "△",
        r"\perp": "⊥",
        r"\parallel": "∥",

        r"\therefore": "∴",
        r"\because": "∵",

        r"\infty": "∞",
        r"\pi": "π",

        r"\alpha": "α",
        r"\beta": "β",
        r"\gamma": "γ",
        r"\delta": "δ",
        r"\Delta": "Δ",
        r"\theta": "θ",
        r"\phi": "φ",
        r"\varphi": "φ",
        r"\lambda": "λ",
        r"\mu": "μ",
        r"\sigma": "σ",
        r"\omega": "ω",
        r"\Omega": "Ω",

        r"\circ": "°",
        r"\degree": "°",

        r"\sqrt": "√",
        r"\boxed": "",

        r"\mathbf": "",
        r"\mathrm": "",
        r"\mathit": "",
        r"\textbf": "",
        r"\textit": "",
        r"\text": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # --------------------------------------------------
    # Fractions
    # \frac{a}{b} -> a / b
    # --------------------------------------------------
    frac_pattern = re.compile(
        r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}"
    )

    previous = None

    while previous != text:
        previous = text
        text = frac_pattern.sub(
            lambda m: f"({m.group(1)} ÷ {m.group(2)})",
            text
        )

    # --------------------------------------------------
    # Superscripts
    # --------------------------------------------------
    superscript_map = str.maketrans(
        "0123456789+-=()",
        "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾"
    )

    text = re.sub(
        r"\^\{([^{}]+)\}",
        lambda m: m.group(1).translate(superscript_map),
        text
    )

    text = re.sub(
        r"\^([0-9+\-=()])",
        lambda m: m.group(1).translate(superscript_map),
        text
    )

    # --------------------------------------------------
    # Subscripts
    # --------------------------------------------------
    subscript_map = str.maketrans(
        "0123456789+-=()",
        "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎"
    )

    text = re.sub(
        r"_\{([^{}]+)\}",
        lambda m: m.group(1).translate(subscript_map),
        text
    )

    text = re.sub(
        r"_([0-9+\-=()])",
        lambda m: m.group(1).translate(subscript_map),
        text
    )

    # --------------------------------------------------
    # Remove remaining braces / LaTeX commands
    # --------------------------------------------------
    text = text.replace("{", "")
    text = text.replace("}", "")

    text = re.sub(
        r"\\[A-Za-z]+",
        "",
        text
    )

    # --------------------------------------------------
    # Normalize symbols already written as text
    # --------------------------------------------------
    text = text.replace(" x ", " × ")
    text = text.replace(" / ", " ÷ ")

    # Common spellings
    text = re.sub(
        r"\bdegrees?\b",
        "°",
        text,
        flags=re.IGNORECASE
    )

    # --------------------------------------------------
    # Clean excessive blank lines
    # --------------------------------------------------
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()
TELEGRAM_FORMAT_RULES = """
For Telegram responses:

- NEVER output LaTeX.
- NEVER output $, $$, \\frac, \\angle, \\theta, \\Omega, \\times, \\sqrt, or \\boxed.
- Use Unicode symbols instead.
- Use ∠ instead of \\angle.
- Use θ instead of \\theta.
- Use Ω instead of \\Omega.
- Use × instead of \\times.
- Use ÷ instead of \\frac or / when presenting simple division.
- Use √ instead of \\sqrt.
- Use ≤, ≥, ≠, ≈, ±, →, ⊥, ∥, ∴ where appropriate.
- Write equations as plain readable Telegram text.
"""
SYSTEM_INSTRUCTION += "\n\n" + TELEGRAM_FORMAT_RULES
#=====

# =========================================================
# USER MANAGEMENT
# =========================================================

def create_or_update_user(
    telegram_user
):

    db = SessionLocal()

    try:

        user = db.query(User).filter(
            User.telegram_user_id
            == telegram_user.id
        ).first()

        if not user:

            user = User(
                telegram_user_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                language="en"
            )

            db.add(user)

        else:

            user.username = telegram_user.username
            user.first_name = telegram_user.first_name
            user.last_name = telegram_user.last_name

            user.last_seen = datetime.now(
                timezone.utc
            )

        db.commit()

        return user.id

    except Exception as e:

        db.rollback()

        print(
            "❌ USER DATABASE ERROR:",
            repr(e)
        )

        return None

    finally:

        db.close()


# =========================================================
# DATABASE MESSAGE
# =========================================================

def save_message(
    telegram_user_id,
    role,
    message
):

    db = SessionLocal()

    try:

        user = db.query(User).filter(
            User.telegram_user_id
            == telegram_user_id
        ).first()

        if not user:
            return

        conversation = Conversation(
            user_id=user.id,
            role=role,
            message=message
        )

        db.add(conversation)

        db.commit()

    except Exception as e:

        db.rollback()

        print(
            "❌ MESSAGE DATABASE ERROR:",
            repr(e)
        )

    finally:

        db.close()


# =========================================================
# LANGUAGE
# =========================================================

def get_language(
    telegram_user_id
):

    db = SessionLocal()

    try:

        user = db.query(User).filter(
            User.telegram_user_id
            == telegram_user_id
        ).first()

        if user:

            return user.language or "en"

        return "en"

    finally:

        db.close()


def set_language(
    telegram_user_id,
    language
):

    db = SessionLocal()

    try:

        user = db.query(User).filter(
            User.telegram_user_id
            == telegram_user_id
        ).first()

        if not user:
            return False

        user.language = language

        db.commit()

        return True

    except Exception as e:

        db.rollback()

        print(
            "❌ LANGUAGE ERROR:",
            repr(e)
        )

        return False

    finally:

        db.close()


# =========================================================
# LANGUAGE PROMPT
# =========================================================

def language_instruction(
    language
):

    languages = {

        "en":
            "Answer in English.",

        "hi":
            "Answer in Hindi. "
            "Keep technical terms in English "
            "where appropriate.",

        "te":
            "Answer in Telugu. "
            "Keep technical terms in English "
            "where appropriate."
    }

    return languages.get(
        language,
        languages["en"]
    )


# =========================================================
# DUPLICATE PROTECTION
# =========================================================

last_messages = {}


def is_duplicate(
    user_id,
    message
):

    current_hash = hashlib.sha256(
        message.strip().lower().encode()
    ).hexdigest()

    previous_hash = last_messages.get(
        user_id
    )

    last_messages[user_id] = current_hash

    return (
        current_hash == previous_hash
    )


# =========================================================
# GEMINI
# =========================================================

async def ask_gemini(
    prompt,
    language="en"
):

    if client is None:

        raise RuntimeError(
            "Gemini client is not configured"
        )

    result = await asyncio.to_thread(
        client.models.generate_content,
        model=GEMINI_MODEL,
        contents=(
            SYSTEM_INSTRUCTION
            + "\n\n"
            + language_instruction(language)
            + "\n\n"
            + prompt
        )
    )

    if not result.text:

        raise RuntimeError(
            "Gemini returned an empty response"
        )

    return result.text.strip()


# =========================================================
# OLLAMA FALLBACK
# =========================================================
async def ask_ollama(prompt, language="en"):
    try:
        print("🦙 Calling Ollama...")

        result = await asyncio.to_thread(
            ollama.chat,
            model="qwen3:1.7b",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        answer = result["message"]["content"].strip()

        if not answer:
            raise RuntimeError("Ollama returned an empty response")

        print("✅ Ollama response received")
        return answer

    except asyncio.TimeoutError:

        print(
            "❌ Ollama timeout after 120 seconds"
        )

        raise RuntimeError(
            "Ollama took too long to respond."
        )

    except Exception as e:

        print("❌ OLLAMA ERROR")
        print(repr(e))

        raise


# =========================================================
# UNIVERSAL AI
# =========================================================
async def ask_ai(prompt, language="en"):

    # ==========================================
    # 1. TRY GEMINI
    # ==========================================

    try:

        print("🤖 Sending request to Gemini...")

        answer = await ask_gemini(
            prompt,
            language
        )

        if answer:
            print("✅ Gemini response received")
            return answer

    except Exception as gemini_error:

        error_text = str(gemini_error)

        print("❌ GEMINI ERROR")
        print(repr(gemini_error))

        # Gemini quota OR connection/server problem
        fallback_errors = (
            "429",
            "RESOURCE_EXHAUSTED",
            "RemoteProtocolError",
            "Server disconnected",
            "ConnectionError",
            "ConnectError",
            "Timeout",
            "timed out",
            "503",
            "UNAVAILABLE"
        )

        should_fallback = any(
            error in error_text
            for error in fallback_errors
        )

        if not should_fallback:
            raise


        # ==========================================
        # 2. FALLBACK TO OLLAMA
        # ==========================================

        print("================================")
        print("🦙 Switching to Ollama...")
        print("================================")

        try:

            answer = await ask_ollama(
                prompt,
                language
            )

            if answer:

                print(
                    "✅ Ollama response received"
                )

                return answer

            raise RuntimeError(
                "Ollama returned empty response"
            )

        except Exception as ollama_error:

            print("❌ OLLAMA ERROR")
            print(repr(ollama_error))

            raise RuntimeError(
                "Both Gemini and Ollama "
                "are currently unavailable."
            )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    create_or_update_user(
        update.effective_user
    )

    await update.message.reply_text(
        "🤖 AI ENGINEERING ASSISTANT\n\n"
        "Welcome!\n\n"
        "I can help with:\n\n"
        "⚡ Engineering\n"
        "💻 Programming\n"
        "🧮 Mathematics\n"
        "🔬 Physics\n"
        "🎓 Education\n"
        "📚 Study preparation\n"
        "🌍 General questions\n\n"
        "Simply send me your question."
    )


# =========================================================
# HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = (
        "🤖 AI ENGINEERING ASSISTANT\n\n"

        "💬 AI\n"
        "Send any question directly.\n\n"

        "🎓 STUDY\n"
        "/explain\n"
        "/mcq\n"
        "/summarize\n"
        "/studyplan\n\n"

        "💻 CODE\n"
        "/code\n"
        "/debug\n"
        "/explaincode\n"
        "/optimize\n\n"

        "🧮 TOOLS\n"
        "/calc\n"
        "/search\n\n"

        "🌍 LANGUAGE\n"
        "/language\n"
        "/english\n"
        "/hindi\n"
        "/telugu\n\n"

        "👤 ACCOUNT\n"
        "/profile\n"
        "/clear\n\n"

        "🔐 ADMIN\n"
        "/admin\n"
        "/users\n"
        "/stats"
    )

    answer = telegram_math(answer)

    await update.message.reply_text(answer)


# =========================================================
# UNIVERSAL TEXT AI
# =========================================================

async def ai_chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    user_id = update.effective_user.id

    user_message = (
        update.message.text or ""
    ).strip()

    if not user_message:
        return


    # Create/update account

    create_or_update_user(
        update.effective_user
    )


    # Duplicate protection

    if is_duplicate(
        user_id,
        user_message
    ):

        print(
            "⚠️ Duplicate message ignored"
        )

        return


    print(
        f"📩 User {user_id}: "
        f"{user_message}"
    )


    language = get_language(
        user_id
    )


    save_message(
        user_id,
        "user",
        user_message
    )


    try:

        answer = await ask_ai(
            user_message,
            language
        )
        answer = telegram_math(answer)

        if not answer:
            answer = (
                "❌ I couldn't generate "
                "an answer."
            )

        save_message(
            user_id,
            "assistant",
            answer
        )

        await update.message.reply_text(
            answer
        )


    except Exception as e:

        print(
            "================================"
        )

        print(
            "❌ AI ERROR"
        )

        print(
            repr(e)
        )

        print(
            "================================"
        )


        await update.message.reply_text(
            "❌ AI service is currently "
            "unavailable.\n\n"
            "Please try again later."
        )


# =========================================================
# CALCULATOR
# =========================================================

ALLOWED_MATH = {
    name: getattr(math, name)
    for name in dir(math)
    if not name.startswith("_")
}


def calculate_expression(
    expression
):

    expression = expression.strip()

    tree = ast.parse(
        expression,
        mode="eval"
    )

    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.USub,
        ast.UAdd,
        ast.Constant,
        ast.Call,
        ast.Name
    )

    for node in ast.walk(tree):

        if not isinstance(
            node,
            allowed_nodes
        ):

            raise ValueError(
                "Invalid expression"
            )

        if isinstance(
            node,
            ast.Name
        ):

            if node.id not in ALLOWED_MATH:

                raise ValueError(
                    "Unknown function"
                )

        if isinstance(
            node,
            ast.Call
        ):

            if not isinstance(
                node.func,
                ast.Name
            ):

                raise ValueError(
                    "Invalid function"
                )

    return eval(
        compile(
            tree,
            "<calculator>",
            "eval"
        ),
        {
            "__builtins__": {}
        },
        ALLOWED_MATH
    )


async def calculator(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "🧮 CALCULATOR\n\n"
            "Example:\n"
            "/calc 25*48\n"
            "/calc sqrt(144)\n"
            "/calc sin(pi/2)"
        )

        return


    expression = " ".join(
        context.args
    )

    try:

        result = calculate_expression(
            expression
        )

        await update.message.reply_text(
            f"🧮 Calculation\n\n"
            f"{expression}\n\n"
            f"= {result}"
        )

    except Exception:

        await update.message.reply_text(
            "❌ Invalid mathematical expression."
        )


# =========================================================
# PROFILE
# =========================================================

async def profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    db = SessionLocal()

    try:

        user = db.query(User).filter(
            User.telegram_user_id
            == user_id
        ).first()

        if not user:

            await update.message.reply_text(
                "❌ Profile not found."
            )

            return


        message_count = db.query(
            Conversation
        ).filter(
            Conversation.user_id
            == user.id
        ).count()


        await update.message.reply_text(

            "👤 MY PROFILE\n\n"

            f"🆔 ID: "
            f"{user.telegram_user_id}\n"

            f"👤 Name: "
            f"{user.first_name or 'User'}\n"

            f"🔗 Username: "
            f"@{user.username}"
            if user.username
            else
            f"🔗 Username: None\n"

            f"🌍 Language: "
            f"{user.language}\n"

            f"💬 Messages: "
            f"{message_count}\n"

            f"📅 Joined: "
            f"{user.created_at.strftime('%d-%m-%Y')}"
        )

    finally:

        db.close()


# =========================================================
# LANGUAGE COMMAND
# =========================================================

async def language_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🌍 LANGUAGE SETTINGS\n\n"
        "/english 🇬🇧\n"
        "/hindi 🇮🇳\n"
        "/telugu 🇮🇳"
    )


async def english_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if set_language(
        update.effective_user.id,
        "en"
    ):

        await update.message.reply_text(
            "🇬🇧 Language changed to English."
        )


async def hindi_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if set_language(
        update.effective_user.id,
        "hi"
    ):

        await update.message.reply_text(
            "🇮🇳 भाषा हिंदी में बदल दी गई है।"
        )


async def telugu_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if set_language(
        update.effective_user.id,
        "te"
    ):

        await update.message.reply_text(
            "🇮🇳 భాష తెలుగుకు మార్చబడింది."
        )


# =========================================================
# STUDY ASSISTANT
# =========================================================

async def explain_topic(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "🎓 Usage:\n"
            "/explain Ohm's Law"
        )

        return


    topic = " ".join(
        context.args
    )


    try:

        answer = await ask_ai(
            f"""
Explain this topic for an engineering student:

{topic}

Include:

• Definition
• Key concepts
• Formula if applicable
• Example
• Applications
• Important exam points
""",
            get_language(
                update.effective_user.id
            )
        )


        await update.message.reply_text(
            "🎓 TOPIC EXPLANATION\n\n"
            + answer
        )


    except Exception as e:

        print(
            "❌ EXPLAIN ERROR:",
            repr(e)
        )

        await update.message.reply_text(
            "❌ Unable to explain the topic."
        )


async def generate_mcq(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "📝 Usage:\n"
            "/mcq Power Systems"
        )

        return


    topic = " ".join(
        context.args
    )


    try:

        answer = await ask_ai(
            f"""
Create 10 MCQs on:

{topic}

Each question must have:

A.
B.
C.
D.

Give the correct answer after each question.
""",
            get_language(
                update.effective_user.id
            )
        )


        await update.message.reply_text(
            "📝 MCQ PRACTICE\n\n"
            + answer
        )


    except Exception as e:

        print(
            "❌ MCQ ERROR:",
            repr(e)
        )

        await update.message.reply_text(
            "❌ Unable to generate MCQs."
        )


async def summarize_topic(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "📚 Usage:\n"
            "/summarize Transformer"
        )

        return


    topic = " ".join(
        context.args
    )


    try:

        answer = await ask_ai(
            f"""
Create concise study notes for:

{topic}

Include:

• Definition
• Key concepts
• Formulas
• Applications
• Exam points
""",
            get_language(
                update.effective_user.id
            )
        )


        await update.message.reply_text(
            "📚 STUDY NOTES\n\n"
            + answer
        )


    except Exception as e:

        print(
            "❌ SUMMARY ERROR:",
            repr(e)
        )

        await update.message.reply_text(
            "❌ Unable to create summary."
        )


async def study_plan(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "📅 Usage:\n"
            "/studyplan Electrical Engineering 30 days"
        )

        return


    request = " ".join(
        context.args
    )


    try:

        answer = await ask_ai(
            f"""
Create a practical study plan:

{request}

Include:

• Daily schedule
• Topics
• Revision
• Practice
• Mock tests
• Final revision
""",
            get_language(
                update.effective_user.id
            )
        )


        await update.message.reply_text(
            "📅 STUDY PLAN\n\n"
            + answer
        )


    except Exception as e:

        print(
            "❌ STUDY PLAN ERROR:",
            repr(e)
        )

        await update.message.reply_text(
            "❌ Unable to create study plan."
        )


# =========================================================
# CODE ASSISTANT
# =========================================================

async def code_assistant(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "💻 Usage:\n"
            "/code C++ Fibonacci program"
        )

        return


    request = " ".join(
        context.args
    )


    try:

        answer = await ask_ai(
            f"""
Act as an expert programming assistant.

User request:

{request}

Provide:

1. Correct runnable code
2. Short explanation
3. Example input/output when useful
4. Time complexity when applicable
""",
            get_language(
                update.effective_user.id
            )
        )


        await update.message.reply_text(
            answer
        )


    except Exception as e:

        print(
            "❌ CODE ERROR:",
            repr(e)
        )

        await update.message.reply_text(
            "❌ Unable to generate code."
        )


async def debug_code(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "🐛 Usage:\n"
            "/debug your error or code"
        )

        return


    request = " ".join(
        context.args
    )


    try:

        answer = await ask_ai(
            f"""
Debug this code/error:

{request}

Provide:

🔍 Problem
🛠 Cause
✅ Fix
💻 Corrected code
📌 Explanation
""",
            get_language(
                update.effective_user.id
            )
        )


        await update.message.reply_text(
            "🐛 DEBUG RESULT\n\n"
            + answer
        )


    except Exception as e:

        print(
            "❌ DEBUG ERROR:",
            repr(e)
        )

        await update.message.reply_text(
            "❌ Unable to debug."
        )


async def explain_code(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "📖 Usage:\n"
            "/explaincode your code"
        )

        return


    code = " ".join(
        context.args
    )


    try:

        answer = await ask_ai(
            f"""
Explain this code:

{code}

Include:

• Purpose
• Logic
• Functions
• Input/output
• Complexity
• Improvements
""",
            get_language(
                update.effective_user.id
            )
        )


        await update.message.reply_text(
            "📖 CODE EXPLANATION\n\n"
            + answer
        )


    except Exception as e:

        print(
            "❌ EXPLAIN CODE ERROR:",
            repr(e)
        )

        await update.message.reply_text(
            "❌ Unable to explain code."
        )


async def optimize_code(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "⚡ Usage:\n"
            "/optimize your code"
        )

        return


    code = " ".join(
        context.args
    )


    try:

        answer = await ask_ai(
            f"""
Optimize this code:

{code}

Explain:

• Problems
• Performance improvements
• Readability
• Security
• Optimized code
""",
            get_language(
                update.effective_user.id
            )
        )


        await update.message.reply_text(
            "⚡ OPTIMIZED CODE\n\n"
            + answer
        )


    except Exception as e:

        print(
            "❌ OPTIMIZE ERROR:",
            repr(e)
        )

        await update.message.reply_text(
            "❌ Unable to optimize code."
        )


# =========================================================
# ADMIN
# =========================================================

def is_admin(
    user_id
):

    return str(user_id) == str(
        ADMIN_USER_ID
    )


async def admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(
        update.effective_user.id
    ):

        await update.message.reply_text(
            "⛔ Access Denied"
        )

        return


    db = SessionLocal()

    try:

        total_users = db.query(
            User
        ).count()

        total_messages = db.query(
            Conversation
        ).count()

        await update.message.reply_text(
            "🔐 ADMIN DASHBOARD\n\n"
            f"👥 Users: {total_users}\n"
            f"💬 Messages: {total_messages}\n\n"
            "/users\n"
            "/stats"
        )

    finally:

        db.close()


async def admin_users(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(
        update.effective_user.id
    ):

        await update.message.reply_text(
            "⛔ Access Denied"
        )

        return


    db = SessionLocal()

    try:

        users = db.query(
            User
        ).order_by(
            User.created_at.desc()
        ).limit(20).all()


        if not users:

            await update.message.reply_text(
                "No users found."
            )

            return


        text = "👥 USERS\n\n"


        for index, user in enumerate(
            users,
            start=1
        ):

            text += (
                f"{index}. "
                f"{user.first_name or 'User'}\n"
                f"🆔 {user.telegram_user_id}\n"
                f"🌍 {user.language}\n\n"
            )


        await update.message.reply_text(
            text
        )

    finally:

        db.close()


async def admin_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_admin(
        update.effective_user.id
    ):

        await update.message.reply_text(
            "⛔ Access Denied"
        )

        return


    db = SessionLocal()

    try:

        total_users = db.query(
            User
        ).count()

        total_messages = db.query(
            Conversation
        ).count()

        await update.message.reply_text(
            "📊 BOT STATISTICS\n\n"
            f"👥 Users: {total_users}\n"
            f"💬 Messages: {total_messages}"
        )

    finally:

        db.close()


# =========================================================
# REMINDER
# =========================================================

async def send_reminder(
    context: ContextTypes.DEFAULT_TYPE
):

    job = context.job

    await context.bot.send_message(
        chat_id=job.chat_id,
        text=(
            "🔔 REMINDER\n\n"
            f"📌 {job.data}\n\n"
            "⏰ Your reminder is due."
        )
    )


async def remind(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if len(context.args) < 2:

        await update.message.reply_text(
            "🔔 Usage:\n\n"
            "/remind 10s Test\n"
            "/remind 30m Study\n"
            "/remind 2h Assignment\n"
            "/remind 1d Revision"
        )

        return


    time_text = context.args[0].lower()

    reminder_text = " ".join(
        context.args[1:]
    )


    try:

        amount = int(
            time_text[:-1]
        )

        unit = time_text[-1]


        if unit == "s":

            delay = timedelta(
                seconds=amount
            )

        elif unit == "m":

            delay = timedelta(
                minutes=amount
            )

        elif unit == "h":

            delay = timedelta(
                hours=amount
            )

        elif unit == "d":

            delay = timedelta(
                days=amount
            )

        else:

            raise ValueError


        context.job_queue.run_once(
            send_reminder,
            when=delay,
            data=reminder_text,
            chat_id=update.effective_chat.id
        )


        await update.message.reply_text(
            "✅ Reminder scheduled!\n\n"
            f"📌 {reminder_text}"
        )


    except Exception:

        await update.message.reply_text(
            "❌ Invalid reminder format."
        )


#==image======
async def image_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    user_id = update.effective_user.id

    print(
        f"📷 User {user_id}: Image question received"
    )

    create_or_update_user(
        update.effective_user
    )

    try:

        await update.message.reply_text(
            "📷 Image received.\n"
            "🔍 Reading the question..."
        )

        # Get highest-resolution Telegram photo
        photo = update.message.photo[-1]

        file = await context.bot.get_file(
            photo.file_id
        )

        image_path = (
            f"uploads/question_{user_id}.jpg"
        )

        await file.download_to_drive(
            image_path
        )

        # Open image
        image = Image.open(
            image_path
        )

        # OCR
        extracted_text = (
            pytesseract.image_to_string(
                image
            ).strip()
        )

        print(
            "📝 Extracted text:"
        )

        print(
            extracted_text
        )

        if not extracted_text:

            await update.message.reply_text(
                "❌ I couldn't read the question "
                "from the image.\n\n"
                "Please upload a clearer image."
            )

            return

        # Get user's language
        language = get_language(
            user_id
        )

        # Send extracted question to AI
        answer = await ask_ai(
            f"""
The user uploaded an image containing a question.

OCR extracted the following text:

{extracted_text}

Answer the question accurately.

If it is:
• Mathematics → show calculation steps.
• Electrical Engineering → show formulas and units.
• Programming → provide correct code.
• Physics → explain step by step.
• Multiple choice → identify the correct option and explain it.

Do not mention OCR unless necessary.
""",
            language
        )

        save_message(
            user_id,
            "user",
            extracted_text
        )

        save_message(
            user_id,
            "assistant",
            answer
        )

        await update.message.reply_text(
            answer
        )

    except Exception as e:

        print(
            "================================"
        )

        print(
            "❌ IMAGE ERROR"
        )

        print(
            repr(e)
        )

        print(
            "================================"
        )

        await update.message.reply_text(
            "❌ I couldn't process the image.\n\n"
            "Please upload a clearer question image "
            "and try again."
        )

#=====PDF====   
async def pdf_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.document:
        return

    user_id = update.effective_user.id

    document = update.message.document

    if not document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text(
            "❌ Please upload a PDF file."
        )
        return

    print(
        f"📄 User {user_id}: "
        f"PDF received: {document.file_name}"
    )

    try:

        await update.message.reply_text(
            "📄 PDF received.\n"
            "🔍 Reading the document..."
        )

        os.makedirs(
            "uploads/documents",
            exist_ok=True
        )

        file = await context.bot.get_file(
            document.file_id
        )

        path = os.path.join(
            "uploads",
            "documents",
            f"{user_id}_{document.file_name}"
        )

        await file.download_to_drive(path)

        # Read PDF
        reader = PdfReader(path)

        extracted_text = ""

        for page in reader.pages:

            text = page.extract_text()

            if text:
                extracted_text += (
                    text + "\n"
                )

        extracted_text = extracted_text.strip()

        if not extracted_text:

            await update.message.reply_text(
                "❌ I couldn't extract text "
                "from this PDF.\n\n"
                "It may be a scanned/image PDF."
            )

            return

        # Prevent extremely large prompts
        extracted_text = extracted_text[:30000]

        print(
            f"📝 Extracted {len(extracted_text)} characters"
        )

        language = get_language(
            user_id
        )

        answer = await ask_ai(
            f"""
The user uploaded a PDF.

Document content:

{extracted_text}

Analyze the document and answer appropriately.

If it contains:
• Engineering questions → solve them step by step.
• Mathematics → show calculations.
• Programming → provide correct code.
• MCQs → provide answers with explanations.
• Study notes → summarize important points.

Answer clearly and professionally.
""",
            language
        )

        save_message(
            user_id,
            "user",
            f"[PDF] {document.file_name}\n"
            + extracted_text[:5000]
        )

        save_message(
            user_id,
            "assistant",
            answer
        )

        await update.message.reply_text(
            answer
        )

    except Exception as e:

        print(
            "================================"
        )

        print(
            "❌ PDF ERROR"
        )

        print(
            repr(e)
        )

        print(
            "================================"
        )

        await update.message.reply_text(
            "❌ Unable to analyze this PDF."
        )  
# =======================================================
#=====csv/exicel====
async def analyze_dataset(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.document:
        return

    user_id = update.effective_user.id
    document = update.message.document
    filename = document.file_name or ""

    if not filename.lower().endswith(
        (".csv", ".xlsx", ".xls")
    ):
        await update.message.reply_text(
            "❌ Please upload a CSV or Excel file."
        )
        return

    try:

        await update.message.reply_text(
            "📊 Dataset received.\n"
            "🔍 Analyzing your data..."
        )

        os.makedirs(
            "uploads/data",
            exist_ok=True
        )

        file = await context.bot.get_file(
            document.file_id
        )

        path = os.path.join(
            "uploads",
            "data",
            f"{user_id}_{filename}"
        )

        await file.download_to_drive(path)

        # Load dataset
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)

        if df.empty:
            await update.message.reply_text(
                "❌ The dataset is empty."
            )
            return

        # Basic analysis
        rows, columns = df.shape

        numeric_columns = df.select_dtypes(
            include="number"
        ).columns.tolist()

        missing = int(
            df.isnull().sum().sum()
        )

        summary = (
            f"📊 DATASET ANALYSIS\n\n"
            f"📄 File: {filename}\n"
            f"📐 Rows: {rows}\n"
            f"📊 Columns: {columns}\n"
            f"🔢 Numeric columns: "
            f"{len(numeric_columns)}\n"
            f"⚠️ Missing values: {missing}\n\n"
            f"📋 Columns:\n"
            + "\n".join(
                f"• {column}"
                for column in df.columns
            )
        )

        await update.message.reply_text(
            summary
        )

        # Create visualization
        if numeric_columns:

            os.makedirs(
                "charts",
                exist_ok=True
            )

            column = numeric_columns[0]

            plt.figure(
                figsize=(10, 6)
            )

            df[column].dropna().plot(
                kind="hist",
                bins=20
            )

            plt.title(
                f"Distribution of {column}"
            )

            plt.xlabel(column)
            plt.ylabel("Frequency")

            chart_path = os.path.join(
                "charts",
                f"{user_id}_chart.png"
            )

            plt.savefig(
                chart_path,
                bbox_inches="tight"
            )

            plt.close()

            with open(
                chart_path,
                "rb"
            ) as chart:

                await update.message.reply_photo(
                    photo=chart,
                    caption=(
                        f"📈 Automatic visualization\n"
                        f"Column: {column}"
                    )
                )

        # AI analysis
        sample = df.head(10).to_string(
            index=False
        )

        language = get_language(
            user_id
        )

        prompt = f"""
Analyze this dataset.

File: {filename}

Rows: {rows}
Columns: {columns}

Columns:
{list(df.columns)}

Numeric columns:
{numeric_columns}

Missing values:
{missing}

Sample data:

{sample}

Provide:

1. Key observations
2. Important statistics
3. Possible trends
4. Data-quality issues
5. Useful recommendations
"""

        answer = await ask_ai(
            prompt,
            language
        )

        answer = telegram_math(answer)

        await update.message.reply_text(answer)

        await update.message.reply_text(
            "🤖 AI DATA INSIGHTS\n\n"
            + answer
        )

        save_message(
            user_id,
            "user",
            f"[DATASET] {filename}"
        )

        save_message(
            user_id,
            "assistant",
            answer
        )

    except Exception as e:

        print(
            "================================"
        )

        print(
            "❌ DATA ANALYSIS ERROR"
        )

        print(
            repr(e)
        )

        print(
            "================================"
        )

        await update.message.reply_text(
            "❌ Unable to analyze this dataset."
        )
#=============
#=====search function====
async def web_search(query):

    if not TAVILY_API_KEY:
        raise RuntimeError(
            "TAVILY_API_KEY is missing"
        )

    response = await asyncio.to_thread(
        requests.post,
        "https://api.tavily.com/search",
        json={
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": 5,
            "include_answer": True
        },
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    results = data.get(
        "results",
        []
    )

    if not results:
        return "No web results found."

    text = []

    for item in results:

        title = item.get(
            "title",
            "Untitled"
        )

        content = item.get(
            "content",
            ""
        )

        url = item.get(
            "url",
            ""
        )

        text.append(
            f"TITLE: {title}\n"
            f"CONTENT: {content}\n"
            f"URL: {url}"
        )

    return "\n\n".join(text)
async def search_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "🌐 WEB SEARCH\n\n"
            "Usage:\n"
            "/search latest electrical engineering news"
        )

        return

    query = " ".join(
        context.args
    )

    try:

        await update.message.reply_text(
            "🌐 Searching the web..."
        )

        results = await web_search(
            query
        )

        language = get_language(
            update.effective_user.id
        )
        
        answer = await ask_ai(
            f"""
Answer the user's question using
the following web-search results.

Question:
{query}

Search results:
{results}

Rules:

• Use only information supported
  by the search results.
• Clearly explain the answer.
• Mention important sources/URLs
  when appropriate.
• If the results are insufficient,
  say so.
""",
            language
        )

        await update.message.reply_text(
            "🌐 WEB SEARCH RESULT\n\n"
            + answer
        )

    except Exception as e:

        print(
            "❌ WEB SEARCH ERROR:",
            repr(e)
        )

        await update.message.reply_text(
            "❌ Web search is currently unavailable."
        )

#===load whisper model====        
print("🎙️ Loading Whisper model...")

whisper_model = whisper.load_model(
    WHISPER_MODEL
)

print("✅ Whisper ready")
#======================================================
#======
async def speech_to_text(
    audio_path
):

    result = await asyncio.to_thread(
        whisper_model.transcribe,
        audio_path
    )

    text = result.get(
        "text",
        ""
    ).strip()

    return text
async def text_to_speech(
    text,
    output_path,
    language="en"
):

    voices = {
        "en": "en-US-AriaNeural",
        "hi": "hi-IN-SwaraNeural",
        "te": "te-IN-ShrutiNeural"
    }

    voice = voices.get(
        language,
        voices["en"]
    )

    communicate = edge_tts.Communicate(
        text,
        voice
    )

    await communicate.save(
        output_path
    )
async def voice_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    user_id = update.effective_user.id

    print(
        f"🎙️ User {user_id}: "
        "Voice message received"
    )

    create_or_update_user(
        update.effective_user
    )

    os.makedirs(
        "uploads/audio",
        exist_ok=True
    )

    try:
        answer = telegram_math(answer)
        await update.message.reply_text(
            "🎙️ Voice received.\n"
            "🔊 Converting speech to text..."
        )

        # Telegram voice file
        voice = update.message.voice

        telegram_file = (
            
            await context.bot.get_file(
                voice.file_id
            )
        )

        input_path = os.path.join(
            "uploads",
            "audio",
            f"{user_id}_input.ogg"
        )
        answer = telegram_math(answer)
        await telegram_file.download_to_drive(
            input_path
        )

        # Speech → Text
        text = await speech_to_text(
            input_path
        )

        if not text:

            await update.message.reply_text(
                "❌ I couldn't understand "
                "the voice message."
            )

            return

        print(
            f"📝 Voice text: {text}"
        )
        answer = telegram_math(answer)
        await update.message.reply_text(
            f"📝 I heard:\n\n{text}\n\n"
            "🤖 Generating answer..."
        )

        language = get_language(
            user_id
        )

        # AI
        answer = telegram_math(answer)
        answer = await ask_ai(
            text,
            language
        )

        answer = telegram_math(answer)

        save_message(
            user_id,
            "user",
            f"[VOICE] {text}"
        )

        save_message(
            user_id,
            "assistant",
            answer
        )

        # Text response
        answer = telegram_math(answer)
        await update.message.reply_text(
            answer
        )

        # Voice response
        output_path = os.path.join(
            "uploads",
            "audio",
            f"{user_id}_reply.mp3"
        )
        answer = telegram_math(answer)
        await text_to_speech(
            answer,
            output_path,
            language
        )

        with open(
            output_path,
            "rb"
        ) as audio:
            answer = telegram_math(answer)
            await update.message.reply_voice(
                voice=audio
            )

        print(
            "✅ Voice reply sent"
        )

    except Exception as e:

        print(
            "================================"
        )

        print(
            "❌ VOICE ERROR"
        )

        print(
            repr(e)
        )

        print(
            "================================"
        )
        answer = telegram_math(answer)
        await update.message.reply_text(
            "❌ I couldn't process the "
            "voice message.\n\n"
            "Please try again."
        )   
#====global error handler====
async def telegram_error_handler(update, context):
    print("================================")
    print("❌ TELEGRAM ERROR")
    print(repr(context.error))
    print("================================")

    # Don't send technical tracebacks to users.
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ A temporary Telegram/network error occurred.\n"
                "Please try again."
            )
    except Exception:
        pass
#====
#====status command====
async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    # Test Ollama
    ollama_status = "❌ Offline"

    try:
        await asyncio.wait_for(
            asyncio.to_thread(
                ollama.list
            ),
            timeout=5
        )

        ollama_status = "✅ Online"

    except Exception:
        pass

    # Gemini status is based on configuration only.
    gemini_status = (
        "✅ Configured"
        if GEMINI_API_KEY
        else "❌ Not configured"
    )

    db_status = "❌ Offline"

    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "✅ Online"
    except Exception:
        pass

    await update.message.reply_text(
        "🤖 AI ENGINEERING ASSISTANT\n\n"
        "📊 SYSTEM STATUS\n\n"
        f"🧠 Gemini API: {gemini_status}\n"
        f"🦙 Ollama: {ollama_status}\n"
        f"🗄️ PostgreSQL: {db_status}\n"
        "📱 Telegram: ✅ Connected\n\n"
        f"🤖 Ollama Model: {OLLAMA_MODEL}\n"
        f"🧠 Gemini Model: {GEMINI_MODEL}"
    )         
#======
#====universal text handler====
async def ask_ai(prompt, language="en"):

    try:
        print("🤖 Trying Gemini...")
        return await ask_gemini(prompt, language)

    except Exception as gemini_error:

        print("❌ Gemini:", repr(gemini_error))

        print("🦙 Trying Ollama...")

        try:
            return await ask_ollama(prompt, language)

        except Exception as ollama_error:

            print("❌ Ollama:", repr(ollama_error))

            raise RuntimeError(
                "Both AI providers are unavailable."
            )
#====
# =========================================================
# MAIN
# =========================================================
def main():
    from telegram.request import HTTPXRequest

    telegram_request = HTTPXRequest(
        connection_pool_size=20,
        connect_timeout=30.0,
        read_timeout=60.0,
        write_timeout=60.0,
        pool_timeout=30.0,
    )

    bot_app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(telegram_request)
        .build()
    )
    
    bot_app.add_handler(
        MessageHandler(
            filters.PHOTO,
            image_question
        )
    )

    # Basic

    bot_app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    bot_app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )


    # Calculator

    bot_app.add_handler(
        CommandHandler(
            "calc",
            calculator
        )
    )


    # Account

    bot_app.add_handler(
        CommandHandler(
            "profile",
            profile
        )
    )


    # Language

    bot_app.add_handler(
        CommandHandler(
            "language",
            language_command
        )
    )

    bot_app.add_handler(
        CommandHandler(
            "english",
            english_command
        )
    )

    bot_app.add_handler(
        CommandHandler(
            "hindi",
            hindi_command
        )
    )

    bot_app.add_handler(
        CommandHandler(
            "telugu",
            telugu_command
        )
    )
    

    # Study

    bot_app.add_handler(
        CommandHandler(
            "explain",
            explain_topic
        )
    )

    bot_app.add_handler(
        CommandHandler(
            "mcq",
            generate_mcq
        )
    )

    bot_app.add_handler(
        CommandHandler(
            "summarize",
            summarize_topic
        )
    )

    bot_app.add_handler(
        CommandHandler(
            "studyplan",
            study_plan
        )
    )


    # Code

    bot_app.add_handler(
        CommandHandler(
            "code",
            code_assistant
        )
    )

    bot_app.add_handler(
        CommandHandler(
            "debug",
            debug_code
        )
    )

    bot_app.add_handler(
        CommandHandler(
            "explaincode",
            explain_code
        )
    )

    bot_app.add_handler(
        CommandHandler(
            "optimize",
            optimize_code
        )
    )


    # Reminder

    bot_app.add_handler(
        CommandHandler(
            "remind",
            remind
        )
    )


    # Admin

    bot_app.add_handler(
        CommandHandler(
            "admin",
            admin
        )
    )

    bot_app.add_handler(
        CommandHandler(
            "users",
            admin_users
        )
    )

    bot_app.add_handler(
        CommandHandler(
            "stats",
            admin_stats
        )
    )
    bot_app.add_handler(
    CommandHandler(
        "search",
        search_command
    )
    )

    bot_app.add_error_handler(telegram_error_handler)
    bot_app.add_handler(
    CommandHandler(
        "status",
        status_command
    )
)
    # Universal text handler
    # Keep this AFTER command handlers.

    # Image questions
    bot_app.add_handler(
        MessageHandler(
            filters.PHOTO,
            image_question
        )
    )
    # 📄 PDF questions
    bot_app.add_handler(
    MessageHandler(
        filters.Document.PDF,
        pdf_document
    )
    ) 
    # 📊 CSV / Excel
    bot_app.add_handler(
    MessageHandler(
        filters.Document.FileExtension(
            "csv"
        )
        | filters.Document.FileExtension(
            "xlsx"
        )
        | filters.Document.FileExtension(
            "xls"
        ),
        analyze_dataset
    )
    )
    # 🎙️ Voice
    bot_app.add_handler(
    MessageHandler(
        filters.VOICE,
        voice_message
    )
    )

    # Normal text questions
    bot_app.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            ai_chat
        )
    )


    print("================================")
    print("🤖 AI ENGINEERING ASSISTANT")
    print("================================")

    bot_app.run_polling()

  


if __name__ == "__main__":

    main()