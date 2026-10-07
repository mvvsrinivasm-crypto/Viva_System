import os
import subprocess
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple
import requests

logger = logging.getLogger(__name__)


def convert_to_pcm_wav(input_path: Path) -> Tuple[Path, dict]:
    """
    Converts any input audio format (webm, opus, ogg, wav, mp3, mp4)
    into standard 16kHz, mono, 16-bit PCM WAV using FFmpeg.
    Returns: (output_wav_path, audio_metadata_dict)
    """
    output_path = input_path.parent / f"{input_path.stem}_16k.wav"

    # Audio inspection & FFmpeg conversion
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(output_path),
    ]

    try:
        res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg conversion failed: %s (stderr: %s)", e, e.stderr)
        raise RuntimeError(f"Audio conversion failed: {e.stderr[:200]}")
    except FileNotFoundError:
        logger.warning("FFmpeg not found on PATH, falling back to original audio file.")
        return input_path, {"sample_rate": 16000, "channels": 1, "format": "original"}

    converted_size = output_path.stat().st_size if output_path.exists() else 0
    metadata = {
        "format": "PCM WAV 16-bit",
        "sample_rate": 16000,
        "channels": 1,
        "file_size": converted_size,
    }

    return output_path, metadata


class BaseASRProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_file_path: Path, context_hint: str = "") -> str:
        """Transcribe an audio file into text."""
        pass


class NemotronASRProvider(BaseASRProvider):
    """
    NVIDIA Nemotron ASR service.
    Uses model: nvidia/nemotron-3.5-asr-streaming-0.6b
    """
    def __init__(self, api_key: str, endpoint: str, model: str):
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model or "nvidia/nemotron-3.5-asr-streaming-0.6b"

    def transcribe(self, audio_file_path: Path, context_hint: str = "") -> str:
        if not audio_file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        file_size = audio_file_path.stat().st_size
        if file_size < 400:
            logger.warning("Audio file too small: %s bytes", file_size)
            return ""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        with open(audio_file_path, "rb") as f:
            files = {"file": (audio_file_path.name, f, "audio/wav")}
            data = {"model": self.model, "language": "en"}
            if context_hint:
                data["prompt"] = context_hint[:200]

            logger.info("Submitting audio to Nemotron ASR endpoint: %s (model: %s)", self.endpoint, self.model)
            response = requests.post(
                self.endpoint,
                headers=headers,
                files=files,
                data=data,
                timeout=45,
            )

        logger.info("Nemotron ASR response status: %s", response.status_code)
        if response.status_code != 200:
            logger.error("Nemotron ASR error %s: %s", response.status_code, response.text[:250])
            raise RuntimeError(f"Nemotron ASR error ({response.status_code}): {response.text[:200]}")

        result_data = response.json()
        transcript = result_data.get("text") or result_data.get("transcript") or ""
        logger.info("Nemotron ASR produced transcript length: %s chars", len(transcript))
        return transcript.strip()


class ASRService:
    def __init__(self, config):
        self.api_key = config.get("NEMOTRON_API_KEY", "")
        self.endpoint = config.get("NEMOTRON_ENDPOINT", "https://integrate.api.nvidia.com/v1/audio/transcriptions")
        self.model = config.get("NEMOTRON_MODEL", "nvidia/nemotron-3.5-asr-streaming-0.6b")

        if self.api_key:
            self.provider = NemotronASRProvider(
                api_key=self.api_key,
                endpoint=self.endpoint,
                model=self.model,
            )
            self.provider_name = "Nemotron ASR"
        else:
            self.provider = None
            self.provider_name = "Speech Recognition (Local)"

    def transcribe_audio(self, raw_audio_path: Path, context_hint: str = "", mime_type: str = "audio/webm") -> str:
        """
        Full end-to-end audio pipeline:
        1. Log audio metadata
        2. Convert to 16kHz mono PCM WAV via FFmpeg
        3. Call ASR provider
        4. Clean temporary converted file
        """
        raw_size = raw_audio_path.stat().st_size if raw_audio_path.exists() else 0
        logger.info("Received audio: filename=%s, MIME=%s, raw_size=%s bytes", raw_audio_path.name, mime_type, raw_size)

        if raw_size < 300:
            logger.warning("Uploaded audio is empty or too small (%s bytes)", raw_size)
            return ""

        # Step 1: Decode & convert to 16kHz mono PCM WAV
        wav_path, meta = convert_to_pcm_wav(raw_audio_path)
        logger.info(
            "Audio converted: format=%s, sample_rate=%s, channels=%s, converted_size=%s bytes",
            meta["format"], meta["sample_rate"], meta["channels"], meta["file_size"]
        )

        transcript = ""
        # Step 2: Transcribe via provider
        if self.provider:
            try:
                transcript = self.provider.transcribe(wav_path, context_hint=context_hint)
            except Exception as e:
                logger.error("ASR provider failed: %s", e)
                raise
        else:
            logger.info("NEMOTRON_API_KEY not configured. Awaiting client transcript or manual entry.")
            transcript = ""

        # Step 3: Clean temporary 16k WAV if distinct
        if wav_path != raw_audio_path and wav_path.exists():
            try:
                wav_path.unlink()
            except Exception:
                pass

        return transcript.strip()
