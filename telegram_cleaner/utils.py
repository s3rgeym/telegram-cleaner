def truncate_string(s: str, limit: int = 75, ellipsis: str = "…") -> str:
    return s[:limit] + bool(s[limit:]) * ellipsis
