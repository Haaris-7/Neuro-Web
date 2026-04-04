#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
#  Neuro Web — Interactive Setup
#  Guides you through installing everything needed to run the full stack.
# ─────────────────────────────────────────────────────────────────────────────

# ── Colors & formatting ──────────────────────────────────────────────────────

BOLD="\033[1m"
DIM="\033[2m"
RESET="\033[0m"
CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
MAGENTA="\033[35m"
BLUE="\033[34m"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
DATA_DIR="$ROOT_DIR/data"
SCRIPTS_DIR="$ROOT_DIR/scripts"
VENV_DIR="$BACKEND_DIR/.venv"
ENV_FILE="$ROOT_DIR/.env"
ENV_EXAMPLE="$ROOT_DIR/.env.example"

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

# ── Helper functions ─────────────────────────────────────────────────────────

banner() {
  echo ""
  echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${CYAN}${BOLD}║                                                              ║${RESET}"
  echo -e "${CYAN}${BOLD}║       ⬡  N E U R O   W E B   —   S E T U P                  ║${RESET}"
  echo -e "${CYAN}${BOLD}║       Brain Response Analysis Platform                       ║${RESET}"
  echo -e "${CYAN}${BOLD}║                                                              ║${RESET}"
  echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
  echo ""
}

section() {
  echo ""
  echo -e "${BLUE}${BOLD}━━━ $1 ━━━${RESET}"
  echo ""
}

step() {
  echo -e "  ${CYAN}▸${RESET} $1"
}

pass() {
  echo -e "  ${GREEN}✓${RESET} $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

warn() {
  echo -e "  ${YELLOW}⚠${RESET} $1"
  WARN_COUNT=$((WARN_COUNT + 1))
}

fail() {
  echo -e "  ${RED}✗${RESET} $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

info() {
  echo -e "  ${DIM}$1${RESET}"
}

ask_yn() {
  local prompt="$1"
  local default="${2:-y}"
  local hint="[Y/n]"
  [[ "$default" == "n" ]] && hint="[y/N]"

  echo ""
  echo -ne "  ${MAGENTA}?${RESET} ${BOLD}$prompt${RESET} $hint "
  read -r answer
  answer="${answer:-$default}"
  [[ "$answer" =~ ^[Yy] ]]
}

ask_input() {
  local prompt="$1"
  local default="${2:-}"
  local hint=""
  [[ -n "$default" ]] && hint=" ${DIM}(default: $default)${RESET}"

  echo -ne "  ${MAGENTA}?${RESET} ${BOLD}$prompt${RESET}$hint: "
  read -r answer
  echo "${answer:-$default}"
}

spinner() {
  local pid=$1
  local msg="$2"
  local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
  local i=0

  while kill -0 "$pid" 2>/dev/null; do
    echo -ne "\r  ${CYAN}${frames[$i]}${RESET} $msg"
    i=$(( (i + 1) % ${#frames[@]} ))
    sleep 0.1
  done

  wait "$pid" 2>/dev/null
  local exit_code=$?
  echo -ne "\r"

  if [[ $exit_code -eq 0 ]]; then
    pass "$msg"
  else
    fail "$msg ${RED}(exit code $exit_code)${RESET}"
  fi
  return $exit_code
}

run_with_spinner() {
  local msg="$1"
  shift
  local log_file
  log_file=$(mktemp)

  "$@" > "$log_file" 2>&1 &
  local pid=$!

  if spinner "$pid" "$msg"; then
    rm -f "$log_file"
    return 0
  else
    echo ""
    echo -e "  ${DIM}── Last 20 lines of output ──${RESET}"
    tail -20 "$log_file" | while IFS= read -r line; do
      echo -e "  ${DIM}│ $line${RESET}"
    done
    echo -e "  ${DIM}── Full log: $log_file ──${RESET}"
    echo ""
    return 1
  fi
}

# ── Detect environment ───────────────────────────────────────────────────────

detect_os() {
  local os
  os="$(uname -s)"
  case "$os" in
    Linux*)  echo "linux" ;;
    Darwin*) echo "macos" ;;
    *)       echo "unknown" ;;
  esac
}

detect_arch() {
  local arch
  arch="$(uname -m)"
  case "$arch" in
    x86_64)  echo "x86_64" ;;
    aarch64) echo "arm64" ;;
    arm64)   echo "arm64" ;;
    *)       echo "$arch" ;;
  esac
}

detect_cuda() {
  if command -v nvidia-smi &>/dev/null; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>/dev/null && return 0
  fi
  return 1
}

# ── Phase 0: System check ───────────────────────────────────────────────────

check_system() {
  section "1/7  System Check"

  local os
  os=$(detect_os)
  local arch
  arch=$(detect_arch)

  pass "Operating system: ${BOLD}$os ($arch)${RESET}"

  # Python
  if command -v python3 &>/dev/null; then
    local pyver
    pyver=$(python3 --version 2>&1 | awk '{print $2}')
    local pymajor
    pymajor=$(echo "$pyver" | cut -d. -f1)
    local pyminor
    pyminor=$(echo "$pyver" | cut -d. -f2)
    if [[ "$pymajor" -ge 3 && "$pyminor" -ge 11 ]]; then
      pass "Python $pyver (≥3.11 required)"
    else
      fail "Python $pyver found — TRIBE v2 requires Python ≥3.11"
      info "Install: https://www.python.org/downloads/"
    fi
  else
    fail "Python 3 not found"
    info "Install: https://www.python.org/downloads/"
  fi

  # Node
  if command -v node &>/dev/null; then
    local nodever
    nodever=$(node --version 2>&1)
    pass "Node.js $nodever"
  else
    fail "Node.js not found"
    info "Install: https://nodejs.org/ or use nvm"
  fi

  # npm
  if command -v npm &>/dev/null; then
    pass "npm $(npm --version 2>&1)"
  else
    fail "npm not found"
  fi

  # Git
  if command -v git &>/dev/null; then
    pass "Git $(git --version | awk '{print $3}')"
  else
    fail "Git not found"
  fi

  # GPU / CUDA
  echo ""
  step "Checking GPU..."
  local gpu_info
  if gpu_info=$(detect_cuda 2>/dev/null); then
    while IFS= read -r line; do
      local gpu_name
      gpu_name=$(echo "$line" | cut -d, -f1 | xargs)
      local vram_mb
      vram_mb=$(echo "$line" | cut -d, -f2 | xargs)
      local vram_gb
      vram_gb=$(echo "scale=1; $vram_mb / 1024" | bc 2>/dev/null || echo "?")

      if [[ "$vram_mb" -ge 24000 ]]; then
        pass "GPU: ${BOLD}$gpu_name${RESET} — ${GREEN}${vram_gb} GB VRAM${RESET} (excellent)"
      elif [[ "$vram_mb" -ge 16000 ]]; then
        pass "GPU: ${BOLD}$gpu_name${RESET} — ${vram_gb} GB VRAM (good)"
      elif [[ "$vram_mb" -ge 12000 ]]; then
        warn "GPU: ${BOLD}$gpu_name${RESET} — ${vram_gb} GB VRAM (tight — 16GB+ recommended)"
      else
        warn "GPU: ${BOLD}$gpu_name${RESET} — ${vram_gb} GB VRAM (may be insufficient)"
      fi
    done <<< "$gpu_info"
    HAS_CUDA=true
  else
    HAS_CUDA=false
    if [[ "$os" == "macos" ]]; then
      warn "No NVIDIA GPU (Apple Silicon detected)"
      info "TRIBE v2 requires NVIDIA CUDA. You can set up everything else now"
      info "and run inference later on a machine with an NVIDIA GPU."
    else
      warn "No NVIDIA GPU or drivers detected"
      info "TRIBE v2 requires an NVIDIA GPU with 16GB+ VRAM."
      info "Install drivers: https://www.nvidia.com/drivers"
    fi
  fi
}

# ── Phase 1: Data directories ───────────────────────────────────────────────

setup_directories() {
  section "2/7  Data Directories"

  local dirs=("captures" "predictions" "reports" "cache")
  for d in "${dirs[@]}"; do
    mkdir -p "$DATA_DIR/$d"
  done
  pass "Created data/{$(IFS=,; echo "${dirs[*]}")}"
}

# ── Phase 2: Environment file ───────────────────────────────────────────────

setup_env() {
  section "3/7  Environment Configuration"

  if [[ -f "$ENV_FILE" ]]; then
    pass ".env file already exists"
    info "Location: $ENV_FILE"

    if ask_yn "Reconfigure .env?" "n"; then
      write_env
    else
      info "Keeping existing .env"
    fi
  else
    step "Creating .env from template..."
    write_env
  fi
}

write_env() {
  cp "$ENV_EXAMPLE" "$ENV_FILE"

  echo ""
  echo -e "  ${BOLD}HuggingFace Token${RESET} ${DIM}(required for TRIBE v2 model access)${RESET}"
  echo -e "  ${DIM}Get one at: https://huggingface.co/settings/tokens${RESET}"
  echo -e "  ${DIM}You also need to accept the Llama 3.2 license at:${RESET}"
  echo -e "  ${DIM}https://huggingface.co/meta-llama/Llama-3.2-3B${RESET}"
  echo ""
  local hf_token
  hf_token=$(ask_input "HF_TOKEN (paste token, or press Enter to skip)")

  if [[ -n "$hf_token" ]]; then
    sed -i.bak "s/^HF_TOKEN=.*/HF_TOKEN=$hf_token/" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
    pass "HF_TOKEN set"
  else
    warn "HF_TOKEN skipped — you'll need to set it before running inference"
  fi

  echo ""
  echo -e "  ${BOLD}LLM API Key${RESET} ${DIM}(optional — enables AI chatbot + enhanced reports)${RESET}"
  echo -e "  ${DIM}Supports OpenAI or Anthropic API keys${RESET}"
  echo ""

  if ask_yn "Add an LLM API key?" "n"; then
    local provider
    provider=$(ask_input "Provider (openai / anthropic)" "openai")
    local llm_key
    llm_key=$(ask_input "API key")
    if [[ -n "$llm_key" ]]; then
      sed -i.bak "s/^LLM_API_KEY=.*/LLM_API_KEY=$llm_key/" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
      sed -i.bak "s/^LLM_PROVIDER=.*/LLM_PROVIDER=$provider/" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
      pass "LLM configured: $provider"
    fi
  else
    info "Skipped — chatbot will be hidden, core analysis still works"
  fi

  pass ".env written to $ENV_FILE"
}

# ── Phase 3: Python backend ─────────────────────────────────────────────────

setup_backend() {
  section "4/7  Python Backend"

  # Virtual environment
  if [[ -d "$VENV_DIR" ]]; then
    pass "Virtual environment exists"
  else
    step "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    pass "Virtual environment created at backend/.venv"
  fi

  local pip="$VENV_DIR/bin/pip"
  local python="$VENV_DIR/bin/python"

  # Upgrade pip
  run_with_spinner "Upgrading pip" "$pip" install --upgrade pip || true

  # Core dependencies (always install — no GPU needed)
  step "Installing core Python dependencies..."
  local core_deps=(
    "fastapi"
    "uvicorn[standard]"
    "aiosqlite"
    "python-dotenv"
    "playwright"
    "pydantic"
    "sse-starlette"
  )
  run_with_spinner "Installing FastAPI stack" "$pip" install "${core_deps[@]}" || {
    fail "Core dependency installation failed"
    return 1
  }

  # Engine dependencies (numpy/scipy/nibabel etc — no GPU needed)
  step "Installing engine dependencies (numpy, scipy, nibabel, etc.)..."
  local engine_deps=(
    "numpy>=1.26.0"
    "pandas>=2.1.0"
    "nibabel>=5.2.0"
    "nilearn>=0.10.0"
    "scipy>=1.12.0"
    "trimesh>=4.0.0"
    "matplotlib>=3.8.0"
    "Pillow>=10.0.0"
    "huggingface_hub>=0.27.0"
  )
  run_with_spinner "Installing engine stack" "$pip" install "${engine_deps[@]}" || {
    fail "Engine dependency installation failed"
    return 1
  }

  # PyTorch — platform-specific
  echo ""
  step "Installing PyTorch..."
  local os
  os=$(detect_os)

  if [[ "$HAS_CUDA" == "true" ]]; then
    echo ""
    echo -e "  ${BOLD}NVIDIA GPU detected — installing CUDA-enabled PyTorch${RESET}"
    echo ""
    echo -e "  ${DIM}Choose CUDA version (must match your driver):${RESET}"
    echo -e "  ${DIM}  Run 'nvidia-smi' to see your driver's CUDA version${RESET}"
    echo ""
    local cuda_ver
    cuda_ver=$(ask_input "CUDA version (12.4 / 12.1 / 11.8)" "12.4")

    local torch_index=""
    case "$cuda_ver" in
      12.4*) torch_index="https://download.pytorch.org/whl/cu124" ;;
      12.1*) torch_index="https://download.pytorch.org/whl/cu121" ;;
      11.8*) torch_index="https://download.pytorch.org/whl/cu118" ;;
      *)
        warn "Unknown CUDA version '$cuda_ver' — installing default PyTorch"
        torch_index=""
        ;;
    esac

    if [[ -n "$torch_index" ]]; then
      run_with_spinner "Installing PyTorch (CUDA $cuda_ver)" \
        "$pip" install "torch>=2.5.0" --index-url "$torch_index" || {
          warn "CUDA PyTorch install failed — falling back to default"
          run_with_spinner "Installing PyTorch (default)" "$pip" install "torch>=2.5.0" || true
        }
    else
      run_with_spinner "Installing PyTorch" "$pip" install "torch>=2.5.0" || true
    fi
  else
    if [[ "$os" == "macos" ]]; then
      info "Apple Silicon — installing CPU PyTorch (MPS backend)"
      info "GPU inference will only work on a machine with NVIDIA CUDA"
    else
      info "No NVIDIA GPU — installing CPU-only PyTorch"
    fi
    run_with_spinner "Installing PyTorch (CPU)" "$pip" install "torch>=2.5.0" || {
      warn "PyTorch installation failed — you can install it manually later"
    }
  fi

  # Playwright browsers
  echo ""
  if ask_yn "Install Playwright Chromium browser? (needed for web capture)" "y"; then
    run_with_spinner "Installing Playwright Chromium" "$python" -m playwright install chromium || {
      warn "Playwright browser install failed — run manually: playwright install chromium"
    }
  fi
}

# ── Phase 4: TRIBE v2 ───────────────────────────────────────────────────────

setup_tribe() {
  section "5/7  TRIBE v2 Model"

  local tribe_dir="$ROOT_DIR/tribev2"

  if "$VENV_DIR/bin/python" -c "from tribev2 import TribeModel" 2>/dev/null; then
    pass "TRIBE v2 is already installed"
    return 0
  fi

  echo -e "  ${BOLD}TRIBE v2${RESET} is Meta's brain encoding foundation model."
  echo -e "  ${DIM}Repository: https://github.com/facebookresearch/tribev2${RESET}"
  echo -e "  ${DIM}License: CC BY-NC 4.0 (non-commercial use)${RESET}"
  echo ""

  if [[ "$HAS_CUDA" != "true" ]]; then
    warn "No NVIDIA GPU detected — TRIBE v2 requires CUDA for inference"
    echo ""
    if ask_yn "Install TRIBE v2 anyway? (for later use on a GPU machine)" "y"; then
      : # continue
    else
      info "Skipped — install later with:"
      info "  git clone https://github.com/facebookresearch/tribev2.git"
      info "  cd tribev2 && pip install -e ."
      return 0
    fi
  fi

  if ask_yn "Clone and install TRIBE v2?" "y"; then
    if [[ -d "$tribe_dir" ]]; then
      pass "tribev2/ directory already exists"
    else
      run_with_spinner "Cloning TRIBE v2 repository" \
        git clone https://github.com/facebookresearch/tribev2.git "$tribe_dir" || {
          fail "Failed to clone TRIBE v2"
          info "Check your internet connection and try:"
          info "  git clone https://github.com/facebookresearch/tribev2.git"
          return 1
        }
    fi

    run_with_spinner "Installing TRIBE v2 package" \
      "$VENV_DIR/bin/pip" install -e "$tribe_dir" || {
        warn "TRIBE v2 installation had issues — check dependencies"
        info "Try manually: cd tribev2 && pip install -e ."
      }
  else
    info "Skipped — install later with:"
    info "  git clone https://github.com/facebookresearch/tribev2.git"
    info "  cd tribev2 && ../backend/.venv/bin/pip install -e ."
  fi
}

# ── Phase 5: Frontend ────────────────────────────────────────────────────────

setup_frontend() {
  section "6/7  Frontend (Next.js)"

  if [[ -d "$FRONTEND_DIR/node_modules" ]]; then
    pass "node_modules exists"
    if ask_yn "Re-run npm install?" "n"; then
      run_with_spinner "Installing npm packages" npm install --prefix "$FRONTEND_DIR" || {
        fail "npm install failed"
        return 1
      }
    fi
  else
    run_with_spinner "Installing npm packages" npm install --prefix "$FRONTEND_DIR" || {
      fail "npm install failed"
      return 1
    }
  fi
}

# ── Phase 6: Validation ─────────────────────────────────────────────────────

validate_setup() {
  section "7/7  Validation"

  local python="$VENV_DIR/bin/python"

  # Check Python imports
  step "Verifying Python dependencies..."

  if "$python" -c "import fastapi, aiosqlite, pydantic" 2>/dev/null; then
    pass "FastAPI stack"
  else
    fail "FastAPI stack — missing imports"
  fi

  if "$python" -c "import numpy, scipy, pandas" 2>/dev/null; then
    pass "Scientific stack (numpy, scipy, pandas)"
  else
    fail "Scientific stack — run: pip install numpy scipy pandas"
  fi

  if "$python" -c "import nibabel, nilearn" 2>/dev/null; then
    pass "Neuroimaging (nibabel, nilearn)"
  else
    fail "Neuroimaging — run: pip install nibabel nilearn"
  fi

  if "$python" -c "import trimesh" 2>/dev/null; then
    pass "Mesh export (trimesh)"
  else
    fail "Mesh export — run: pip install trimesh"
  fi

  if "$python" -c "import matplotlib, PIL" 2>/dev/null; then
    pass "Visualization (matplotlib, Pillow)"
  else
    fail "Visualization — run: pip install matplotlib Pillow"
  fi

  if "$python" -c "import torch; print(f'PyTorch {torch.__version__}')" 2>/dev/null; then
    local torch_info
    torch_info=$("$python" -c "
import torch
cuda = torch.cuda.is_available()
ver = torch.__version__
if cuda:
    print(f'PyTorch {ver} with CUDA {torch.version.cuda}')
else:
    print(f'PyTorch {ver} (CPU only)')
" 2>/dev/null)
    pass "$torch_info"
  else
    warn "PyTorch not installed"
  fi

  if "$python" -c "from tribev2 import TribeModel" 2>/dev/null; then
    pass "TRIBE v2 model library"
  else
    warn "TRIBE v2 not installed (needed for brain inference)"
  fi

  # Check Playwright
  if "$python" -c "from playwright.sync_api import sync_playwright" 2>/dev/null; then
    pass "Playwright library"
  else
    fail "Playwright — run: pip install playwright && playwright install chromium"
  fi

  # Check .env
  echo ""
  step "Checking configuration..."

  if [[ -f "$ENV_FILE" ]]; then
    pass ".env file exists"

    if grep -q "^HF_TOKEN=.\+" "$ENV_FILE" 2>/dev/null; then
      pass "HF_TOKEN is set"
    else
      warn "HF_TOKEN is empty — needed for TRIBE v2 model download"
    fi

    if grep -q "^LLM_API_KEY=.\+" "$ENV_FILE" 2>/dev/null; then
      local provider
      provider=$(grep "^LLM_PROVIDER=" "$ENV_FILE" | cut -d= -f2)
      pass "LLM configured ($provider) — chatbot will be available"
    else
      info "LLM not configured — chatbot disabled (optional)"
    fi
  else
    fail ".env file missing — run this setup again or copy .env.example to .env"
  fi

  # Check frontend
  echo ""
  step "Checking frontend..."

  if [[ -d "$FRONTEND_DIR/node_modules" ]]; then
    pass "Frontend dependencies installed"
  else
    fail "Frontend dependencies missing — run: cd frontend && npm install"
  fi

  # Check data dirs
  local missing_dirs=()
  for d in captures predictions reports cache; do
    [[ -d "$DATA_DIR/$d" ]] || missing_dirs+=("$d")
  done
  if [[ ${#missing_dirs[@]} -eq 0 ]]; then
    pass "Data directories ready"
  else
    fail "Missing data directories: ${missing_dirs[*]}"
  fi
}

# ── Summary ──────────────────────────────────────────────────────────────────

print_summary() {
  echo ""
  echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${CYAN}${BOLD}║                      Setup Summary                          ║${RESET}"
  echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
  echo ""

  echo -e "  ${GREEN}✓ $PASS_COUNT passed${RESET}    ${YELLOW}⚠ $WARN_COUNT warnings${RESET}    ${RED}✗ $FAIL_COUNT failed${RESET}"
  echo ""

  if [[ $FAIL_COUNT -gt 0 ]]; then
    echo -e "  ${RED}${BOLD}Some components need attention.${RESET}"
    echo -e "  ${DIM}Re-run this script after fixing the issues above.${RESET}"
    echo ""
  fi

  echo -e "  ${BOLD}Quick Reference${RESET}"
  echo ""
  echo -e "  ${DIM}Start the app:${RESET}        ${BOLD}make run${RESET}"
  echo -e "  ${DIM}Start backend only:${RESET}   ${BOLD}make run-backend${RESET}"
  echo -e "  ${DIM}Start frontend only:${RESET}  ${BOLD}make run-frontend${RESET}"
  echo -e "  ${DIM}Check GPU:${RESET}            ${BOLD}make check-gpu${RESET}"
  echo -e "  ${DIM}Clean data:${RESET}           ${BOLD}make clean${RESET}"
  echo ""
  echo -e "  ${DIM}Frontend:${RESET}  ${CYAN}http://localhost:3000${RESET}"
  echo -e "  ${DIM}Backend:${RESET}   ${CYAN}http://localhost:8000${RESET}"
  echo -e "  ${DIM}Health:${RESET}    ${CYAN}http://localhost:8000/health${RESET}"
  echo ""

  if [[ "$HAS_CUDA" != "true" ]]; then
    echo -e "  ${YELLOW}${BOLD}Note: No NVIDIA GPU detected${RESET}"
    echo -e "  ${DIM}The frontend and capture pipeline will work, but brain${RESET}"
    echo -e "  ${DIM}analysis requires an NVIDIA GPU with 16GB+ VRAM.${RESET}"
    echo -e "  ${DIM}Transfer this project to a GPU machine and re-run setup.${RESET}"
    echo ""
  fi

  if ! grep -q "^HF_TOKEN=.\+" "$ENV_FILE" 2>/dev/null; then
    echo -e "  ${YELLOW}${BOLD}Before first run:${RESET}"
    echo -e "  ${DIM}1. Get a HuggingFace token: https://huggingface.co/settings/tokens${RESET}"
    echo -e "  ${DIM}2. Accept Llama 3.2 license: https://huggingface.co/meta-llama/Llama-3.2-3B${RESET}"
    echo -e "  ${DIM}3. Set in .env:  HF_TOKEN=hf_your_token_here${RESET}"
    echo ""
  fi

  echo -e "  ${DIM}─────────────────────────────────────────────${RESET}"
  echo -e "  ${DIM}Neuro Web — Brain Response Analysis Platform${RESET}"
  echo -e "  ${DIM}Powered by Meta TRIBE v2 · Local GPU Inference${RESET}"
  echo ""
}

# ── Main ─────────────────────────────────────────────────────────────────────

main() {
  cd "$ROOT_DIR"

  HAS_CUDA=false

  banner

  echo -e "  ${DIM}This script will guide you through setting up Neuro Web.${RESET}"
  echo -e "  ${DIM}It checks prerequisites, installs dependencies, and${RESET}"
  echo -e "  ${DIM}configures the environment for your machine.${RESET}"
  echo ""
  echo -e "  ${DIM}Project root: $ROOT_DIR${RESET}"

  if ! ask_yn "Ready to begin?" "y"; then
    echo ""
    echo -e "  ${DIM}Setup cancelled.${RESET}"
    exit 0
  fi

  check_system
  setup_directories
  setup_env
  setup_backend
  setup_tribe
  setup_frontend
  validate_setup
  print_summary
}

main "$@"
