"""Escape user-provided strings for safe LaTeX rendering."""

_REPLACEMENTS = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "#": r"\#",
    "%": r"\%",
    "&": r"\&",
    "_": r"\_",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def tex_escape(value: str) -> str:
    """Escape LaTeX special characters in a string."""
    # Process backslash first to avoid double-escaping
    result = value.replace("\\", "\x00BACKSLASH\x00")
    for char, escaped in _REPLACEMENTS.items():
        if char == "\\":
            continue
        result = result.replace(char, escaped)
    result = result.replace("\x00BACKSLASH\x00", r"\textbackslash{}")
    return result


def escape_data(data: dict | list | str | int | float | bool | None) -> dict | list | str | int | float | bool | None:
    """Recursively escape all string values in a data structure."""
    if isinstance(data, str):
        return tex_escape(data)
    if isinstance(data, dict):
        return {k: escape_data(v) for k, v in data.items()}
    if isinstance(data, list):
        return [escape_data(v) for v in data]
    return data
