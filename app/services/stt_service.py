import tempfile
import os
from faster_whisper import WhisperModel

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

def transcribe_audio(audio_bytes: bytes) -> str:
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp:
            temp.write(audio_bytes)
            temp_path = temp.name

        print(f"임시파일 생성됨: {temp_path}")
        print(f"생성 직후 존재 여부: {os.path.exists(temp_path)}")

        segments, info = model.transcribe(
            temp_path,
            language="ko"
        )

        text = "".join(segment.text for segment in segments).strip()
        return text

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"임시파일 삭제됨: {temp_path}")
            print(f"삭제 후 존재 여부: {os.path.exists(temp_path)}")