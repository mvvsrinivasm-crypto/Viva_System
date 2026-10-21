import os
import sys
import subprocess
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.asr_service import convert_to_pcm_wav, ASRService


def test_mobile_audio_pipeline():
    test_dir = backend_dir / "data" / "test_audio"
    test_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate a valid 1-second sine wave audio in webm and mp4 formats using ffmpeg
    sample_webm = test_dir / "test_mobile.webm"
    sample_mp4 = test_dir / "test_mobile.mp4"

    # Generate synthetic webm (typical Android Chrome recording)
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
        "-c:a", "libopus", "-b:a", "64k", str(sample_webm)
    ], capture_output=True, check=True)

    # Generate synthetic mp4 / aac (typical iOS Safari recording)
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
        "-c:a", "aac", "-b:a", "64k", str(sample_mp4)
    ], capture_output=True, check=True)

    assert sample_webm.exists() and sample_webm.stat().st_size > 500
    assert sample_mp4.exists() and sample_mp4.stat().st_size > 500

    # 2. Test convert_to_pcm_wav on webm
    wav_webm, meta_webm = convert_to_pcm_wav(sample_webm)
    assert wav_webm.exists()
    assert meta_webm["sample_rate"] == 16000
    assert meta_webm["channels"] == 1
    assert "PCM WAV 16-bit" in meta_webm["format"]

    # 3. Test convert_to_pcm_wav on mp4 (iOS format)
    wav_mp4, meta_mp4 = convert_to_pcm_wav(sample_mp4)
    assert wav_mp4.exists()
    assert meta_mp4["sample_rate"] == 16000
    assert meta_mp4["channels"] == 1
    assert "PCM WAV 16-bit" in meta_mp4["format"]

    # 4. Test ASRService with Mock Provider
    config = {
        "USE_MOCK_ASR_IF_NO_KEY": True,
        "NEMOTRON_API_KEY": "",
        "GEMINI_API_KEY": "",
    }
    svc = ASRService(config)

    transcript_webm = svc.transcribe_audio(
        sample_webm,
        context_hint="FIFO Queue Data Structure",
        mime_type="audio/webm;codecs=opus"
    )
    assert len(transcript_webm) > 0
    print("WebM Transcribe Result:", transcript_webm)

    transcript_mp4 = svc.transcribe_audio(
        sample_mp4,
        context_hint="FIFO Queue Data Structure",
        mime_type="audio/mp4"
    )
    assert len(transcript_mp4) > 0
    print("MP4 Transcribe Result:", transcript_mp4)

    # 5. Clean up test artifacts
    for p in [sample_webm, sample_mp4, wav_webm, wav_mp4]:
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

    print("Mobile ASR pipeline verification: SUCCESS!")


if __name__ == "__main__":
    test_mobile_audio_pipeline()
