import asyncio
import functools
from typing import Any, Awaitable, Callable


def make_sync(func: Awaitable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(func(*args, **kwargs))

    return wrapper


# unused
def truncate_string(s: str, limit: int = 75, ellipsis: str = "…") -> str:
    return s[:limit] + bool(s[limit:]) * ellipsis


# unused
def colorize(s: str, color: str) -> str:
    color_map = {
        "black": 30,
        "red": 31,
        "green": 32,
        "yellow": 33,
        "blue": 34,
        "magenta": 35,
        "cyan": 36,
        "white": 37,
    }
    return f"\033[{color_map[color]}m{s}\033[0m"
