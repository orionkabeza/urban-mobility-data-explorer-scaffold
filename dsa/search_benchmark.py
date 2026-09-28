from __future__ import annotations

import time
from typing import Any

from dsa.storage import load_store


def linear_search(records: list[dict[str, Any]], target_id: int) -> dict[str, Any] | None:
    """O(n) scan through records for id == target_id."""
    for record in records:
        if record["id"] == target_id:
            return record
    return None


def dict_lookup(index: dict[int, dict[str, Any]], target_id: int) -> dict[str, Any] | None:
    """O(1) average-case dict lookup."""
    return index.get(target_id)


def benchmark(sample_size: int = 20, repeats: int = 1000) -> None:
    """Time linear_search vs dict_lookup over `sample_size` ids and print
    a comparison table."""
    store = load_store()
    records, index = store.list(), store.as_dict()
    n = len(records)

    # Spread sample ids evenly across the dataset.
    step = max(1, n // sample_size)
    sample_ids = [records[i]["id"] for i in range(0, n, step)][:sample_size]

    # Explicit worst-case: last record (linear_search must scan the whole
    # list) and a guaranteed "not found" id (linear_search scans the whole
    # list with no match; dict_lookup misses immediately).
    sample_ids.append(records[-1]["id"])
    not_found_id = max(r["id"] for r in records) + 1
    sample_ids.append(not_found_id)

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

    total_lookups = repeats * len(sample_ids)
    print(f"Dataset size: {n} records")
    print(f"Ids searched per repeat: {len(sample_ids)} (includes last-record "
          f"and not-found worst cases)")
    print(f"Repeats: {repeats}  (total lookups per method: {total_lookups})")
    print()
    print(f"{'Method':<15}{'Total time (s)':<18}{'Avg per lookup (µs)':<22}")
    print(f"{'-'*15}{'-'*18}{'-'*22}")
    print(f"{'linear_search':<15}{linear_elapsed:<18.4f}"
          f"{(linear_elapsed / total_lookups) * 1e6:<22.4f}")
    print(f"{'dict_lookup':<15}{dict_elapsed:<18.4f}"
          f"{(dict_elapsed / total_lookups) * 1e6:<22.4f}")
    print()
    speedup = linear_elapsed / dict_elapsed if dict_elapsed > 0 else float("inf")
    print(f"dict_lookup was ~{speedup:.1f}x faster than linear_search")


if __name__ == "__main__":
    benchmark()