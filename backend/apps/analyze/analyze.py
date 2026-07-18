import io
import json
import traceback
from contextlib import asynccontextmanager

from fastapi import APIRouter, UploadFile, File, HTTPException
from PyPDF2 import PdfReader

from backend.config.Apps import SubApp
from swarm_debug import debug

import os
from dotenv import load_dotenv

load_dotenv()

# --- Gemini Setup ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# --- Groq Setup (fallback) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Try importing Gemini
gemini_available = False
genai = None
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai_mod
        genai = genai_mod
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_available = True
        debug("Gemini API configured successfully")
    except Exception as e:
        debug(f"Gemini import/config error: {e}")

# Try importing Groq
groq_available = False
groq_client = None
if GROQ_API_KEY:
    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
        groq_available = True
        debug("Groq API configured successfully")
    except Exception as e:
        debug(f"Groq import/config error: {e}")


@asynccontextmanager
async def analyze_lifespan():
    debug("analyze SubApp lifespan starting")
    yield


analyze = SubApp("analyze", analyze_lifespan)


async def call_gemini_json(prompt: str) -> dict:
    """Calls Gemini API and enforces a JSON response format."""
    if not gemini_available or genai is None:
        return {}
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        response = await model.generate_content_async(prompt)
        result_text = response.text
        parsed = json.loads(result_text)
        if not isinstance(parsed, dict):
            debug(f"Gemini returned non-dict JSON: {parsed}")
            return {}
        return parsed
    except Exception as e:
        debug(f"Gemini JSON Error: {e}")
        return {}


def call_groq_json(prompt: str) -> dict:
    """Calls Groq API and enforces a JSON response format. (Synchronous via httpx or Groq SDK)"""
    if not groq_available or groq_client is None:
        return {}
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You must respond with valid JSON only. No markdown, no code fences, just raw JSON. Ensure all string values properly escape any internal quotes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2048,
        )
        result_text = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[-1]
        if result_text.endswith("```"):
            result_text = result_text.rsplit("```", 1)[0]
        result_text = result_text.strip()
        parsed = json.loads(result_text)
        if not isinstance(parsed, dict):
            debug(f"Groq returned non-dict JSON: {parsed}")
            return {}
        return parsed
    except Exception as e:
        debug(f"Groq JSON Error: {e}")
        return {}


async def call_llm_json(prompt: str, agent_name: str = "unknown") -> dict:
    """Try Gemini first, fall back to Groq if Gemini fails."""
    result = await call_gemini_json(prompt)
    if result:
        debug(f"[{agent_name}] LLM call succeeded via Gemini")
        return result
    
    debug(f"[{agent_name}] Gemini failed or unavailable, falling back to Groq...")
    result = call_groq_json(prompt)
    if result:
        debug(f"[{agent_name}] LLM call succeeded via Groq")
        return result
    
    debug(f"[{agent_name}] Both Gemini and Groq failed")
    return {}


@analyze.router.post("/upload")
async def analyze_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Read PDF text
    try:
        contents = await file.read()
        reader = PdfReader(io.BytesIO(contents))
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    except Exception as e:
        debug(f"PDF extraction error: {e}")
        raise HTTPException(status_code=500, detail="Error extracting text from PDF.")

    if not text.strip():
        text = "No text found in PDF. Assuming standard terms."

    # Using the first 2000 chars to avoid exceeding context windows
    contract_snippet = text[:2000]

    debug("Running Analysis Agents...")

    # Agent 1: Legal — uses a simpler 2-field response to avoid JSON parse failures
    # caused by contract text with quotes/special chars in the 'clause' field.
    # The clause is extracted separately via a second call if needed.
    legal_prompt = f"You are a legal expert analyzing a contract. Find legal risks (termination clauses, liability limits). Return ONLY a JSON object with keys: 'risk' (High, Medium, or Low) and 'description' (short text describing the risk). Contract: {contract_snippet}"
    legal_data = await call_llm_json(legal_prompt, "Legal")
    if not legal_data:
        legal_data = {"risk": "Medium", "description": "Unable to analyze legal risks (LLM unavailable)."}
    # Ensure required fields exist
    if "risk" not in legal_data:
        legal_data["risk"] = "Medium"
    if "description" not in legal_data:
        legal_data["description"] = "No description provided."

    # Agent 2: Privacy
    privacy_prompt = f"You are a privacy expert analyzing a contract for GDPR and data risks. Return ONLY a JSON object with keys: 'risk' (High, Medium, or Low) and 'description' (short text). Contract: {contract_snippet}"
    privacy_data = await call_llm_json(privacy_prompt, "Privacy")
    if not privacy_data:
        privacy_data = {"risk": "Medium", "description": "Unable to analyze privacy risks (LLM unavailable)."}
    if "risk" not in privacy_data:
        privacy_data["risk"] = "Medium"
    if "description" not in privacy_data:
        privacy_data["description"] = "No description provided."

    # Agent 3: Finance
    finance_prompt = f"You are a finance expert analyzing a contract for financial risks (fees, payment terms). Return ONLY a JSON object with keys: 'risk' (High, Medium, or Low) and 'description' (short text). Contract: {contract_snippet}"
    finance_data = await call_llm_json(finance_prompt, "Finance")
    if not finance_data:
        finance_data = {"risk": "Medium", "description": "Unable to analyze financial risks (LLM unavailable)."}
    if "risk" not in finance_data:
        finance_data["risk"] = "Medium"
    if "description" not in finance_data:
        finance_data["description"] = "No description provided."

    # Agent 4: Security
    security_prompt = f"You are a cybersecurity expert analyzing a contract for security risks. Return ONLY a JSON object with keys: 'risk' (High, Medium, or Low) and 'description' (short text). Contract: {contract_snippet}"
    security_data = await call_llm_json(security_prompt, "Security")
    if not security_data:
        security_data = {"risk": "Medium", "description": "Unable to analyze security risks (LLM unavailable)."}
    if "risk" not in security_data:
        security_data["risk"] = "Medium"
    if "description" not in security_data:
        security_data["description"] = "No description provided."

    # Extract the actual risky clause via a separate lightweight call
    # This avoids JSON parse failures caused by contract text with quotes/special chars
    if "clause" not in legal_data or legal_data.get("clause", "") in ("N/A", "", None):
        try:
            clause_prompt = f"The legal expert found this risk: {legal_data.get('description', 'N/A')}. Extract the exact contract clause text that corresponds to this risk. Return ONLY a JSON object with key 'clause' (the exact contract text of that risky clause). Contract: {contract_snippet}"
            clause_data = await call_llm_json(clause_prompt, "Clause")
            if clause_data and "clause" in clause_data and clause_data["clause"]:
                legal_data["clause"] = clause_data["clause"]
            else:
                legal_data["clause"] = legal_data.get("description", "No clause extracted.")
        except Exception as e:
            debug(f"[Clause] Extraction failed: {e}")
            legal_data["clause"] = legal_data.get("description", "No clause extracted.")
    else:
        debug(f"[Clause] Legal agent already provided clause")

    debug("Running Debate Moderator...")

    # Multi-Agent Debate Mechanism (Moderator)
    debate_prompt = f"""You are a Moderator. The following are risk assessments from 4 experts on the same contract:
Legal: {json.dumps(legal_data)}
Privacy: {json.dumps(privacy_data)}
Finance: {json.dumps(finance_data)}
Security: {json.dumps(security_data)}

Analyze these differing viewpoints and generate a short debate summary. Return ONLY a JSON object with exactly these 3 keys:
'legal_view' (summary of legal concern), 'reviewer_view' (a counter-perspective or mitigating factor), and 'moderator_view' (your final ruling on the risk)."""
    debate_data = await call_llm_json(debate_prompt, "Debate")
    if not debate_data:
        debate_data = {
            "legal_view": "Legal sees potential risks.",
            "reviewer_view": "The other agents did not flag critical issues.",
            "moderator_view": "Proceed with caution based on LLM unavailability."
        }

    debug("Running Fix Agent...")

    # AI Fix Agent
    clause_to_fix = legal_data.get('clause', 'No clause provided')
    fix_prompt = f"""You are an AI Fix Agent. The legal expert found this risky clause:
"{clause_to_fix}"
And described the risk as: {legal_data.get('description', 'Unknown')}

Rewrite this clause to be more fair and balanced. Return ONLY a JSON object with these 3 keys:
'original' (the original clause text), 'improved' (the rewritten fairer clause), and 'explanation' (why you changed it)."""
    fix_data = await call_llm_json(fix_prompt, "Fix")
    if not fix_data:
        fix_data = {
            "original": clause_to_fix,
            "improved": "Error generating improvement.",
            "explanation": "LLM failed to return a fix."
        }

    # Overall Score Calculation
    risk_map = {"High": 3, "Medium": 2, "Low": 1}
    total_risk = risk_map.get(legal_data.get("risk", "Medium"), 2) + \
                 risk_map.get(privacy_data.get("risk", "Medium"), 2) + \
                 risk_map.get(finance_data.get("risk", "Medium"), 2) + \
                 risk_map.get(security_data.get("risk", "Medium"), 2)

    # 4 lowest, 12 highest. Score = 100 - ((total_risk - 4) / 8 * 100)
    score = 100 - int(((total_risk - 4) / 8) * 100)
    overall_risk = "High" if total_risk > 9 else "Medium" if total_risk > 6 else "Low"

    return {
        "filename": file.filename,
        "agents": {
            "legal": legal_data,
            "privacy": privacy_data,
            "finance": finance_data,
            "security": security_data
        },
        "debate": debate_data,
        "fix": fix_data,
        "score": score,
        "overall_risk": overall_risk
    }
