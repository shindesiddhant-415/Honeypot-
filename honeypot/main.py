from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict
import requests
import datetime
import random

app = FastAPI(title="Agentic Honey-Pot API")

# --- Configuration ---
VALID_API_KEYS = ["sk_test_123456789"]
CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

# --- In-Memory Database (Replace with Redis/DB in prod) ---
# Format: {session_id: {"history": [], "metadata": {}, "scam_detected": False}}
sessions: Dict[str, Dict] = {}

# --- Models ---
class MessageRequest(BaseModel):
    sender: str
    text: str
    timestamp: str

class HoneyPotRequest(BaseModel):
    sessionId: str
    message: MessageRequest
    conversationHistory: Optional[List[MessageRequest]] = []
    metadata: Optional[Dict] = {}

class HoneyPotResponse(BaseModel):
    status: str
    reply: str

class CallbackPayload(BaseModel):
    sessionId: str
    scamDetected: bool
    totalMessagesExchanged: int
    extractedIntelligence: Dict
    agentNotes: str

# --- Logic (Rule-Based for "No API Key" Scenario) ---

SCAM_KEYWORDS = ["bank", "verify", "block", "suspend", "upi", "urgent", "pan card", "kyc", "expired"]

def detect_scam(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in SCAM_KEYWORDS)

def generate_agent_reply(last_scammer_text: str, session_data: Dict) -> str:
    """
    Simulates a naive victim to keep the scammer engaged.
    """
    history_len = len(session_data.get("conversationHistory", []))
    
    if history_len < 2:
        return "Who is this? Why are you messaging me?"
    elif "verify" in last_scammer_text.lower():
        return "I don't know how to verify. Can you help me?"
    elif "bank" in last_scammer_text.lower():
        return "Oh no! My bank account? What happened?"
    elif "upi" in last_scammer_text.lower():
        return "I send money using GPay normally. Is that UPI?"
    else:
        replies = [
            "I am confused.",
            "Please tell me what to do.",
            "Is this official?",
            "I am getting scared."
        ]
        return random.choice(replies)

def extract_intelligence(history: List[MessageRequest]) -> Dict:
    # Heuristic extraction
    intel = {
        "bankAccounts": [],
        "upiIds": [],
        "phishingLinks": [],
        "phoneNumbers": [],
        "suspiciousKeywords": []
    }
    for msg in history:
        if msg.sender == "user": continue # Skip our own messages
        
        text = msg.text
        # Naive extraction logic
        if "http" in text:
            intel["phishingLinks"].append(text.split("http")[1].split(" ")[0])
        if "@" in text and "upi" not in intel["upiIds"]: # weak check for upi
             words = text.split()
             for w in words:
                 if "@" in w: intel["upiIds"].append(w)
        
        # Check keywords
        for kw in SCAM_KEYWORDS:
            if kw in text.lower() and kw not in intel["suspiciousKeywords"]:
                intel["suspiciousKeywords"].append(kw)
                
    return intel

async def send_callback(session_id: str, session_data: Dict):
    """
    Sends the final report to the hackathon evaluation endpoint.
    """
    history = session_data["history"]
    intel = extract_intelligence([MessageRequest(**m) if isinstance(m, dict) else m for m in history])
    
    payload = {
        "sessionId": session_id,
        "scamDetected": session_data["scam_detected"],
        "totalMessagesExchanged": len(history),
        "extractedIntelligence": intel,
        "agentNotes": "Rule-based agent detected scam keywords and engaged."
    }
    
    # In a real run, we would POST this.
    # checking if we should actually call it or log it
    print(f"--- MOCK CALLBACK SENDING FOR {session_id} ---")
    print(payload)
    # try:
    #     requests.post(CALLBACK_URL, json=payload, timeout=5)
    # except Exception as e:
    #     print(f"Callback failed: {e}")

# --- Endpoints ---
from fastapi import APIRouter

router = APIRouter()

@router.post("/api/chat", response_model=HoneyPotResponse)
async def chat_handler(
    request: HoneyPotRequest, 
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(...)
):
    if x_api_key not in VALID_API_KEYS:
        # For simplicity in hackathon, returning success false or HTTP 401
        raise HTTPException(status_code=401, detail="Invalid API Key")

    # 1. Update Session
    sid = request.sessionId
    if sid not in sessions:
        sessions[sid] = {
            "history": [], 
            "metadata": request.metadata, 
            "scam_detected": False
        }
    
    # Sync history if provided
    if request.conversationHistory:
        # In a real app we might merge, here we heavily rely on the request's history if it's stateless
        pass 
    
    # Append current message
    current_msg = request.message
    sessions[sid]["history"].append(current_msg)

    # 2. Detect Scam
    is_scam = detect_scam(current_msg.text)
    if is_scam:
        sessions[sid]["scam_detected"] = True

    # 3. Generate Reply
    if sessions[sid]["scam_detected"]:
        reply_text = generate_agent_reply(current_msg.text, request.dict())
        
        # Add our reply to history
        our_reply = {
            "sender": "user",
            "text": reply_text,
            "timestamp": datetime.datetime.now().isoformat()
        }
        sessions[sid]["history"].append(our_reply)

        
        # 4. Check if we should end/callback (Simple rule: > 4 messages triggers report)
        if len(sessions[sid]["history"]) >= 4:
            background_tasks.add_task(send_callback, sid, sessions[sid])
            
        return HoneyPotResponse(status="success", reply=reply_text)
    else:
        # If not scam, be normal or ignore? Problem says "If scam intent is detected... Agent is activated"
        # If NOT detected, maybe we just say generic greeting or don't reply?
        # But API must return something.
        return HoneyPotResponse(status="success", reply="Hello, how can I help you?")

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
