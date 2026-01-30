from fastapi import FastAPI, HTTPException, Header, Body
from pydantic import BaseModel
import base64
import random
import uvicorn
import io

app = FastAPI(title="AI Voice Detection API")

# --- Configuration ---
VALID_API_KEYS = ["sk_test_123456789"]  # Example key from problem statement
SUPPORTED_LANGUAGES = ["Tamil", "English", "Hindi", "Malayalam", "Telugu"]

# --- Models ---
class VoiceRequest(BaseModel):
    language: str
    audioFormat: str
    audioBase64: str

class VoiceResponse(BaseModel):
    status: str
    language: str
    classification: str
    confidenceScore: float
    explanation: str

class ErrorResponse(BaseModel):
    status: str
    message: str

# --- Helpers ---
def validate_api_key(x_api_key: str = Header(...)):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key

def analyze_audio(audio_bytes: bytes, language: str):
    """
    Placeholder for actual model inference.
    In a real scenario, we would load a .pth/.h5 model here and run inference.
    """
    # Mock logic for demonstration:
    # Randomly classify for now since we don't have a trained model file.
    # In integration, replace this with `model.predict(audio_bytes)`
    
    score = random.uniform(0.6, 0.99)
    classification = "AI_GENERATED" if score > 0.8 else "HUMAN"
    
    explanation = "Detected synthetic spectral patterns." if classification == "AI_GENERATED" else "Natural breathing and pitch variations detected."
    
    return classification, score, explanation

# --- Endpoints ---
from fastapi import APIRouter

router = APIRouter()

@router.post("/api/voice-detection", response_model=VoiceResponse, responses={401: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
async def detect_voice(
    request: VoiceRequest,
    x_api_key: str = Header(...)
):
    # 1. Validate API Key
    if x_api_key not in VALID_API_KEYS:
        # FastAPI handles 422 for missing headers, but we want custom error format if possible, 
        # or we rely on the HTTPException handler.
        return VoiceResponse( # Fallback if we want to return 200 with error status, or raise Exception
            status="error",
            language=request.language,
            classification="UNKNOWN",
            confidenceScore=0.0,
            explanation="Invalid API Key"
        ) # Actually better to use JSONResponse for strict adherence or HTTPException

    # 2. Validate Inputs
    if request.language not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported Language")
    
    if request.audioFormat.lower() != "mp3":
        raise HTTPException(status_code=400, detail="Only mp3 format is supported")

    # 3. Decode Audio
    try:
        audio_data = base64.b64decode(request.audioBase64)
        if not audio_data:
             raise ValueError("Empty audio")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Base64 audio")

    # 4. Analyze
    classification, score, explanation = analyze_audio(audio_data, request.language)

    # 5. Return Response
    return VoiceResponse(
        status="success",
        language=request.language,
        classification=classification,
        confidenceScore=round(score, 2),
        explanation=explanation
    )

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
