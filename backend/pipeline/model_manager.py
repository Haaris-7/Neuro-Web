"""Singleton owner of the TRIBE v2 model with GPU detection and health reporting."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import settings

logger = logging.getLogger(__name__)

try:
    import torch
except ImportError:
    torch = None

try:
    from tribev2 import TribeModel
except ImportError:
    TribeModel = None

MIN_VRAM_GB = 16.0
RECOMMENDED_VRAM_GB = 24.0
VIDEO_ONLY_MIN_VRAM_GB = 8.0


@dataclass(frozen=True)
class GPUInfo:
    available: bool
    device_count: int
    devices: list[dict[str, Any]]

    @staticmethod
    def detect() -> GPUInfo:
        if torch is None or not torch.cuda.is_available():
            return GPUInfo(available=False, device_count=0, devices=[])
        devices = []
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            total_gb = props.total_mem / (1024**3)
            devices.append(
                {
                    "index": i,
                    "name": torch.cuda.get_device_name(i),
                    "total_vram_gb": round(total_gb, 1),
                    "sufficient": total_gb >= MIN_VRAM_GB,
                    "sufficient_video_only": total_gb >= VIDEO_ONLY_MIN_VRAM_GB,
                    "recommended": total_gb >= RECOMMENDED_VRAM_GB,
                }
            )
        return GPUInfo(available=True, device_count=len(devices), devices=devices)


class ModelManager:
    _instance: ModelManager | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._model: Any = None
        self._loaded = False
        self._load_time_s = 0.0
        self._gpu_info: GPUInfo | None = None
        self._error: str | None = None

    @classmethod
    def get(cls) -> ModelManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def model(self) -> Any:
        return self._model

    @property
    def gpu_info(self) -> GPUInfo:
        if self._gpu_info is None:
            self._gpu_info = GPUInfo.detect()
        return self._gpu_info

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def inference_ready(self) -> bool:
        return settings.INFERENCE_BACKEND == "mock" or self._loaded

    def health(self) -> dict[str, Any]:
        gpu = self.gpu_info
        return {
            "inference_backend": settings.INFERENCE_BACKEND,
            "modalities": list(settings.TRIBE_MODALITIES),
            "inference_ready": self.inference_ready,
            "model_loaded": self._loaded,
            "load_time_s": round(self._load_time_s, 2),
            "gpu_available": gpu.available,
            "gpu_count": gpu.device_count,
            "devices": gpu.devices,
            "llm_available": settings.llm_available,
            "llm_provider": settings.LLM_PROVIDER if settings.llm_available else None,
            "error": self._error,
        }

    def _preflight(self) -> str | None:
        if TribeModel is None:
            return (
                "tribev2 package not installed. Run `make setup-tribe` "
                "(clones https://github.com/facebookresearch/tribev2 and installs it)."
            )
        gpu = self.gpu_info
        if not gpu.available:
            return "CUDA is not available. TRIBE v2 requires an NVIDIA GPU."
        if "text" in settings.TRIBE_MODALITIES and not settings.HF_TOKEN:
            return (
                "HF_TOKEN is not set but the text modality is enabled. The text encoder "
                "(meta-llama/Llama-3.2-3B) is gated; add HF_TOKEN to .env or set "
                "TRIBE_MODALITIES=video."
            )
        for dev in gpu.devices:
            threshold = MIN_VRAM_GB if "text" in settings.TRIBE_MODALITIES else VIDEO_ONLY_MIN_VRAM_GB
            if dev["total_vram_gb"] < threshold:
                logger.warning(
                    "GPU %s has %.1f GB VRAM; %.0f GB+ recommended for modalities %s",
                    dev["name"],
                    dev["total_vram_gb"],
                    threshold,
                    ",".join(settings.TRIBE_MODALITIES),
                )
        return None

    def load_model(self) -> None:
        """Load TRIBE v2 weights. Blocking; call from a worker thread."""
        if self._loaded or settings.INFERENCE_BACKEND == "mock":
            return
        problem = self._preflight()
        if problem:
            self._error = problem
            logger.error(problem)
            return

        cache_dir = Path(settings.MODEL_CACHE_DIR) / "tribe"
        cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Loading TRIBE v2 (%s); first run downloads weights", settings.TRIBE_MODEL_ID)
        t0 = time.monotonic()
        try:
            self._model = TribeModel.from_pretrained(
                settings.TRIBE_MODEL_ID,
                cache_folder=str(cache_dir),
                config_update={"data.num_workers": settings.TRIBE_NUM_WORKERS},
            )
            self._load_time_s = time.monotonic() - t0
            self._loaded = True
            self._error = None
            logger.info("TRIBE v2 loaded in %.1fs", self._load_time_s)
        except Exception as exc:
            self._load_time_s = time.monotonic() - t0
            self._error = f"Failed to load TRIBE v2: {exc}"
            logger.exception(self._error)
