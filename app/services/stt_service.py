import os
import tempfile
from faster_whisper import WhisperModel

# ============================================
# Faster-Whisper STT 모델 로드
# ============================================
# small 모델:
# - 한국어 인식 성능이 괜찮음
# - CPU 환경에서도 비교적 빠르게 동작
# device="cpu" :
# - GPU 없이 CPU만 사용
# compute_type="int8" :
# - 메모리 사용량 감소 및 CPU 추론 속도 향상
model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)


def transcribe_audio(audio_bytes: bytes) -> str:
    """
    프론트에서 전달받은 음성 데이터를 텍스트로 변환하는 함수

    매개변수:
        audio_bytes : 프론트(MediaRecorder)가 전송한 음성 데이터

    반환값:
        STT 변환 결과 문자열
    """

    # 임시 파일 경로 저장용 변수
    temp_path = None

    try:
        # ============================================
        # 1. 메모리에 존재하는 음성 데이터를
        #    임시 webm 파일로 저장
        # ============================================
        #
        # Faster-Whisper는 파일 경로를 입력으로 받기 때문에
        # 메모리상의 bytes 데이터를 잠시 파일로 변환한다.
        #
        # delete=False:
        #   with 블록이 종료되어도 자동 삭제하지 않음
        #   → STT 처리 완료 후 finally에서 직접 삭제
        #
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".webm"
        ) as temp:

            temp.write(audio_bytes)
            temp_path = temp.name

        # ============================================
        # 2. Faster-Whisper를 이용한 STT 수행
        # ============================================
        #
        # language="ko"
        # → 한국어 음성 인식 모드
        #
        segments, info = model.transcribe(
            temp_path,
            language="ko"
        )

        # ============================================
        # 3. 여러 문장 조각(segment)을 하나의 문자열로 합침
        # ============================================
        #
        # 예:
        # ["안녕하세요", "사하구청입니다"]
        #
        # ↓
        #
        # "안녕하세요 사하구청입니다"
        #
        text = "".join(
            segment.text for segment in segments
        ).strip()

        return text

    finally:
        # ============================================
        # 4. STT 처리 후 임시 음성 파일 즉시 삭제
        # ============================================
        #
        # 음성 개인정보 보호를 위해
        # 음성 파일은 디스크에 저장하지 않고
        # 텍스트 변환 직후 즉시 삭제한다.
        #
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)