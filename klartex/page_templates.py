"""Page template loader and registry.

A page template is composed from two independent slots, ``header`` and
``footer``. Each slot is either a predefined variant (a ``.tex.jinja``
fragment in ``page_templates/<slot>/<variant>.tex.jinja``), a custom source
supplied by the caller, or empty. Structured settings keep applying to
whichever slot stays predefined.

Header variants are ``letterhead`` (organisation details and logo) and
``logo`` (logo only); the footer variant is ``standard``. The names
``formal``, ``clean`` and ``none`` are aliases for slot combinations.

Page template data in the render request can be either a string (an alias)
or an object::

    "page_template": "formal"

    "page_template": {
        "header": {
            "variant": "letterhead",
            "org_name": "Föreningen Klartex",
            "email": "info@example.org"
        },
        "footer": {
            "company": "Bolaget AB",
            "org_number": "556123-4567",
            "bankgiro": "1234-5678"
        },
        "page_numbers": false,
        "first_page_header": false,
        "font": "Futura",
        "header_font": "Futura"
    }

Custom slot sources are not part of the JSON payload; they travel as
``render(header_source=…)`` / ``render(footer_source=…)`` keyword arguments,
and ``page_template_source`` supplies one source for both slots.
"""

from dataclasses import dataclass, field
from pathlib import Path

import jinja2

from klartex.jinja_env import make_env

# Default directory for page template definitions
_ROOT = Path(__file__).resolve().parent
PAGE_TEMPLATES_DIR = _ROOT / "page_templates"

_fragment_env = make_env(jinja2.FileSystemLoader([str(PAGE_TEMPLATES_DIR)]))


# Predefined slot variants: name -> description and the settings it accepts.
HEADER_VARIANTS: dict[str, dict] = {
    "letterhead": {
        "description": (
            "Organisationsuppgifter till vänster och logotyp till höger "
            "i sidhuvudet"
        ),
        "settings": ("org_name", "address", "web", "email", "phone", "logo"),
    },
    "logo": {
        "description": "Endast logotyp till höger i sidhuvudet",
        "settings": ("logo",),
    },
}

# Footer fields grouped by footer column, in render order
FOOTER_COMPANY_FIELDS = ("company", "address", "seat")
FOOTER_CONTACT_FIELDS = ("phone", "email", "web")
FOOTER_PAYMENT_FIELDS = ("bankgiro", "plusgiro", "iban", "bic")
FOOTER_ORG_FIELDS = ("org_number", "vat_number", "f_tax")
FOOTER_FIELDS = (
    FOOTER_COMPANY_FIELDS
    + FOOTER_CONTACT_FIELDS
    + FOOTER_PAYMENT_FIELDS
    + FOOTER_ORG_FIELDS
)

FOOTER_VARIANTS: dict[str, dict] = {
    "standard": {
        "description": (
            "Sidnummer centrerat i sidfoten, med dokumenttiteln före numret "
            "när title är satt; kontaktfält ger en flerkolumnsfot"
        ),
        "settings": ("title",) + FOOTER_FIELDS,
    },
}

_VARIANTS: dict[str, dict[str, dict]] = {
    "header": HEADER_VARIANTS,
    "footer": FOOTER_VARIANTS,
}

# Slot-object keys that configure the slot rather than name a footer field.
# ``page_numbers`` is reserved for the per-slot page-number policy and is
# rejected until that policy is defined (#67).
FOOTER_RESERVED_KEYS = ("variant", "title", "page_numbers")

# Header-space reclaim: emitted after both slots, so the \ifdefempty test at
# preamble end sees the final value of the contract macros.
_RECLAIM = r"\geometry{top=2cm, headheight=0pt, headsep=0pt, includehead=false}"
_RECLAIM_GUARDED = (
    "%\n  " + _RECLAIM + "%\n  " + r"\fancyhead{}" + "%\n}{}"
)
_HEADER_RECLAIM: dict[str, str] = {
    "letterhead": r"\ifdefempty{\orgname}{\ifdefempty{\brandlogo}{" + _RECLAIM_GUARDED + "}{}",
    "logo": r"\ifdefempty{\brandlogo}{" + _RECLAIM_GUARDED,
}

# Aliases: legacy page-template names as slot combinations.
_ALIASES: dict[str, dict] = {
    "formal": {
        "description": "Logo top-left, org name in header, page numbers in footer",
        "header": ("letterhead", {}),
        "footer": ("standard", {"title": True}),
    },
    "clean": {
        "description": "Logo only in header, page numbers in footer, no org details",
        "header": ("logo", {}),
        "footer": ("standard", {}),
    },
    "none": {
        "description": "No header, page numbers only in footer",
        "header": (None, {}),
        "footer": ("standard", {}),
    },
}

_MISSING = object()


@dataclass
class SlotSpec:
    """One resolved page-template slot: predefined, custom or empty."""

    variant: str | None = None
    source: str | None = None
    settings: dict = field(default_factory=dict)
    #: True when ``source`` is a monolithic source shared with the other slot,
    #: so the composition emits it once.
    shared_source: bool = False

    @property
    def is_custom(self) -> bool:
        return self.source is not None

    @property
    def is_predefined(self) -> bool:
        return self.source is None and self.variant is not None

    @property
    def is_empty(self) -> bool:
        return self.source is None and self.variant is None

    @property
    def fields(self) -> dict:
        """Settings that are content fields, i.e. not slot configuration."""
        return {
            k: v
            for k, v in self.settings.items()
            if k not in FOOTER_RESERVED_KEYS
        }

    @property
    def has_fields(self) -> bool:
        return bool(self.fields)


@dataclass
class PageTemplate:
    """Resolved page template definition."""

    name: str
    description: str = ""
    header: SlotSpec = field(default_factory=SlotSpec)
    footer: SlotSpec = field(default_factory=SlotSpec)
    page_numbers: bool = True
    first_page_header: bool = True
    font: str | None = None
    header_font: str | None = None
    diff_style: str = "color"

    @property
    def footer_has_payment(self) -> bool:
        """True when the footer carries any payment field — the signal for
        the faktura recipe to suppress its in-body payment_info block."""
        fields = self.footer.fields
        return any(fields.get(f) for f in FOOTER_PAYMENT_FIELDS)

    @property
    def header_fragment(self) -> str:
        """The rendered header variant fragment, empty unless predefined."""
        if not self.header.is_predefined:
            return ""
        return render_fragment("header", self.header.variant, self.header.settings)

    @property
    def footer_fragment(self) -> str:
        """The rendered footer variant fragment, empty unless predefined."""
        if not self.footer.is_predefined:
            return ""
        return render_fragment("footer", self.footer.variant, self.footer.settings)

    @property
    def header_reclaim(self) -> str:
        """The header-space reclaim block for the resolved header slot.

        Empty for a custom header — that source owns its own geometry.
        """
        if self.header.is_custom:
            return ""
        if self.header.is_empty:
            return _RECLAIM
        return _HEADER_RECLAIM.get(self.header.variant, "")


def _variant_names(slot: str) -> str:
    return ", ".join(_VARIANTS[slot])


def _check_variant(slot: str, variant: str) -> None:
    if variant not in _VARIANTS[slot]:
        raise ValueError(
            f"Unknown page-template variant '{variant}' for the {slot} slot. "
            f"Available: {_variant_names(slot)}"
        )


def _check_settings(slot: str, variant: str, settings: dict) -> None:
    allowed = _VARIANTS[slot][variant]["settings"]
    for key in settings:
        if slot == "footer" and key == "page_numbers":
            raise ValueError(
                "'page_numbers' on the footer slot is reserved and not "
                "accepted yet"
            )
        if key not in allowed:
            raise ValueError(
                f"Unknown setting '{key}' for the {variant} {slot} variant. "
                f"Allowed: {', '.join(allowed)}"
            )


def _resolve_slot(slot: str, value, default: tuple[str | None, dict]) -> SlotSpec:
    """Resolve one slot value from the payload into a SlotSpec."""
    if value is _MISSING:
        variant, settings = default
        return SlotSpec(variant=variant, settings=dict(settings))

    if value is None:
        return SlotSpec()

    if isinstance(value, str):
        _check_variant(slot, value)
        return SlotSpec(variant=value)

    if isinstance(value, dict):
        variant = value.get("variant")
        if variant is None:
            if slot == "header":
                raise ValueError(
                    "A header slot object must include 'variant' "
                    f"(one of: {_variant_names('header')})"
                )
            variant = "standard"
        _check_variant(slot, variant)
        settings = {k: v for k, v in value.items() if k != "variant"}
        _check_settings(slot, variant, settings)
        return SlotSpec(variant=variant, settings=settings)

    raise ValueError(
        f"The {slot} slot must be null, a variant name or an object, "
        f"got {type(value).__name__}"
    )


def load_page_template(
    spec: str | dict | None = None,
    *,
    default: str = "none",
    header_source: str | None = None,
    footer_source: str | None = None,
    page_template_source: str | None = None,
) -> PageTemplate:
    """Resolve a page template from its payload value and any custom sources.

    Args:
        spec: An alias name, a slot object, or None for the engine default.
        default: Alias whose slot combination is used when ``spec`` names
                 none — the engine's own default.
        header_source: Raw ``.tex.jinja`` content owning the header slot.
        footer_source: Raw ``.tex.jinja`` content owning the footer slot.
        page_template_source: Raw content owning both slots (monolithic).
                 In this mode the payload's slot and chrome keys are ignored
                 and an unknown or missing alias name is tolerated; only the
                 document-level keys are read.

    Returns:
        Resolved PageTemplate.

    Raises:
        ValueError: If an alias, variant or setting is unknown.
    """
    if isinstance(spec, dict):
        overrides = spec
        name = spec.get("name")
    else:
        overrides = {}
        name = spec

    # Document-level settings are not chrome, so they apply in every mode,
    # including alongside a custom slot source.
    font = overrides.get("font")
    header_font = overrides.get("header_font") or font
    diff_style = overrides.get("diff_style") or "color"

    if page_template_source is not None:
        # Monolithic source: it owns both slots, so nothing about the chrome
        # is read from the payload and an unknown name is tolerated.
        return PageTemplate(
            name="custom",
            header=SlotSpec(source=page_template_source),
            footer=SlotSpec(source=page_template_source, shared_source=True),
            font=font,
            header_font=header_font,
            diff_style=diff_style,
        )

    alias_name = name if name is not None else default
    if alias_name not in _ALIASES:
        available = ", ".join(sorted(_ALIASES))
        raise ValueError(
            f"Unknown page template '{alias_name}'. Available: {available}"
        )
    alias = _ALIASES[alias_name]

    if header_source is not None:
        header = SlotSpec(source=header_source)
    else:
        header = _resolve_slot("header", overrides.get("header", _MISSING), alias["header"])

    if footer_source is not None:
        footer = SlotSpec(source=footer_source)
    else:
        footer = _resolve_slot("footer", overrides.get("footer", _MISSING), alias["footer"])

    page_numbers = overrides.get("page_numbers")
    if page_numbers is None:
        page_numbers = True
    first_page_header = overrides.get("first_page_header")
    if first_page_header is None:
        # A header that puts nothing on the page has nothing to suppress on
        # page one either, so the empty slot defaults this off.
        first_page_header = not header.is_empty

    return PageTemplate(
        name=alias_name,
        description=alias["description"],
        header=header,
        footer=footer,
        page_numbers=page_numbers,
        first_page_header=first_page_header,
        font=font,
        header_font=header_font,
        diff_style=diff_style,
    )


def read_slot_source(slot: str, variant: str) -> str:
    """Read the raw ``.tex.jinja`` source for one slot variant.

    Raises:
        FileNotFoundError: If the fragment file doesn't exist.
    """
    path = PAGE_TEMPLATES_DIR / slot / f"{variant}.tex.jinja"
    return path.read_text(encoding="utf-8")


def render_fragment(slot: str, variant: str, settings: dict | None = None) -> str:
    """Render one slot variant fragment with its settings as context."""
    source = read_slot_source(slot, variant)
    return _fragment_env.from_string(source).render(**(settings or {}))


def read_page_template_source(name: str) -> str:
    """Compose the full ``.tex.jinja`` source for a built-in alias.

    The starting point for "copy a built-in and edit it": the alias's header
    and footer fragments plus its header-space reclaim block.

    Raises:
        FileNotFoundError: If the name is not a built-in alias.
    """
    if name not in _ALIASES:
        raise FileNotFoundError(f"No built-in page template named '{name}'")
    page_template = load_page_template(name)
    parts = [
        page_template.header_fragment,
        page_template.footer_fragment,
        page_template.header_reclaim,
    ]
    return "\n".join(p for p in parts if p)


def list_page_templates() -> list[dict]:
    """Return all built-in page-template aliases with metadata.

    Returns:
        List of dicts with name, description, and defaults.
    """
    listed = []
    for name, info in sorted(_ALIASES.items()):
        resolved = load_page_template(name)
        listed.append(
            {
                "name": name,
                "description": info["description"],
                "defaults": {
                    "page_numbers": resolved.page_numbers,
                    "first_page_header": resolved.first_page_header,
                },
            }
        )
    return listed


def list_slot_variants() -> dict[str, list[dict]]:
    """Return the predefined variants available per slot.

    Returns:
        ``{"header": [{"name", "description", "settings"}], "footer": [...]}``
    """
    return {
        slot: [
            {
                "name": variant,
                "description": info["description"],
                "settings": list(info["settings"]),
            }
            for variant, info in variants.items()
        ]
        for slot, variants in _VARIANTS.items()
    }
