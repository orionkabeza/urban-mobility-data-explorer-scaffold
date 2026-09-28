"""DSA Integration: linear search vs. dict lookup benchmark.

Run from anywhere, e.g.:
    python dsa/search_benchmark.py
    python -m dsa.search_benchmark
    python dsa/search_benchmark.py --xml "path/to/modified_sms_v2.xml"
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

# Allow running as a plain script (python dsa/search_benchmark.py), where the
# project root is not on sys.path and `from dsa...` would otherwise fail.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dsa.storage import load_store  # noqa: E402

RAW_DIR = PROJECT_ROOT / "data" / "raw"
JSON_PATH = PROJECT_ROOT / "data" / "processed" / "transactions.json"


def find_xml(explicit: Path | None = None) -> Path:
    """Locates the SMS XML independent of the current working directory.

    Accepts the canonical name (modified_sms_v2.xml) as well as browser-style
    duplicates such as modified_sms_v2-1.xml or "modified_sms_v2 (1).xml".
    """
    if explicit is not None:
        if not explicit.exists():
            raise FileNotFoundError(f"XML file not found: {explicit}")
        return explicit

    canonical = RAW_DIR / "modified_sms_v2.xml"
    if canonical.exists():
        return canonical

    candidates = sorted(RAW_DIR.glob("modified_sms_v2*.xml"))
    if candidates:
        return candidates[0]

    raise FileNotFoundError(
        f"No modified_sms_v2*.xml found in {RAW_DIR}. "
        "Place the SMS backup there (or pass --xml <path>)."
    )


def linear_search(records: list[dict[str, Any]], target_id: int) -> dict[str, Any] | None:
    """O(n) scan through records for id == target_id."""
    for record in records:
        if record["id"] == target_id:
            return record
    return None


def dict_lookup(index: dict[int, dict[str, Any]], target_id: int) -> dict[str, Any] | None:
    """O(1) average-case dict lookup."""
    return index.get(target_id)


def benchmark(sample_size: int = 20, repeats: int = 1000, xml_path: Path | None = None) -> None:
    """Times linear_search vs dict_lookup over `sample_size` ids (plus the
    last record and a not-found id as worst cases) and prints a comparison."""
    xml = find_xml(xml_path)
    store = load_store(json_path=JSON_PATH, xml_path=xml)
    records, index = store.list(), store.as_dict()
    n = len(records)
    if n == 0:
        raise SystemExit("No transactions loaded - nothing to benchmark.")

    # Evenly spread ids across the dataset.
    step = max(1, n // sample_size)
    sample_ids = [records[i]["id"] for i in range(0, n, step)][:sample_size]

    # Worst cases: last record (full scan, found) and a missing id (full scan, not found).
    sample_ids.append(records[-1]["id"])
    sample_ids.append(max(r["id"] for r in records) + 1)

    # Sanity check: both methods must agree before we trust the timings.
    for tid in sample_ids:
        assert linear_search(records, tid) is dict_lookup(index, tid), f"Mismatch for id {tid}"

    t0 = time.perf_counter()
    for _ in range(repeats):
        for tid in sample_ids:
            linear_search(records, tid)
    linear_elapsed = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(repeats):
        for tid in sample_ids:
            dict_lookup(index, tid)
    dict_elapsed = time.perf_counter() - t0

    total = repeats * len(sample_ids)
    print(f"Data source : {xml}")
    print(f"Dataset size: {n} records")
    print(f"Ids searched per repeat: {len(sample_ids)} (incl. last-record and not-found worst cases)")
    print(f"Repeats: {repeats}  (total lookups per method: {total})")
    print()
    print(f"{'Method':<15}{'Total time (s)':<18}{'Avg per lookup (us)':<22}")
    print("-" * 55)
    print(f"{'linear_search':<15}{linear_elapsed:<18.4f}{linear_elapsed / total * 1e6:<22.4f}")
    print(f"{'dict_lookup':<15}{dict_elapsed:<18.4f}{dict_elapsed / total * 1e6:<22.4f}")
    print()
    speedup = linear_elapsed / dict_elapsed if dict_elapsed > 0 else float("inf")
    print(f"dict_lookup was ~{speedup:.1f}x faster than linear_search")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml", type=Path, default=None, help="Path to the SMS backup XML")
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--repeats", type=int, default=1000)
    args = parser.parse_args()
    benchmark(sample_size=args.sample_size, repeats=args.repeats, xml_path=args.xml)