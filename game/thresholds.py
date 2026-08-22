def parse_threshold(value):
    """'3+' -> 3, '-' or falsy -> None (no roll can ever succeed)."""
    if not value or value == "-":
        return None
    return int(str(value).rstrip("+"))
