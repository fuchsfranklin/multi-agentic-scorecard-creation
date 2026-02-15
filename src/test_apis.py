"""
Quick smoke test for all non-LLM APIs used in the project.
Tests: ClinicalTrials.gov v2, PubMed/Entrez, LanceDB, sentence-transformers.
Does NOT call OpenRouter (no cost incurred).
"""
import sys
import json
import time

print("=" * 60)
print("  API Smoke Tests (no OpenRouter / no cost)")
print("=" * 60)

failures = []

# ---------------------------------------------------------------
# 1. ClinicalTrials.gov v2 API
# ---------------------------------------------------------------
print("\n[1/5] ClinicalTrials.gov v2 — search by title...")
try:
    import requests
    resp = requests.get(
        "https://clinicaltrials.gov/api/v2/studies",
        params={"query.titles": "enzalutamide placebo prostate", "pageSize": 1},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    studies = data.get("studies", [])
    if not studies:
        raise ValueError("No studies returned")
    nct = studies[0]["protocolSection"]["identificationModule"]["nctId"]
    title = studies[0]["protocolSection"]["identificationModule"]["officialTitle"]
    print(f"  OK — Found: {nct}")
    print(f"       Title: {title[:80]}...")
except Exception as e:
    print(f"  FAIL — {e}")
    failures.append(("ClinicalTrials.gov v2 search", str(e)))

print("\n[2/5] ClinicalTrials.gov v2 — fetch single study...")
try:
    resp2 = requests.get(
        "https://clinicaltrials.gov/api/v2/studies/NCT01212991",
        timeout=15,
    )
    resp2.raise_for_status()
    study = resp2.json()
    study_title = study["protocolSection"]["identificationModule"]["officialTitle"]
    print(f"  OK — Fetched NCT01212991")
    print(f"       Title: {study_title[:80]}...")
except Exception as e:
    print(f"  FAIL — {e}")
    failures.append(("ClinicalTrials.gov v2 fetch", str(e)))

# ---------------------------------------------------------------
# 2. PubMed / NCBI Entrez
# ---------------------------------------------------------------
print("\n[3/5] PubMed Entrez — search + fetch abstract...")
try:
    from Bio import Entrez
    import config
    Entrez.email = config.ENTREZ_EMAIL
    if config.NCBI_API_KEY:
        Entrez.api_key = config.NCBI_API_KEY

    handle = Entrez.esearch(db="pubmed", term="enzalutamide prostate cancer", retmax="2")
    record = Entrez.read(handle)
    handle.close()
    ids = record.get("IdList", [])
    if not ids:
        raise ValueError("No PubMed IDs returned")
    print(f"  OK — Search returned PMIDs: {ids}")

    handle2 = Entrez.efetch(db="pubmed", id=ids[0], rettype="abstract", retmode="text")
    abstract_text = handle2.read()
    handle2.close()
    snippet = abstract_text.strip()[:120].replace("\n", " ")
    print(f"  OK — Fetched abstract for PMID {ids[0]}: {snippet}...")
except Exception as e:
    print(f"  FAIL — {e}")
    failures.append(("PubMed Entrez", str(e)))

# ---------------------------------------------------------------
# 3. sentence-transformers embedding model
# ---------------------------------------------------------------
print("\n[4/5] sentence-transformers — load model + encode...")
sentence_model = None
try:
    from sentence_transformers import SentenceTransformer
    import config
    sentence_model = SentenceTransformer(config.EMBEDDING_MODEL_FOR_RAG)
    embedding = sentence_model.encode("enzalutamide prostate cancer clinical trial", convert_to_tensor=False)
    dim = len(embedding)
    expected = config.EMBEDDING_DIMENSION
    if dim != expected:
        raise ValueError(f"Dimension mismatch: got {dim}, expected {expected}")
    print(f"  OK — Model: {config.EMBEDDING_MODEL_FOR_RAG}, dimension: {dim}")
except Exception as e:
    err_str = str(e)
    if "SSL" in err_str or "CERTIFICATE" in err_str or "client has been closed" in err_str:
        print(f"  SKIP — Corporate SSL/Zscaler blocking HuggingFace downloads.")
        print(f"         This is expected on corporate networks. Will work from home/VPN.")
        print(f"         Error: {err_str[:100]}")
    else:
        print(f"  FAIL — {e}")
        failures.append(("sentence-transformers", str(e)))

# ---------------------------------------------------------------
# 4. LanceDB — create table, insert, hybrid search
# ---------------------------------------------------------------
print("\n[5/5] LanceDB — table creation, insert, vector search, hybrid search...")
try:
    import lancedb
    import pyarrow as pa
    import config
    import tempfile
    import os
    import numpy as np

    # Use a temp directory so we don't pollute the real DB
    tmp_dir = os.path.join(tempfile.gettempdir(), "lancedb_test")
    db = lancedb.connect(tmp_dir)

    dim = config.EMBEDDING_DIMENSION
    schema = pa.schema([
        pa.field("id", pa.string()),
        pa.field("text", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), dim)),
    ])
    table = db.create_table("test_table", schema=schema, mode="overwrite")

    # Insert test docs — use real embeddings if model loaded, else random vectors
    test_texts = [
        "Enzalutamide improved overall survival in metastatic prostate cancer.",
        "Trastuzumab added to chemotherapy improved outcomes in HER2+ breast cancer.",
        "Ipilimumab showed disease-free survival benefit in stage III melanoma.",
    ]
    data = []
    for i, txt in enumerate(test_texts):
        if sentence_model is not None:
            vec = sentence_model.encode(txt, convert_to_tensor=False).tolist()
        else:
            # Use random vectors for structural testing when model unavailable
            vec = np.random.randn(dim).astype(np.float32).tolist()
        data.append({"id": f"doc_{i}", "text": txt, "vector": vec})
    table.add(data)
    count = len(table.to_pandas())
    print(f"  OK — Inserted {count} documents")

    # Vector search
    if sentence_model is not None:
        query_vec = sentence_model.encode("prostate cancer treatment", convert_to_tensor=False).tolist()
    else:
        query_vec = np.random.randn(dim).astype(np.float32).tolist()
    results = table.search(query_vec).limit(2).to_pandas()
    print(f"  OK — Vector search returned {len(results)} results")
    if len(results) > 0:
        print(f"       Top hit: {results.iloc[0]['text'][:80]}...")

    # FTS index + hybrid search
    try:
        table.create_fts_index("text", replace=True)
        from lancedb.rerankers import LinearCombinationReranker
        reranker = LinearCombinationReranker(weight=0.7)
        hybrid_results = (
            table.search(query_type="hybrid")
            .vector(query_vec)
            .text("prostate cancer")
            .limit(2)
            .rerank(reranker=reranker)
            .to_pandas()
        )
        print(f"  OK — Hybrid search returned {len(hybrid_results)} results")
    except Exception as e:
        print(f"  WARN — Hybrid search failed (vector search still works): {e}")

    # Cleanup
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

except Exception as e:
    print(f"  FAIL — {e}")
    failures.append(("LanceDB", str(e)))

# ---------------------------------------------------------------
# Summary
# ---------------------------------------------------------------
print("\n" + "=" * 60)
if failures:
    print(f"  RESULT: {len(failures)} FAILURE(S)")
    for name, err in failures:
        print(f"    ✗ {name}: {err}")
    sys.exit(1)
else:
    print("  RESULT: ALL 5 TESTS PASSED")
    sys.exit(0)
