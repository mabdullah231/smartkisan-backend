from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response
from typing import Optional
import httpx
from models.auth import User
from models.api import APIConfig
from helpers.token_helper import get_current_user
from pydantic import BaseModel

azure_router = APIRouter(prefix="/azure")

class TTSRequest(BaseModel):
    text: str
    language: str = "en-US"  # en-US, ur-PK
    voice: Optional[str] = None  # Specific voice name, will use defaults if not provided

class STTResponse(BaseModel):
    text: str
    language: str
    confidence: Optional[float] = None

async def get_azure_config() -> dict:
    """Get Azure Cognitive Services configuration from database"""
    try:
        config = await APIConfig.get(category="Azure", is_active=True)
        if not config.api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Azure Speech API key not configured"
            )

        extra = config.extra_config or {}
        region = extra.get("region")
        endpoint = extra.get("endpoint")

        if not region and not endpoint:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Azure Speech region or endpoint not configured"
            )

        return {
            "api_key": config.api_key,
            "region": region,
            "endpoint": endpoint
        }
    except APIConfig.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Azure Cognitive Services not configured. Please set up Azure API configuration in admin settings."
        )


def build_tts_url(region: Optional[str], endpoint: Optional[str]) -> str:
    if endpoint:
        endpoint = endpoint.rstrip('/')
        if endpoint.endswith('/cognitiveservices/v1') or endpoint.endswith('/speech/tts/v3.0'):
            return endpoint
        return f"{endpoint}/cognitiveservices/v1"
    if not region:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Azure Speech region not configured"
        )
    return f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"


# def build_stt_url(region: Optional[str], endpoint: Optional[str], language: str) -> str:
#     if endpoint:
#         endpoint = endpoint.rstrip('/')
#         if endpoint.endswith('/speech/recognition/conversation/cognitiveservices/v1'):
#             return f"{endpoint}?language={language}" if '?language=' not in endpoint else endpoint
#         return f"{endpoint}/speech/recognition/conversation/cognitiveservices/v1?language={language}"
#     if not region:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Azure Speech region not configured"
#         )
#     return f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={language}"

def build_stt_url(region: Optional[str], language: str) -> str:
    if not region:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Azure Speech region not configured"
        )
    # Normalize language code — Azure REST STT requires exact BCP-47 tags
    lang_map = {
        "ur-IN": "ur-IN",
        "en-US": "en-US",
        "en": "en-US",
        "ur": "ur-IN",
    }
    normalized = lang_map.get(language, language)
    return f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={normalized}&format=detailed"


def get_voice_name(language: str, voice: Optional[str] = None) -> str:
    if voice:
        return voice

    voice_map = {
        "en-US": "en-US-AriaNeural",
        "ur-PK": "ur-PK-AsadNeural"
    }

    return voice_map.get(language, "en-US-AriaNeural")


def build_ssml(text: str, voice_name: str, language: str) -> str:
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f"<speak version='1.0' xml:lang='{language}'>"
        f"<voice name='{voice_name}'>"
        f"{escaped}"
        f"</voice>"
        f"</speak>"
    )

@azure_router.post("/tts")
async def text_to_speech(
    tts_request: TTSRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        azure_config = await get_azure_config()
        tts_url = build_tts_url(azure_config.get("region"), azure_config.get("endpoint"))
        voice_name = get_voice_name(tts_request.language, tts_request.voice)
        ssml = build_ssml(tts_request.text, voice_name, tts_request.language)

        headers = {
            "Ocp-Apim-Subscription-Key": azure_config["api_key"],
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
            "User-Agent": "SmartKisan"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(tts_url, headers=headers, content=ssml.encode("utf-8"))
            if response.status_code == 404 and azure_config.get("region") and azure_config.get("endpoint"):
                fallback_url = build_tts_url(azure_config.get("region"), None)
                if fallback_url != tts_url:
                    response = await client.post(fallback_url, headers=headers, content=ssml.encode("utf-8"))

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"TTS Error: {response.status_code} {response.text}"
            )

        return Response(
            content=response.content,
            media_type="audio/wav",
            headers={"Content-Disposition": "inline"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS Error: {str(e)}"
        )

@azure_router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    audio_file: UploadFile = File(...),
    language: str = Form("en-US"),
    current_user: User = Depends(get_current_user)
):
    try:
        if not audio_file.content_type.startswith("audio/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an audio file"
            )

        azure_config = await get_azure_config()
        stt_url = build_stt_url(azure_config.get("region"), language)
        audio_data = await audio_file.read()

        print(f"[STT DEBUG] language received: '{language}'")
        print(f"[STT DEBUG] stt_url: '{stt_url}'")
        print(f"[STT DEBUG] audio content_type: '{audio_file.content_type}'")
        print(f"[STT DEBUG] region: '{azure_config.get('region')}'")
        print(f"[STT DEBUG] audio size: {len(audio_data)} bytes")
        print(f"[STT DEBUG] audio header bytes: {audio_data[:4]}")

        headers = {
            "Ocp-Apim-Subscription-Key": azure_config["api_key"],
            "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(stt_url, headers=headers, content=audio_data)

        print(f"[STT DEBUG] Azure response: {response.status_code} | {response.text}")

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"STT Error: {response.status_code} {response.text}"
            )

        data = response.json()
        recognition_status = data.get("RecognitionStatus")

        if recognition_status in ("NoMatch", "InitialSilenceTimeout"):
            return STTResponse(text="", language=language, confidence=None)

        if recognition_status != "Success":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recognition failed: {recognition_status}"
            )

        nbest = data.get("NBest", [])
        if nbest:
            best = nbest[0]
            return STTResponse(
                text=best.get("Display", data.get("DisplayText", "")),
                language=language,
                confidence=best.get("Confidence")
            )

        return STTResponse(
            text=data.get("DisplayText", ""),
            language=language,
            confidence=None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"STT Error: {str(e)}"
        )

@azure_router.get("/voices")
async def get_available_voices(
    current_user: User = Depends(get_current_user)
):
    try:
        azure_config = await get_azure_config()
        tts_url = build_tts_url(azure_config.get("region"), azure_config.get("endpoint"))

        headers = {
            "Ocp-Apim-Subscription-Key": azure_config["api_key"],
            "User-Agent": "SmartKisan"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{tts_url}?mkt=en-US", headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Voice list error: {response.status_code} {response.text}"
            )

        data = response.json()
        voices = []
        for voice in data.get("voices", []):
            if voice.get("locale") in ["en-US", "ur-PK"]:
                voices.append({
                    "name": voice.get("name"),
                    "locale": voice.get("locale"),
                    "gender": voice.get("gender", "Unknown"),
                    "voice_type": voice.get("voiceType", "Unknown")
                })

        return {"voices": voices}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving voices: {str(e)}"
        )