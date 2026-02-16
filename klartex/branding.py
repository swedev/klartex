"""Load branding configuration from YAML files."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Branding:
    name: str = ""
    org_number: str = ""
    address: dict = field(default_factory=lambda: {"line1": "", "line2": ""})
    website: str = ""
    email: str = ""
    phone: str = ""
    logo: str = ""
    colors: dict = field(default_factory=lambda: {"primary": "1A1A1A", "secondary": "666666", "accent": "0066CC"})
    font: dict = field(default_factory=lambda: {"family": ""})
    lang: str = "sv"


def load_branding(name: str, branding_dir: Path) -> tuple[Branding, Path]:
    """Load a branding config by name from the branding directory.

    Returns:
        Tuple of (Branding, resolved branding directory path)
    """
    path = branding_dir / f"{name}.yaml"
    if not path.exists():
        if name == "default":
            return Branding(), branding_dir
        raise FileNotFoundError(f"Branding '{name}' not found: {path}")
    raw = yaml.safe_load(path.read_text())
    return Branding(**raw), branding_dir.resolve()
