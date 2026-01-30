from fastapi import FastAPI
from voice_detection.main import router as voice_router
from honeypot.main import router as honeypot_router

app = FastAPI(title="Hackathon Unified API")

# Include routes from both modules
# They already define their full paths (/api/voice-detection, /api/chat)
app.include_router(voice_router)
app.include_router(honeypot_router)

@app.get("/")
def home():
    return {"status": "running", "endpoints": ["/api/voice-detection", "/api/chat"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
