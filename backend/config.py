import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    @property
    def DATA_DIR(self) -> str:
        return os.environ.get("DATA_DIR", str(Path(__file__).resolve().parent.parent / "data"))

    @property
    def CAPTURE_DURATION(self) -> int:
        return int(os.environ.get("CAPTURE_DURATION", "30"))

    @property
    def CAPTURE_VIEWPORT_W(self) -> int:
        return int(os.environ.get("CAPTURE_VIEWPORT_W", "1440"))

    @property
    def CAPTURE_VIEWPORT_H(self) -> int:
        return int(os.environ.get("CAPTURE_VIEWPORT_H", "900"))

    @property
    def MAX_VIDEO_SIZE_MB(self) -> int:
        return int(os.environ.get("MAX_VIDEO_SIZE_MB", "100"))

    @property
    def MAX_REDIRECTS(self) -> int:
        return int(os.environ.get("MAX_REDIRECTS", "5"))

    @property
    def MAX_URL_LENGTH(self) -> int:
        return int(os.environ.get("MAX_URL_LENGTH", "2048"))

    @property
    def BACKEND_PORT(self) -> int:
        return int(os.environ.get("BACKEND_PORT", "8000"))

    @property
    def LLM_API_KEY(self) -> str | None:
        v = os.environ.get("LLM_API_KEY")
        return v if v else None

    @property
    def LLM_PROVIDER(self) -> str:
        return os.environ.get("LLM_PROVIDER", "openai")

    @property
    def HF_TOKEN(self) -> str | None:
        v = os.environ.get("HF_TOKEN")
        return v if v else None

    @property
    def VIDEO_WEIGHT(self) -> float:
        return float(os.environ.get("VIDEO_WEIGHT", "0.6"))

    @property
    def TEXT_WEIGHT(self) -> float:
        return float(os.environ.get("TEXT_WEIGHT", "0.4"))

    @property
    def MODEL_CACHE_DIR(self) -> str:
        return os.environ.get("MODEL_CACHE_DIR", str(Path(__file__).resolve().parent.parent / "data" / "cache"))


settings = Settings()
