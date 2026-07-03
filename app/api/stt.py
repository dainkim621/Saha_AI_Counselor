from fastapi import APIRouter, UploadFile, File
from app.services.stt_service import transcribe_audio

# STT 관련 API들을 묶어서 관리할 라우터 생성
router = APIRouter()


# 프론트에서 POST /stt 요청을 보내면 실행되는 API
@router.post("/stt")
async def stt_endpoint(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    
    text = transcribe_audio(audio_bytes)
    
    return {
        "text": text
    }
    
