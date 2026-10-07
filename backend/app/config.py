import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "kare-viva-secret-key-2026-production-kalasalingam")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "kare-jwt-super-secret-key-2026-viva-system")
    JWT_ACCESS_TOKEN_EXPIRES_HOURS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", "24"))

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://neondb_owner:npg_KzX74atmlRWB@ep-bold-fog-b55jjztk-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require",
    )
    # Neon postgres compatibility: ensure 'postgresql://' instead of 'postgres://'
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Storage paths
    UPLOAD_FOLDER = BASE_DIR / os.getenv("UPLOAD_FOLDER", "data/uploads")
    AUDIO_FOLDER = BASE_DIR / os.getenv("AUDIO_FOLDER", "data/audio")

    # CORS
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    ]

    # External ASR & LLM Services
    NEMOTRON_API_KEY = os.getenv("NEMOTRON_API_KEY", "")
    NEMOTRON_ENDPOINT = os.getenv("NEMOTRON_ENDPOINT", "https://integrate.api.nvidia.com/v1/audio/transcriptions")
    NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/nemotron-3.5-asr-streaming-0.6b")
    USE_MOCK_ASR_IF_NO_KEY = os.getenv("USE_MOCK_ASR_IF_NO_KEY", "True").lower() in ("true", "1", "yes")

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    # For automated unit testing without destroying production tables
    # Neon postgres can be used or separate test database / schema
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
