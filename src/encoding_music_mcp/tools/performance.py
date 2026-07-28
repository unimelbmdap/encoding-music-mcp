"""Concurrency and result-cache helpers for CPU-heavy analysis tools."""

from __future__ import annotations

import copy
import inspect
import json
import os
from collections import OrderedDict
from functools import wraps
from threading import BoundedSemaphore, Lock
from typing import Any, Callable, ParamSpec, TypeVar

from .helpers import get_mei_filepath

P = ParamSpec("P")
R = TypeVar("R")


def _positive_int_from_env(name: str, default: int) -> int:
    """Read a positive integer setting, falling back to a safe default."""
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


# Two analysis jobs gave the best balance for small scores in local benchmarks.
# A bounded pool prevents dozens of CPU-heavy jobs from making every request slow.
_ANALYSIS_CONCURRENCY = _positive_int_from_env("MCP_ANALYSIS_CONCURRENCY", 2)
_ANALYSIS_SEMAPHORE = BoundedSemaphore(_ANALYSIS_CONCURRENCY)

_RESULT_CACHE_SIZE = _positive_int_from_env("MCP_RESULT_CACHE_SIZE", 32)
_RESULT_CACHE: OrderedDict[str, Any] = OrderedDict()
_RESULT_CACHE_LOCK = Lock()
_IN_FLIGHT_LOCKS: dict[str, Lock] = {}


def limit_analysis_concurrency(
    function: Callable[P, R],
) -> Callable[P, R]:
    """Limit simultaneous execution without blocking the asyncio event loop."""

    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        with _ANALYSIS_SEMAPHORE:
            return function(*args, **kwargs)

    return wrapped


def _file_signature(filename: str | None) -> tuple[str, int, int] | None:
    """Return a cache signature that changes when an MEI file changes."""
    if not filename:
        return None

    filepath = get_mei_filepath(filename)
    try:
        stat = filepath.stat()
    except OSError:
        return (str(filepath.resolve()), -1, -1)
    return (str(filepath.resolve()), stat.st_mtime_ns, stat.st_size)


def _cache_key(
    function: Callable[..., Any],
    signature: inspect.Signature,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    """Build a stable key from call arguments and the source file fingerprint."""
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    arguments = dict(bound.arguments)
    filename = arguments.get("filename")
    payload = {
        "tool": function.__name__,
        "arguments": arguments,
        "file": _file_signature(filename if isinstance(filename, str) else None),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def cache_analysis_result(
    function: Callable[P, R],
) -> Callable[P, R]:
    """Cache deterministic results and coalesce simultaneous identical calls."""
    signature = inspect.signature(function)

    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        key = _cache_key(function, signature, args, kwargs)

        with _RESULT_CACHE_LOCK:
            if key in _RESULT_CACHE:
                cached = _RESULT_CACHE.pop(key)
                _RESULT_CACHE[key] = cached
                return copy.deepcopy(cached)
            key_lock = _IN_FLIGHT_LOCKS.setdefault(key, Lock())

        try:
            with key_lock:
                with _RESULT_CACHE_LOCK:
                    if key in _RESULT_CACHE:
                        cached = _RESULT_CACHE.pop(key)
                        _RESULT_CACHE[key] = cached
                        return copy.deepcopy(cached)

                result = function(*args, **kwargs)

                with _RESULT_CACHE_LOCK:
                    _RESULT_CACHE[key] = copy.deepcopy(result)
                    _RESULT_CACHE.move_to_end(key)
                    while len(_RESULT_CACHE) > _RESULT_CACHE_SIZE:
                        _RESULT_CACHE.popitem(last=False)
                    if _IN_FLIGHT_LOCKS.get(key) is key_lock:
                        _IN_FLIGHT_LOCKS.pop(key, None)
                return result
        except BaseException:
            with _RESULT_CACHE_LOCK:
                if _IN_FLIGHT_LOCKS.get(key) is key_lock:
                    _IN_FLIGHT_LOCKS.pop(key, None)
            raise

    return wrapped


def performant_analysis_tool(
    function: Callable[P, R],
) -> Callable[P, R]:
    """Apply result caching outside the analysis concurrency limiter."""
    return cache_analysis_result(limit_analysis_concurrency(function))


def clear_analysis_result_cache() -> None:
    """Clear cached results; intended for tests and operational maintenance."""
    with _RESULT_CACHE_LOCK:
        _RESULT_CACHE.clear()
        _IN_FLIGHT_LOCKS.clear()
