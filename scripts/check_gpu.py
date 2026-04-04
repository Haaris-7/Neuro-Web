import sys

def main():
    try:
        import torch
    except ImportError:
        print("PyTorch not installed. Run 'make setup' first.")
        sys.exit(1)

    if not torch.cuda.is_available():
        print("CUDA is not available.")
        print("TRIBE v2 requires an NVIDIA GPU with CUDA support.")
        print("Minimum: 16GB VRAM | Recommended: 24GB VRAM")
        sys.exit(1)

    device_count = torch.cuda.device_count()
    print(f"CUDA available: {device_count} device(s) found\n")

    for i in range(device_count):
        name = torch.cuda.get_device_name(i)
        total = torch.cuda.get_device_properties(i).total_mem / (1024 ** 3)
        print(f"  GPU {i}: {name}")
        print(f"  VRAM: {total:.1f} GB")

        if total < 16:
            print(f"  WARNING: {total:.1f}GB may be insufficient. TRIBE v2 needs ~16GB minimum.")
        elif total < 24:
            print(f"  OK: Should work, but 24GB+ recommended for comfortable headroom.")
        else:
            print(f"  EXCELLENT: Plenty of VRAM for TRIBE v2.")
        print()

if __name__ == "__main__":
    main()
