#!/usr/bin/env python3
"""
Ingest ARGO NetCDF files -> create summary documents -> embed -> persist to a local Chroma vector store.

Usage:
    python ingest_vectorstore.py --root ./data/argo_nc --persist_dir ./vectorstore/chroma --collection floatchat_profiles

Notes:
- This script tries to be robust to variations in ARGO NetCDF naming.
- By default it uses sentence-transformers 'all-MiniLM-L6-v2' (local CPU).
- If Chroma is not desired, set --backend faiss to persist a FAISS index instead (FAISS currently will save to disk).
"""
import os
import glob
import argparse
from datetime import datetime
from typing import Optional, Dict, List

import xarray as xr
import numpy as np
import pandas as pd
from netCDF4 import num2date
from tqdm import tqdm

# LangChain imports
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma, FAISS
from langchain.schema import Document

# -------------------
# Utility helpers
# -------------------
def safe_get_attr(ds, keys, default=None):
    for k in keys:
        if k in ds.attrs:
            return ds.attrs[k]
    return default

def try_parse_juld(variable) -> Optional[str]:
    """
    Try to convert JULD (or similar) to ISO timestamp string.
    Handles both datetime64 and numeric with units (NetCDF style).
    """
    try:
        vals = variable.values
        if np.issubdtype(vals.dtype, np.datetime64):
            dt = pd.to_datetime(np.atleast_1d(vals)[0])
            return dt.isoformat()
        # numeric -> use netCDF4.num2date with units attribute
        units = variable.attrs.get("units", None)
        calendar = variable.attrs.get("calendar", "gregorian")
        if units is None:
            return None
        # convert first element
        first = np.atleast_1d(vals)[0]
        if np.ma.is_masked(first):
            return None
        dates = num2date(np.atleast_1d(vals), units=units, calendar=calendar)
        # num2date can return list of datetimes; take first
        if len(dates) > 0:
            return pd.to_datetime(dates[0]).isoformat()
        return None
    except Exception:
        return None

def qc_ok_fraction(var_values, qc_values) -> Optional[float]:
    """
    Compute fraction of values flagged as QC '1' or '2' (good/probably good).
    qc_values may be an array of bytes or strings.
    """
    if qc_values is None or var_values is None:
        return None
    try:
        arr = np.ravel(var_values)
        qc = np.ravel(qc_values)
        # convert bytes to str if necessary
        if qc.dtype.kind == "S" or qc.dtype.kind == "O":
            # decode bytes or objects to strings like '1','2', etc.
            qc_str = np.array([str(x).strip().strip("b'\"") for x in qc])
        else:
            qc_str = qc.astype(str)
        valid_mask = ~np.isnan(arr.astype(float))
        if valid_mask.sum() == 0:
            return 0.0
        ok_mask = np.isin(qc_str, ["1", "2"]) & valid_mask
        return float(ok_mask.sum()) / float(valid_mask.sum())
    except Exception:
        return None

def extract_basic_metadata(ds, file_path: str) -> Dict:
    """
    Extract canonical metadata from a NetCDF ARGO dataset.
    """
    meta = {"source_file": os.path.abspath(file_path)}
    # try platform/wmo id
    wmo = safe_get_attr(ds, ["platform_number", "PLATFORM_NUMBER", "WMO_NUMBER", "platform_nominal", "PLATFORM_NUMBER"])
    if wmo is None and "PLATFORM_NUMBER" in ds.variables:
        try:
            wmo = str(np.atleast_1d(ds["PLATFORM_NUMBER"].values)[0])
        except:
            wmo = None
    meta["wmo_id"] = str(wmo) if wmo is not None else None

    # cycle (try variables then attrs)
    cycle = None
    for k in ("CYCLE_NUMBER", "cycle_number", "CYCLE"):
        if k in ds.variables:
            try:
                cycle = int(np.atleast_1d(ds[k].values)[0])
                break
            except Exception:
                pass
    if cycle is None:
        cycle_attr = safe_get_attr(ds, ["cycle_number", "CYCLE_NUMBER"])
        try:
            cycle = int(cycle_attr) if cycle_attr is not None else None
        except:
            cycle = None
    meta["cycle"] = cycle

    # time
    time_iso = None
    for tname in ("JULD", "juld", "TIME", "time", "JULD_LOCATION"):
        if tname in ds.variables:
            parsed = try_parse_juld(ds[tname])
            if parsed:
                time_iso = parsed
                break
    if time_iso is None:
        # fallback to file mtime
        time_iso = datetime.utcfromtimestamp(os.path.getmtime(file_path)).isoformat() + "Z"
    meta["time_utc"] = time_iso

    # lat / lon
    lat = None; lon = None
    for k in ("LATITUDE", "latitude", "LAT", "lat"):
        if k in ds.variables:
            try:
                lat = float(np.atleast_1d(ds[k].values)[0])
                break
            except:
                pass
    for k in ("LONGITUDE","longitude","LON","lon"):
        if k in ds.variables:
            try:
                lon = float(np.atleast_1d(ds[k].values)[0])
                break
            except:
                pass
    meta["lat"] = lat
    meta["lon"] = lon

    # variables present
    vars_present = list(ds.data_vars.keys())
    meta["vars_present"] = vars_present

    # compute depth range and n_levels if a PRES-like var exists
    depth_min=None; depth_max=None; n_levels=None
    for pres_name in ("PRES","PRESURE","PRES_dbar","pressure","PRES_ADJUSTED"):
        if pres_name in ds.variables:
            try:
                pres = np.ravel(ds[pres_name].values.astype(float))
                pres = pres[~np.isnan(pres)]
                n_levels = int(pres.size)
                if pres.size>0:
                    depth_min = float(np.nanmin(pres)); depth_max = float(np.nanmax(pres))
                break
            except:
                pass
    meta["n_levels"] = n_levels
    meta["depth_min_dbar"] = depth_min
    meta["depth_max_dbar"] = depth_max

    # compute qc ratios for a handful of common vars if qc arrays exist
    qc_summary = {}
    keys_of_interest = ["TEMP", "PSAL", "DOXY", "NITRATE", "CHLA"]
    for v in keys_of_interest:
        if v in ds.variables:
            var = ds[v]
            qc_name = f"{v}_QC" if f"{v}_QC" in ds.variables else (f"{v}_QC" if f"{v}_QC" in ds.variables else None)
            qc_values = ds[qc_name].values if qc_name and qc_name in ds.variables else None
            frac = qc_ok_fraction(var.values, qc_values) if qc_values is not None else None
            qc_summary[v] = frac
        else:
            qc_summary[v] = None
    meta["qc_ok_ratio"] = qc_summary

    return meta

def make_summary_text(meta: Dict) -> str:
    """
    Create a concise human-readable summary for a profile.
    """
    parts = []
    parts.append(f"ARGO profile: file={os.path.basename(meta.get('source_file',''))}")
    if meta.get("wmo_id"):
        parts.append(f"WMO: {meta['wmo_id']}")
    if meta.get("cycle") is not None:
        parts.append(f"Cycle: {meta['cycle']}")
    if meta.get("lat") is not None and meta.get("lon") is not None:
        parts.append(f"Location: {meta['lat']:.4f} N, {meta['lon']:.4f} E")
    if meta.get("time_utc"):
        parts.append(f"Time (UTC): {meta['time_utc']}")
    if meta.get("n_levels"):
        parts.append(f"Levels: {meta['n_levels']}, depth range ≈ {meta.get('depth_min_dbar')}–{meta.get('depth_max_dbar')} dbar")
    if meta.get("vars_present"):
        top_vars = [v for v in ("TEMP","PSAL","PRES","DOXY","CHLA") if v in meta.get("vars_present",[])]
        if top_vars:
            parts.append("Measured: " + ", ".join(top_vars))
    # qc notes
    qc = meta.get("qc_ok_ratio", {})
    qc_notes = []
    for k, v in (qc.items() if isinstance(qc, dict) else []):
        if v is not None and v < 0.5:
            qc_notes.append(f"{k} low coverage ({v:.2f})")
    if qc_notes:
        parts.append("QC notes: " + "; ".join(qc_notes))
    return "\n".join(parts)

# -------------------
# Main ingestion function
# -------------------
def ingest_to_vectorstore(
    root_dir: str,
    glob_pattern: str = "**/*.nc",
    embedding_model: str = "all-MiniLM-L6-v2",
    backend: str = "chroma",
    persist_dir: str = "./vectorstore",
    collection_name: str = "floatchat_profiles",
    chunk_size:int = 700,
    chunk_overlap:int = 120,
    max_files: Optional[int] = None
):
    # discover files
    paths = sorted(glob.glob(os.path.join(root_dir, glob_pattern), recursive=True))
    if max_files:
        paths = paths[:max_files]
    print(f"[INFO] Found {len(paths)} files under {root_dir}")

    # parse files -> Documents
    docs: List[Document] = []
    for p in tqdm(paths, desc="parsing nc files"):
        try:
            # open dataset with decode_times True when possible
            try:
                ds = xr.open_dataset(p, decode_times=True)
            except Exception:
                ds = xr.open_dataset(p, decode_times=False)
        except Exception as e:
            print(f"[WARN] could not open {p}: {e}")
            continue

        meta = extract_basic_metadata(ds, p)
        summary = make_summary_text(meta)

        # optionally append a few numeric stats (means) to help embeddings
        numeric_stats = []
        for var in ("TEMP","PSAL","PRES"):
            if var in ds.variables:
                try:
                    arr = np.ravel(ds[var].values.astype(float))
                    arr = arr[~np.isnan(arr)]
                    if arr.size>0:
                        numeric_stats.append(f"{var}_mean={float(np.nanmean(arr)):.3f}")
                except:
                    pass
        if numeric_stats:
            summary += "\n" + " | ".join(numeric_stats)

        # create a Document for langchain
        # ensure metadata is JSON-serializable: convert numpy types to python
        meta_clean = {}
        for k,v in meta.items():
            if isinstance(v, (np.generic, np.ndarray)):
                try:
                    meta_clean[k] = v.tolist()
                except:
                    meta_clean[k] = str(v)
            else:
                meta_clean[k] = v
        doc = Document(page_content=summary, metadata=meta_clean)
        docs.append(doc)

        # close dataset
        try:
            ds.close()
        except:
            pass

    print(f"[INFO] Created {len(docs)} documents from NetCDF files. Chunking...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunked_docs = splitter.split_documents(docs)
    print(f"[INFO] After chunking: {len(chunked_docs)} chunks")

    # create embeddings
    print(f"[INFO] Creating embeddings using model: {embedding_model}")
    embeddings = SentenceTransformerEmbeddings(model_name=embedding_model)

    # ensure persist path exists
    os.makedirs(persist_dir, exist_ok=True)
    target = os.path.join(persist_dir, collection_name)
    print(f"[INFO] Persist directory: {target}")

    if backend.lower() == "chroma":
        vs = Chroma.from_documents(documents=chunked_docs, embedding=embeddings,
                                   persist_directory=target, collection_name=collection_name)
        vs.persist()
        print("[INFO] Chroma vector store created and persisted.")
        return vs

    elif backend.lower() in ("faiss", "faiss-cpu"):
        vs = FAISS.from_documents(documents=chunked_docs, embedding=embeddings)
        vs.save_local(target)
        print("[INFO] FAISS index created and saved.")
        return vs

    else:
        raise ValueError("Unsupported backend. Choose 'chroma' or 'faiss'.")


# -------------------
# CLI & quick test
# -------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Root folder with NetCDF files")
    parser.add_argument("--persist_dir", default="./vectorstore", help="Where to persist vectorstore")
    parser.add_argument("--collection", default="floatchat_profiles", help="Chroma collection or folder name")
    parser.add_argument("--backend", default="chroma", choices=["chroma","faiss"], help="Which vector DB backend")
    parser.add_argument("--embedding_model", default="all-MiniLM-L6-v2", help="Sentence-transformers model name")
    parser.add_argument("--chunk_size", type=int, default=700)
    parser.add_argument("--chunk_overlap", type=int, default=120)
    parser.add_argument("--max_files", type=int, default=None)
    args = parser.parse_args()

    vs = ingest_to_vectorstore(
        root_dir=args.root,
        embedding_model=args.embedding_model,
        backend=args.backend,
        persist_dir=args.persist_dir,
        collection_name=args.collection,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        max_files=args.max_files
    )

    # Quick retrieval test
    print("\n[INFO] Running a quick semantic search test (k=5).")
    test_queries = [
        "salinity profiles near the equator in March 2023",
        "temperature profile with many levels",
        "argos in the Arabian Sea"
    ]
    for q in test_queries:
        print(f"\n--- Query: {q}")
        try:
            results = vs.similarity_search(q, k=5)
            for i, r in enumerate(results):
                print(f"Result {i+1}:")
                print(r.page_content[:400].replace("\n"," | "))
                print("metadata:", r.metadata)
        except Exception as e:
            print("Search failed:", e)


if __name__ == "__main__":
    main()
