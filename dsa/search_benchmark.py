"""Compares linear search vs. dictionary lookup for finding a transaction by id."""

from __future__ import annotations

import time
from typing import Any

from dsa.storage import load_store


def linear_search(records: list[dict[str, Any]], target_id: int) -> dict[str, Any] | None:
    # TODO: scan the list and return the record with id == target_id, else None.
    raise NotImplementedError


def dict_lookup(index: dict[int, dict[str, Any]], target_id: int) -> dict[str, Any] | None:
    # TODO: O(1) dict lookup by id.
    raise NotImplementedError


def benchmark(sample_size: int = 20, repeats: int = 1000) -> None:
    # TODO: time linear_search vs. dict_lookup over `sample_size` ids
    # (repeated `repeats` times each, since a single lookup is
    # sub-microsecond) and print a comparison.
    raise NotImplementedError


if __name__ == "__main__":
    benchmark()
