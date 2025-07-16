from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from typing import TypeVar, Callable, ParamSpec, Concatenate, TYPE_CHECKING
import functools
import inspect

P = ParamSpec("P")
R = TypeVar("R")

def validate_kwargs(target_method: Callable[..., Any], exclude=()):
    valid_keys = {
        k for k in inspect.signature(target_method).parameters
        if k not in exclude
    }

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            unexpected = [k for k in kwargs if k not in valid_keys]
            if unexpected:
                raise TypeError(f"Unexpected keyword argument(s): {', '.join(unexpected)}")
            return func(*args, **kwargs)
        return wrapper
    return decorator