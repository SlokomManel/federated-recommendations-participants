"""Inspection script for U.npy and global_V.npy

Usage: python scripts/inspect_matrices.py

This script attempts to use src.core to discover SyftBox paths. If that fails
it falls back to the common ~/.syftbox paths. It prints presence, shapes, norms,
min/max/mean and a small sample of values for U and global_V.
"""
from pathlib import Path
import json
import sys

try:
    from src.core import get_private_path, get_shared_folder_path
    from src.config import APP_NAME
    HAS_CORE = True
except Exception:
    HAS_CORE = False

import numpy as np


def inspect_array(path: Path):
    print(f"\nInspecting: {path}")
    if not path.exists():
        print("  MISSING")
        return
    try:
        arr = np.load(path, allow_pickle=True)
    except Exception as e:
        print(f"  Could not load npy: {e}")
        return
    if isinstance(arr, np.ndarray):
        print(f"  type: ndarray, shape: {arr.shape}")
        try:
            flat = arr.astype(float).ravel()
            print(f"  dtype: {arr.dtype}, len: {flat.size}")
            print(f"  norm: {np.linalg.norm(flat):.6f}")
            print(f"  min: {flat.min():.6f}, max: {flat.max():.6f}, mean: {flat.mean():.6f}")
            sample = flat[:10]
            print(f"  sample (first 10): {sample.tolist()}")
        except Exception as e:
            print(f"  Could not summarize array values: {e}")
    else:
        print(f"  Loaded object type: {type(arr)}")
        try:
            if isinstance(arr, dict):
                print(f"  dict keys (sample): {list(arr.keys())[:10]}")
        except Exception:
            pass


def main():
    print("Matrix inspection for federated-recommendations")

    if HAS_CORE:
        try:
            private = get_private_path()
            shared = get_shared_folder_path()
            print(f"Detected paths from src.core:")
            print(f"  private: {private}")
            print(f"  shared: {shared}")
        except Exception as e:
            print(f"src.core import succeeded but path lookup failed: {e}")
            private = None
            shared = None
    else:
        print("Could not import src.core. Falling back to common syftbox paths.")
        private = None
        shared = None

    # Fallback guesses (user may need to adapt these)
    fallback_private = Path.home() / ".syftbox" / "private" / ("federated-recommendations") / "profile_0" / "svd_training"
    fallback_shared = Path.home() / ".syftbox" / "aggregator" / "app_data" / ("federated-recommendations")

    # Candidate paths
    u_candidates = []
    v_candidates = []

    if private:
        u_candidates.append(Path(private) / "svd_training" / "U.npy")
    u_candidates.append(fallback_private / "U.npy")

    if shared:
        v_candidates.append(Path(shared) / "global_V.npy")
    v_candidates.append(fallback_shared / "global_V.npy")

    print("\nChecking U candidates:")
    for p in u_candidates:
        inspect_array(Path(p))

    print("\nChecking global_V candidates:")
    for p in v_candidates:
        inspect_array(Path(p))

    print("\nCheck for vocabulary.json in shared folder(s):")
    if shared:
        p = Path(shared) / "vocabulary.json"
        print(f"  {p} -> exists: {p.exists()}")
    p = fallback_shared / "vocabulary.json"
    print(f"  {p} -> exists: {p.exists()}")

    print("\nDone.")


if __name__ == '__main__':
    main()
