import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_ROOT = Path(__file__).resolve().parent.parent

VALID_MODALITIES = ("video", "text")
VALID_BACKENDS = ("tribe", "mock")
VALID_LLM_PROVIDERS = ("openai", "anthropic")


def _env_str(key: str, default: str) -> str:
    value = os.environ.get(key, "")
    return value.strip() or default


def _env_int(key: str, default: int) -> int:
    return int(_env_str(key, str(default)))


def _env_float(key: str, default: float) -> float:
    return float(_env_str(key, str(default)))


def _env_optional(key: str) -> str | None:
    value = os.environ.get(key, "").strip()
    return value or None


class Settings:
    @property
    def DATA_DIR(self) -> str:
        return _env_str("DATA_DIR", str(_ROOT / "data"))

    @property
    def MODEL_CACHE_DIR(self) -> str:
        return _env_str("MODEL_CACHE_DIR", str(Path(self.DATA_DIR) / "cache"))

    @property
    def CAPTURE_DURATION(self) -> int:
        return _env_int("CAPTURE_DURATION", 30)

    @property
    def CAPTURE_VIEWPORT_W(self) -> int:
        return _env_int("CAPTURE_VIEWPORT_W", 1440)

    @property
    def CAPTURE_VIEWPORT_H(self) -> int:
        return _env_int("CAPTURE_VIEWPORT_H", 900)

    @property
    def MAX_VIDEO_SIZE_MB(self) -> int:
        return _env_int("MAX_VIDEO_SIZE_MB", 100)

    @property
    def MAX_REDIRECTS(self) -> int:
        return _env_int("MAX_REDIRECTS", 5)

    @property
    def MAX_URL_LENGTH(self) -> int:
        return _env_int("MAX_URL_LENGTH", 2048)

    @property
    def BACKEND_HOST(self) -> str:
        return _env_str("BACKEND_HOST", "127.0.0.1")

    @property
    def BACKEND_PORT(self) -> int:
        return _env_int("BACKEND_PORT", 8000)

    @property
    def CHAT_RATE_LIMIT_PER_MINUTE(self) -> int:
        return _env_int("CHAT_RATE_LIMIT_PER_MINUTE", 20)

    @property
    def FRONTEND_ORIGIN(self) -> str:
        return _env_str("FRONTEND_ORIGIN", "http://localhost:3000")

    @property
    def INFERENCE_BACKEND(self) -> str:
        value = _env_str("INFERENCE_BACKEND", "tribe").lower()
        if value not in VALID_BACKENDS:
            raise ValueError(
                f"INFERENCE_BACKEND must be one of {VALID_BACKENDS}, got {value!r}"
            )
        return value

    @property
    def TRIBE_MODALITIES(self) -> tuple[str, ...]:
        raw = _env_str("TRIBE_MODALITIES", "video,text")
        chosen = tuple(m.strip().lower() for m in raw.split(",") if m.strip())
        unknown = [m for m in chosen if m not in VALID_MODALITIES]
        if unknown or not chosen:
            raise ValueError(
                f"TRIBE_MODALITIES must be a comma-separated subset of {VALID_MODALITIES}, got {raw!r}"
            )
        return chosen

    @property
    def TRIBE_MODEL_ID(self) -> str:
        return _env_str("TRIBE_MODEL_ID", "facebook/tribev2")

    @property
    def TRIBE_NUM_WORKERS(self) -> int:
        return _env_int("TRIBE_NUM_WORKERS", 4)

    @property
    def TEXT_READING_WPM(self) -> float:
        return _env_float("TEXT_READING_WPM", 240.0)

    @property
    def TEXT_CONTEXT_WORDS(self) -> int:
        return _env_int("TEXT_CONTEXT_WORDS", 256)

    @property
    def HF_TOKEN(self) -> str | None:
        return _env_optional("HF_TOKEN")

    @property
    def LLM_API_KEY(self) -> str | None:
        return _env_optional("LLM_API_KEY")

    @property
    def LLM_PROVIDER(self) -> str:
        value = _env_str("LLM_PROVIDER", "openai").lower()
        if value not in VALID_LLM_PROVIDERS:
            raise ValueError(
                f"LLM_PROVIDER must be one of {VALID_LLM_PROVIDERS}, got {value!r}"
            )
        return value

    @property
    def LLM_MODEL(self) -> str:
        default = "gpt-4o-mini" if self.LLM_PROVIDER == "openai" else "claude-3-5-haiku-latest"
        return _env_str("LLM_MODEL", default)

    @property
    def LLM_BASE_URL(self) -> str | None:
        return _env_optional("LLM_BASE_URL")

    @property
    def llm_available(self) -> bool:
        return self.LLM_API_KEY is not None


settings = Settings()
