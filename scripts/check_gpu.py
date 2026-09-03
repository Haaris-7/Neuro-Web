"""Report CUDA availability and whether the GPU can run TRIBE v2 locally.

Peak VRAM is set by the largest feature extractor because TRIBE v2 loads them
one at a time and frees each after caching its features:
  video only  (V-JEPA2 ViT-G)          ~6-8 GB
  video+text  (+ Llama-3.2-3B, fp32)   ~13-16 GB
"""

import sys

VIDEO_ONLY_GB = 8.0
VIDEO_TEXT_GB = 16.0
COMFORTABLE_GB = 24.0


def main() -> int:
    try:
        import torch
    except ImportError:
        print("PyTorch is not installed. Run `make setup-backend`.")
        return 1

    print(f"PyTorch {torch.__version__} (CUDA build: {torch.version.cuda or 'none'})")
    if not torch.cuda.is_available():
        print()
        print("CUDA is not available. TRIBE v2 requires an NVIDIA GPU.")
        print("  - Install NVIDIA drivers: https://www.nvidia.com/drivers")
        print("  - Install a CUDA build of PyTorch: https://pytorch.org/get-started")
        print("  - To exercise the app without a GPU: INFERENCE_BACKEND=mock make run")
        return 1

    verdicts = []
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        vram = props.total_mem / (1024**3)
        print(f"\nGPU {i}: {torch.cuda.get_device_name(i)}")
        print(f"  VRAM:          {vram:.1f} GB")
        print(f"  Compute:       {props.major}.{props.minor}")
        if vram >= COMFORTABLE_GB:
            verdict = "video+text with headroom"
        elif vram >= VIDEO_TEXT_GB:
            verdict = "video+text (default)"
        elif vram >= VIDEO_ONLY_GB:
            verdict = "video only: set TRIBE_MODALITIES=video"
        else:
            verdict = "insufficient for TRIBE v2"
        print(f"  Recommendation: {verdict}")
        verdicts.append(vram >= VIDEO_ONLY_GB)

    print()
    if any(verdicts):
        print("Next steps:")
        print("  1. make setup-tribe")
        print("  2. For the text modality: set HF_TOKEN in .env and accept the Llama 3.2 licence")
        print("     at https://huggingface.co/meta-llama/Llama-3.2-3B")
        print("  3. make run")
        return 0
    print("No GPU with enough VRAM was found (minimum ~8 GB for video-only mode).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
