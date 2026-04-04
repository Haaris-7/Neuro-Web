"""GPU validation script for TRIBE v2 compatibility.

Checks CUDA availability, VRAM, driver version, and estimates whether
TRIBE v2 inference will fit on the detected GPU(s).
"""

import sys


def main():
    try:
        import torch
    except ImportError:
        print("ERROR: PyTorch not installed.")
        print("  Run: pip install torch>=2.5.0")
        print("  Or:  make setup")
        sys.exit(1)

    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA compiled:   {torch.version.cuda or 'N/A'}")

    if not torch.cuda.is_available():
        print()
        print("CUDA is NOT available.")
        print("TRIBE v2 requires an NVIDIA GPU with CUDA support.")
        print()
        print("Troubleshooting:")
        print("  1. Ensure you have an NVIDIA GPU")
        print("  2. Install NVIDIA drivers: https://www.nvidia.com/drivers")
        print("  3. Install CUDA-enabled PyTorch: https://pytorch.org/get-started")
        sys.exit(1)

    device_count = torch.cuda.device_count()
    print(f"CUDA available:  Yes ({device_count} device(s))")
    print()

    any_sufficient = False

    for i in range(device_count):
        name = torch.cuda.get_device_name(i)
        props = torch.cuda.get_device_properties(i)
        total_gb = props.total_mem / (1024**3)
        compute = f"{props.major}.{props.minor}"

        print(f"  GPU {i}: {name}")
        print(f"    VRAM:           {total_gb:.1f} GB")
        print(f"    Compute cap:    {compute}")

        if total_gb < 12:
            print(f"    Status:         INSUFFICIENT — TRIBE v2 needs 16GB+")
            print(f"    Recommendation: Upgrade GPU or use cloud GPU")
        elif total_gb < 16:
            print(f"    Status:         TIGHT — may work with reduced batch size")
            print(f"    Recommendation: 16GB+ VRAM strongly recommended")
        elif total_gb < 24:
            print(f"    Status:         OK — should work for TRIBE v2 inference")
            print(f"    Recommendation: 24GB+ ideal for comfortable headroom")
            any_sufficient = True
        else:
            print(f"    Status:         EXCELLENT — plenty of VRAM for TRIBE v2")
            any_sufficient = True
        print()

    print("--- TRIBE v2 Compatibility Estimate ---")
    print()
    print("  V-JEPA2 ViT-G (video encoder):  ~8-12 GB peak")
    print("  Llama 3.2-3B (text encoder):     ~6-8 GB peak")
    print("  TRIBE v2 Transformer:            ~2-4 GB")
    print("  (Extractors load/free sequentially — peak = largest single extractor)")
    print()

    if any_sufficient:
        print("  Verdict: Your GPU should support TRIBE v2 inference.")
        print()
        print("  Next steps:")
        print("    1. Set HF_TOKEN in .env (https://huggingface.co/settings/tokens)")
        print("    2. Request access to facebook/tribev2 on HuggingFace")
        print("    3. Run `make run` to start the application")
    else:
        print("  Verdict: Your GPU may not have enough VRAM for TRIBE v2.")
        print("  Minimum: 16 GB VRAM  |  Recommended: 24 GB+ VRAM")
        sys.exit(1)


if __name__ == "__main__":
    main()
