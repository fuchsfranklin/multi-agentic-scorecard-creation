#!/usr/bin/env python3
"""
Pre-flight validation for running the scorecard project on a new machine.

Checks:
  1. Python version (3.10+)
  2. All pip dependencies installed
  3. .env file exists with required keys
  4. OpenRouter API key is valid (quick auth check, no cost)
  5. External APIs reachable (ClinicalTrials.gov, PubMed)
  6. sentence-transformers model downloadable
  7. LanceDB functional
  8. Tantivy installed (for hybrid search)
  9. Output directories writable

Run this FIRST on any new machine before running the actual scripts.

Usage:
    python setup_and_validate.py
"""
import sys
import os
import importlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REQUIRED_PYTHON = (3, 10)

checks_passed = 0
checks_failed = 0
warnings = []


def ok(msg):
    global checks_passed
    checks_passed += 1
    print(f"  ✓ {msg}")


def fail(msg):
    global checks_failed
    checks_failed += 1
    print(f"  ✗ {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"  ⚠ {msg}")


print("=" * 60)
print("  Scorecard Project — Setup Validation")
print("=" * 60)

# ---------------------------------------------------------------
# 1. Python version
# ---------------------------------------------------------------
print("\n[1/8] Python version...")
v = sys.version_info
if (v.major, v.minor) >= REQUIRED_PYTHON:
    ok(f"Python {v.major}.{v.minor}.{v.micro}")
else:
    fail(f"Python {v.major}.{v.minor}.{v.micro} — need {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+")

# ---------------------------------------------------------------
# 2. Pip dependencies
# ---------------------------------------------------------------
print("\n[2/8] Python dependencies...")
REQUIRED_PACKAGES = {
    "requests": "requests",
    "sentence_transformers": "sentence-transformers",
    "lancedb": "lancedb",
    "pyarrow": "pyarrow",
    "openai": "openai",
    "dotenv": "python-dotenv",
    "bs4": "beautifulsoup4",
    "Bio": "BioPython",
    "openpyxl": "openpyxl",
    "sklearn": "scikit-learn",
    "matplotlib": "matplotlib",
    "deepeval": "deepeval",
}

missing = []
for import_name, pip_name in REQUIRED_PACKAGES.items():
    try:
        importlib.import_module(import_name)
    except ImportError:
        missing.append(pip_name)

if missing:
    fail(f"Missing packages: {', '.join(missing)}")
    print(f"       Fix: pip install {' '.join(missing)}")
else:
    ok(f"All {len(REQUIRED_PACKAGES)} packages installed")

# ---------------------------------------------------------------
# 3. .env file
# ---------------------------------------------------------------
print("\n[3/8] Environment configuration...")
env_path = PROJECT_ROOT / ".env"

if env_path.exists():
    ok(".env file exists")
    env_content = env_path.read_text()
    if "OPENROUTER_API_KEY" in env_content and "your_openrouter_api_key_here" not in env_content:
        ok("OPENROUTER_API_KEY is set")
    else:
        fail("OPENROUTER_API_KEY not set in .env (copy from .env.example and fill in)")
    if "ENTREZ_EMAIL" in env_content and "your_email@example.com" not in env_content:
        ok("ENTREZ_EMAIL is set")
    else:
        warn("ENTREZ_EMAIL not customized — PubMed may rate-limit you")
else:
    fail(".env file missing — copy from .env.example:")
    print("       copy .env.example .env")

# ---------------------------------------------------------------
# 4. OpenRouter API key validation
# ---------------------------------------------------------------
print("\n[4/8] OpenRouter API connectivity...")
try:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    import config as cfg
    if cfg.OPENROUTER_API_KEY and cfg.OPENROUTER_API_KEY != "your_openrouter_api_key_here":
        import requests
        resp = requests.get(
            f"{cfg.OPENROUTER_API_HOST}/models",
            headers={"Authorization": f"Bearer {cfg.OPENROUTER_API_KEY}"},
            timeout=10,
        )
        if resp.status_code == 200:
            ok("OpenRouter API key valid — models endpoint reachable")
        elif resp.status_code == 401:
            fail("OpenRouter API key invalid (401 Unauthorized)")
        else:
            warn(f"OpenRouter returned status {resp.status_code} — may still work")
    else:
        fail("No OpenRouter API key configured")
except Exception as e:
    fail(f"OpenRouter check failed: {e}")

# ---------------------------------------------------------------
# 5. External APIs
# ---------------------------------------------------------------
print("\n[5/8] External API connectivity...")
try:
    import requests
    resp = requests.get(
        "https://clinicaltrials.gov/api/v2/studies",
        params={"query.titles": "enzalutamide", "pageSize": 1},
        timeout=15,
    )
    resp.raise_for_status()
    ok("ClinicalTrials.gov v2 API reachable")
except Exception as e:
    fail(f"ClinicalTrials.gov v2: {e}")

try:
    from Bio import Entrez
    Entrez.email = getattr(cfg, "ENTREZ_EMAIL", "test@example.com")
    handle = Entrez.esearch(db="pubmed", term="cancer", retmax="1")
    record = Entrez.read(handle)
    handle.close()
    if record.get("IdList"):
        ok("PubMed/NCBI Entrez API reachable")
    else:
        warn("PubMed returned no results (may be a transient issue)")
except Exception as e:
    fail(f"PubMed/Entrez: {e}")

# ---------------------------------------------------------------
# 6. Embedding model
# ---------------------------------------------------------------
print("\n[6/8] Embedding model...")
try:
    from sentence_transformers import SentenceTransformer
    model_name = getattr(cfg, "EMBEDDING_MODEL_FOR_RAG", "all-mpnet-base-v2")
    model = SentenceTransformer(model_name)
    vec = model.encode("test", convert_to_tensor=False)
    expected_dim = getattr(cfg, "EMBEDDING_DIMENSION", 768)
    if len(vec) == expected_dim:
        ok(f"{model_name} loaded — dimension {len(vec)} matches config")
    else:
        fail(f"Dimension mismatch: got {len(vec)}, config says {expected_dim}")
except Exception as e:
    err = str(e)
    if "SSL" in err or "CERTIFICATE" in err:
        warn("SSL/corporate proxy blocking model download — will need VPN or manual download")
    else:
        fail(f"Embedding model: {e}")

# ---------------------------------------------------------------
# 7. LanceDB
# ---------------------------------------------------------------
print("\n[7/9] LanceDB...")
try:
    import lancedb
    import pyarrow as pa
    import tempfile
    import shutil
    tmp = os.path.join(tempfile.gettempdir(), "lancedb_validate")
    db = lancedb.connect(tmp)
    schema = pa.schema([
        pa.field("id", pa.string()),
        pa.field("text", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), 4)),
    ])
    t = db.create_table("test", schema=schema, mode="overwrite")
    t.add([{"id": "1", "text": "test", "vector": [0.1, 0.2, 0.3, 0.4]}])
    assert len(t.to_pandas()) == 1
    shutil.rmtree(tmp, ignore_errors=True)
    ok("LanceDB create/insert/query works")
except Exception as e:
    fail(f"LanceDB: {e}")

# ---------------------------------------------------------------
# 8. Tantivy (for hybrid search in RAG pipeline)
# ---------------------------------------------------------------
print("\n[8/9] Tantivy (hybrid search)...")
try:
    import tantivy  # noqa: F401
    ok("tantivy installed — LanceDB hybrid search (vector + BM25) will work")
except ImportError:
    warn("tantivy not installed — RAG pipeline will fall back to vector-only search")
    print("       Fix: pip install tantivy")

# ---------------------------------------------------------------
# 9. Output directories
# ---------------------------------------------------------------
print("\n[9/9] Output directories...")
dirs_to_check = [
    PROJECT_ROOT / "results" / "single_llm",
    PROJECT_ROOT / "results" / "multi_agentic",
    PROJECT_ROOT / "results" / "rag_llm",
    PROJECT_ROOT / "results" / "deep_outputs",
    PROJECT_ROOT / "logs",
]
all_dirs_ok = True
for d in dirs_to_check:
    d.mkdir(parents=True, exist_ok=True)
    if d.exists() and os.access(d, os.W_OK):
        pass
    else:
        fail(f"Cannot write to {d}")
        all_dirs_ok = False
if all_dirs_ok:
    ok(f"All {len(dirs_to_check)} output directories writable")

# ---------------------------------------------------------------
# Summary
# ---------------------------------------------------------------
print("\n" + "=" * 60)
print(f"  PASSED: {checks_passed}  |  FAILED: {checks_failed}  |  WARNINGS: {len(warnings)}")
if checks_failed == 0:
    print("  ✓ Ready to run! Use: python run_all.py")
else:
    print("  ✗ Fix the failures above before running.")
if warnings:
    print("\n  Warnings:")
    for w in warnings:
        print(f"    ⚠ {w}")
print("=" * 60)
sys.exit(1 if checks_failed > 0 else 0)
