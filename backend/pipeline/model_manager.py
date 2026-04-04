"""Singleton TRIBE v2 model manager with eager warm-up, health check, and VRAM reporting."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)

try:
    import torch
except ImportError:
    torch = None  # type: ignore[assignment]

try:
    from tribev2 import TribeModel
except ImportError:
    TribeModel = None  # type: ignore[assignment,misc]


@dataclass(frozen=True)
class GPUInfo:
    available: bool
    device_count: int
    devices: list[dict]

    @staticmethod
    def detect() -> GPUInfo:
        if torch is None or not torch.cuda.is_available():
            return GPUInfo(available=False, device_count=0, devices=[])
        count = torch.cuda.device_count()
        devices = []
        for i in range(count):
            props = torch.cuda.get_device_properties(i)
            total_gb = props.total_mem / (1024**3)
            devices.append(
                {
                    "index": i,
                    "name": torch.cuda.get_device_name(i),
                    "total_vram_gb": round(total_gb, 1),
                    "sufficient": total_gb >= 16,
                    "recommended": total_gb >= 24,
                }
            )
        return GPUInfo(available=True, device_count=count, devices=devices)


class ModelManager:
    """Thread-safe singleton for loading and managing the TRIBE v2 model."""

    _instance: ModelManager | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._model: TribeModel | None = None  # type: ignore[annotation-unchecked]
        self._loaded = False
        self._load_time_s: float = 0.0
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
    def model(self) -> TribeModel | None:  # type: ignore[annotation-unchecked]
        return self._model

    @property
    def gpu_info(self) -> GPUInfo:
        if self._gpu_info is None:
            self._gpu_info = GPUInfo.detect()
        return self._gpu_info

    @property
    def error(self) -> str | None:
        return self._error

    def health(self) -> dict:
        gpu = self.gpu_info
        return {
            "model_loaded": self._loaded,
            "load_time_s": round(self._load_time_s, 2),
            "gpu_available": gpu.available,
            "gpu_count": gpu.device_count,
            "devices": gpu.devices,
            "error": self._error,
        }

    def load_model(self) -> None:
        """Load TRIBE v2 model. Call from a non-event-loop thread (e.g. asyncio.to_thread)."""
        if self._loaded:
            return

        if TribeModel is None:
            self._error = (
                "tribev2 package not installed. "
                "Clone https://github.com/facebookresearch/tribev2 and run `pip install -e .`"
            )
            logger.error(self._error)
            return

        gpu = self.gpu_info
        if not gpu.available:
            self._error = (
                "CUDA is not available. TRIBE v2 requires an NVIDIA GPU with 16GB+ VRAM."
            )
            logger.error(self._error)
            return

        for dev in gpu.devices:
            if not dev["sufficient"]:
                logger.warning(
                    "GPU %s has %.1f GB VRAM — may be insufficient (16GB+ needed)",
                    dev["name"],
                    dev["total_vram_gb"],
                )

        cache_dir = Path(settings.MODEL_CACHE_DIR)
        cache_dir.mkdir(parents=True, exist_ok=True)

        hf_token = settings.HF_TOKEN
        if not hf_token:
            self._error = (
                "HF_TOKEN not set. TRIBE v2 requires a HuggingFace token "
                "for gated model access. Get one at https://huggingface.co/settings/tokens"
            )
            logger.error(self._error)
            return

        logger.info("Loading TRIBE v2 model (this may take a minute on first run)...")
        t0 = time.monotonic()
        try:
            self._model = TribeModel.from_pretrained(
                "facebook/tribev2",
                cache_folder=str(cache_dir),
            )
            self._load_time_s = time.monotonic() - t0
            self._loaded = True
            self._error = None
            logger.info(
                "TRIBE v2 loaded in %.1fs — GPU: %s",
                self._load_time_s,
                gpu.devices[0]["name"] if gpu.devices else "unknown",
            )
        except Exception as exc:
            self._load_time_s = time.monotonic() - t0
            self._error = f"Failed to load TRIBE v2: {exc}"
            logger.exception(self._error)

    def warm_up(self) -> None:
        """Optional dry-run to warm CUDA allocator. Call after load_model."""
        if not self._loaded or self._model is None:
            return
        if torch is None:
            return
        try:
            logger.info("Warming up CUDA allocator...")
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            dummy = torch.zeros(1, device=device)
            del dummy
            if torch.cuda.is_available():
                torch.cuda.synchronize()
                allocated = torch.cuda.memory_allocated() / (1024**3)
                reserved = torch.cuda.memory_reserved() / (1024**3)
                logger.info(
                    "CUDA warm-up done — allocated: %.2f GB, reserved: %.2f GB",
                    allocated,
                    reserved,
                )
        except Exception:
            logger.warning("CUDA warm-up failed (non-fatal)", exc_info=True)
