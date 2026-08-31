"""Page template loader and registry.

A page template is composed from two independent slots, ``header`` and
``footer``. Each slot is either a predefined variant (a ``.tex.jinja``
fragment in ``page_templates/<slot>/<variant>.tex.jinja``), a custom source
supplied by the caller, or empty. Structured settings keep applying to
whichever slot stays predefined.

Header variants are ``letterhead`` (organisation details and logo) and
``logo`` (logo only); footer variants are ``pagenumber`` (page numbers,
optionally with the document title) and ``columns`` (the multi-column
footer with company, contact and payment details). A slot the payload
leaves out takes the surface's default: the block engine has an empty header
and the page-number footer, recipes the letterhead header and the
page-number footer with the document title (``BLOCK_DEFAULT_SLOTS`` /
``RECIPE_DEFAULT_SLOTS``).

Page template data in the render request is an object::

    "page_template": {
        "header": {
            "variant": "letterhead",
            "fields": {
                "org_name": "Föreningen Klartex",
                "email": "info@example.org"
            }
        },
        "footer": {
            "variant": "columns",
            "fields": {
                "company": "Bolaget AB",
                "org_number": "556123-4567",
                "bankgiro": "1234-5678"
            }
        },
        "page_numbers": false,
        "first_page_header": false,
        "font": "Futura",
        "header_font": "Futura"
    }

Custom slot sources are not part of the JSON payload; they travel as
``render(header_source=…)`` / ``render(footer_source=…)`` keyword arguments.
"""

from dataclasses import dataclass, field
from pathlib import Path

import jinja2

from klartex.jinja_env import make_env

# Default directory for page template definitions
_ROOT = Path(__file__).resolve().parent
PAGE_TEMPLATES_DIR = _ROOT / "page_templates"

_fragment_env = make_env(jinja2.FileSystemLoader([str(PAGE_TEMPLATES_DIR)]))


# ---------------------------------------------------------------------------
# The slot model — the single definition of what a page template accepts.
# A FieldType says how a value validates (JSON Schema); a Field is a named
# use of a type in a variant: its description, and how it renders — the
# header contract macro it sets, or the \kxfooter keyval it becomes. A
# Variant composes named fields and its own settings. The loader validates
# against the model, the composition include and the fragments render from
# it, and ``page_template_schema()`` generates the JSON Schema subtree that
# ``registry.py`` injects into every template schema.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldType:
    """How a field value validates — a JSON Schema, composable with
    ``|`` (union) and ``list_of()`` (array of)."""

    schema: dict

    def __or__(self, other: "FieldType") -> "FieldType":
        mine = self.schema.get("oneOf", [self.schema])
        theirs = other.schema.get("oneOf", [other.schema])
        return FieldType({"oneOf": [*mine, *theirs]})

    @property
    def is_bool(self) -> bool:
        return self.schema.get("type") == "boolean"


def list_of(item: FieldType) -> FieldType:
    return FieldType({"type": "array", "items": item.schema})


FILENAME_PATTERN = r"^[^\\#$%&_{}~^]+$"

TEXT = FieldType({"type": "string"})
BOOL = FieldType({"type": "boolean"})
FILENAME = FieldType({"type": "string", "pattern": FILENAME_PATTERN})


@dataclass(frozen=True)
class Field:
    """A named, typed field of a variant."""

    type: FieldType
    description: str
    #: Header contract macro the value is assigned to (``\renewcommand``).
    macro: str | None = None
    #: klartex-footer keyval the value becomes; defaults to the field name.
    keyval: str | None = None

    @property
    def schema(self) -> dict:
        return {**self.type.schema, "description": self.description}


@dataclass(frozen=True)
class Variant:
    """A predefined slot variant: its settings and its typed fields."""

    description: str
    settings: dict[str, dict] = field(default_factory=dict)
    fields: dict[str, Field] = field(default_factory=dict)
    #: Fields that must be present and non-empty in the object form.
    required: tuple[str, ...] = ()
    fields_description: str = ""
    empty_note: str = ""


# One word, one type, one macro, in both header variants.
LOGO = Field(
    FILENAME,
    "Logo file name, placed top right in the header. Must not contain LaTeX "
    "special characters (\\ # $ % & _ { } ~ ^); looked up in asset_dir or "
    "the working directory.",
    macro="brandlogo",
)

TITLE_SETTING = {
    "type": "boolean",
    "default": False,
    "description": "true prints the document title before the page number.",
}

HEADER_VARIANTS: dict[str, Variant] = {
    "letterhead": Variant(
        description="Organisation details on the left and the logo on the right of the header",
        fields={
            "org_name": Field(TEXT, "Organisation name, in bold at the top left.", macro="orgname"),
            "address": Field(TEXT, "Postal address, under the organisation name.", macro="orgaddress"),
            "web": Field(TEXT, "Website, in the header's right-hand text column.", macro="orgwebsite"),
            "email": Field(TEXT, "Email address, in the header's right-hand text column.", macro="orgemail"),
            "phone": Field(TEXT, "Phone number, in the header's right-hand text column.", macro="orgphone"),
            "logo": LOGO,
        },
        # The letterhead is built around the organisation name: the fragment
        # renders the whole details block only when \orgname is set, and the
        # header-space reclaim tests the same macro. Requiring it in the
        # object form keeps supplied contact details from being dropped.
        required=("org_name",),
        fields_description="The organisation details printed in the header. org_name is required — the header is built around the name.",
        empty_note="Omitted details are not printed; with neither details nor logo the header's space is reclaimed.",
    ),
    "logo": Variant(
        description="Logo only, on the right of the header",
        fields={"logo": LOGO},
        fields_description="The logo printed in the header.",
        empty_note="Without a logo the header's space is reclaimed.",
    ),
}

FOOTER_VARIANTS: dict[str, Variant] = {
    "pagenumber": Variant(
        description="Page number centred in the footer, preceded by the document title when title is set",
        settings={"title": TITLE_SETTING},
    ),
    "columns": Variant(
        description="Multi-column footer with company, contact and payment details from fields, and page numbers when the document runs past one page",
        fields={
            "company": Field(TEXT, "Company name"),
            "address": Field(
                TEXT | list_of(TEXT),
                "Postal address as an array with one line per element, e.g. "
                "['Storgatan 1', '123 45 Stad'] — line-broken like a postal "
                "address. A string renders as a single line.",
            ),
            "seat": Field(TEXT, "Registered seat of the board, e.g. 'Malmö'"),
            "phone": Field(TEXT, "Phone"),
            "email": Field(TEXT, "Email"),
            "web": Field(TEXT, "Website"),
            "bankgiro": Field(TEXT, "Bankgiro number"),
            "plusgiro": Field(TEXT, "Plusgiro number"),
            "iban": Field(TEXT, "IBAN"),
            "bic": Field(TEXT, "BIC/SWIFT"),
            "org_number": Field(TEXT, "Organisation number", keyval="orgnr"),
            "vat_number": Field(TEXT, "VAT registration number (SExxxxxxxxxx01)", keyval="vatnr"),
            "f_tax": Field(BOOL, "true shows the line 'Godkänd för F-skatt' (approved for F-tax)", keyval="ftax"),
        },
        fields_description="Contact, company and payment details, laid out over the footer's columns.",
    ),
}

_VARIANTS: dict[str, dict[str, Variant]] = {
    "header": HEADER_VARIANTS,
    "footer": FOOTER_VARIANTS,
}

#: Footer fields whose presence means "payment details are in the footer".
FOOTER_PAYMENT_FIELDS = ("bankgiro", "plusgiro", "iban", "bic")

# Slot descriptions for the generated schema.
_SLOT_TEXT = {
    "header": {
        "label": "The header",
        "empty": "Empty header — nothing is printed at the top of the page.",
        "bare": "A header variant with no fields",
    },
    "footer": {
        "label": "The footer",
        "empty": "Empty footer — nothing is printed at the bottom of the page.",
        "bare": "A footer variant with no settings",
    },
}

# Document-level settings on the page_template object.
DOCUMENT_SETTINGS: dict[str, dict] = {
    "page_numbers": {"type": "boolean", "description": "Show page numbers in the footer"},
    "first_page_header": {"type": "boolean", "description": "Show the header on the first page"},
    "font": {
        "type": "string",
        "description": "Document font (fontspec name, e.g. 'Futura'). Must be installed where rendering happens.",
    },
    "header_font": {
        "type": "string",
        "description": "Font for the header and footer. Default: same as font.",
    },
    "diff_style": {
        "type": "string",
        "enum": ["color", "underline"],
        "default": "color",
        "description": (
            "How added text is marked: \"color\" (green text, default) or "
            "\"underline\" (green underlined — the convention in change "
            "documents, and the signal that survives black-and-white printing). "
            "Removed text is struck through in both cases."
        ),
    },
}


# Header-space reclaim: emitted after both slots, so the \ifdefempty test at
# preamble end sees the final value of the contract macros.
_RECLAIM = r"\geometry{top=1.7cm, headheight=0pt, headsep=0pt, includehead=false}"
_RECLAIM_GUARDED = (
    "%\n  " + _RECLAIM + "%\n  " + r"\fancyhead{}" + "%\n}{}"
)
_HEADER_RECLAIM: dict[str, str] = {
    "letterhead": r"\ifdefempty{\orgname}{\ifdefempty{\brandlogo}{" + _RECLAIM_GUARDED + "}{}",
    "logo": r"\ifdefempty{\brandlogo}{" + _RECLAIM_GUARDED,
}

# Slot defaults per rendering surface, in payload syntax. A slot the payload
# leaves out resolves to the surface's value here.
BLOCK_DEFAULT_SLOTS: dict = {"header": None, "footer": "pagenumber"}
RECIPE_DEFAULT_SLOTS: dict = {
    "header": "letterhead",
    "footer": {"variant": "pagenumber", "title": True},
}

# Top-level keys a page_template object may carry.
PAGE_TEMPLATE_KEYS = ("header", "footer") + tuple(DOCUMENT_SETTINGS)

_MISSING = object()


@dataclass
class SlotSpec:
    """One resolved page-template slot: predefined, custom or empty."""

    variant: str | None = None
    source: str | None = None
    settings: dict = field(default_factory=dict)

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
        """The slot's content fields (the ``fields`` setting), never None."""
        return self.settings.get("fields") or {}

    @property
    def has_fields(self) -> bool:
        return bool(self.fields)


@dataclass
class PageTemplate:
    """Resolved page template definition."""

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
    def header_macros(self) -> list[tuple[str, str]]:
        """``(macro, value)`` for every header field that is set, in the
        field table's order — the ``\\renewcommand``s emitted before the
        header fragment."""
        if not self.header.is_predefined:
            return []
        fields = self.header.fields
        variant = HEADER_VARIANTS[self.header.variant]
        return [
            (typ.macro, fields[name])
            for name, typ in variant.fields.items()
            if typ.macro and fields.get(name)
        ]

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
        return render_fragment(
            "footer",
            self.footer.variant,
            {
                **self.footer.settings,
                "page_numbers": self.page_numbers,
                "keyvals": footer_keyvals(self.footer.fields),
            },
        )

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
    spec = _VARIANTS[slot][variant]
    allowed = tuple(spec.settings) + (("fields",) if spec.fields else ())
    for key in settings:
        if key not in allowed:
            raise ValueError(
                f"Unknown setting '{key}' for the {variant} {slot} variant. "
                f"Allowed: {', '.join(allowed)}"
            )
    fields = settings.get("fields")
    if fields is not None:
        if not isinstance(fields, dict):
            raise ValueError(
                f"'fields' on the {variant} {slot} variant must be an object"
            )
        for key in fields:
            if key not in spec.fields:
                raise ValueError(
                    f"Unknown field '{key}' for the {variant} {slot} variant. "
                    f"Allowed: {', '.join(spec.fields)}"
                )
    for key in spec.required:
        if not (fields or {}).get(key):
            raise ValueError(
                f"The {variant} {slot} variant requires fields.{key} when "
                f"given as an object. Use the variant name on its own for an "
                f"empty {variant} {slot}."
            )


def _resolve_slot(slot: str, value, default) -> SlotSpec:
    """Resolve one slot value from the payload into a SlotSpec.

    ``default`` is the surface's value for the slot, in payload syntax, used
    when the payload leaves the slot out.
    """
    if value is _MISSING:
        value = default

    if value is None:
        return SlotSpec()

    if isinstance(value, str):
        _check_variant(slot, value)
        return SlotSpec(variant=value)

    if isinstance(value, dict):
        variant = value.get("variant")
        if variant is None:
            raise ValueError(
                f"A {slot} slot object must include 'variant' "
                f"(one of: {_variant_names(slot)})"
            )
        _check_variant(slot, variant)
        settings = {k: v for k, v in value.items() if k != "variant"}
        _check_settings(slot, variant, settings)
        return SlotSpec(variant=variant, settings=settings)

    raise ValueError(
        f"The {slot} slot must be null, a variant name or an object, "
        f"got {type(value).__name__}"
    )


def load_page_template(
    spec: dict | None = None,
    *,
    defaults: dict | None = None,
    header_source: str | None = None,
    footer_source: str | None = None,
) -> PageTemplate:
    """Resolve a page template from its payload value and any custom sources.

    Args:
        spec: The ``page_template`` object from the payload, or None.
        defaults: Slot values, in payload syntax, for the slots ``spec``
                 leaves out — the rendering surface's own default
                 (``BLOCK_DEFAULT_SLOTS`` when omitted).
        header_source: Raw ``.tex.jinja`` content owning the header slot.
        footer_source: Raw ``.tex.jinja`` content owning the footer slot.

    Returns:
        Resolved PageTemplate.

    Raises:
        ValueError: If ``spec`` is not an object, or a key, variant or
                    setting is unknown.
    """
    if spec is None:
        overrides: dict = {}
    elif isinstance(spec, dict):
        overrides = spec
    else:
        raise ValueError(
            "page_template must be an object with header/footer slots, "
            f"got {type(spec).__name__}"
        )
    unknown = [k for k in overrides if k not in PAGE_TEMPLATE_KEYS]
    if unknown:
        raise ValueError(
            f"Unknown page_template key(s): {', '.join(unknown)}. "
            f"Allowed: {', '.join(PAGE_TEMPLATE_KEYS)}"
        )
    if defaults is None:
        defaults = BLOCK_DEFAULT_SLOTS

    # Document-level settings are not chrome, so they apply in every mode,
    # including alongside a custom slot source.
    font = overrides.get("font")
    header_font = overrides.get("header_font") or font
    diff_style = overrides.get("diff_style") or "color"

    if header_source is not None:
        header = SlotSpec(source=header_source)
    else:
        header = _resolve_slot("header", overrides.get("header", _MISSING), defaults["header"])

    if footer_source is not None:
        footer = SlotSpec(source=footer_source)
    else:
        footer = _resolve_slot("footer", overrides.get("footer", _MISSING), defaults["footer"])

    page_numbers = overrides.get("page_numbers")
    if page_numbers is None:
        page_numbers = True
    first_page_header = overrides.get("first_page_header")
    if first_page_header is None:
        # A header that puts nothing on the page has nothing to suppress on
        # page one either, so the empty slot defaults this off.
        first_page_header = not header.is_empty

    return PageTemplate(
        header=header,
        footer=footer,
        page_numbers=page_numbers,
        first_page_header=first_page_header,
        font=font,
        header_font=header_font,
        diff_style=diff_style,
    )


def footer_keyvals(fields: dict, variant: str = "columns") -> list[str]:
    """``key={value}`` strings for ``\\kxfooter``, one per set field of the
    footer variant, in the variant's field order. Values are expected to be
    LaTeX-escaped already; a list value (lines) is joined with ``\\\\``."""
    out = []
    for name, typ in FOOTER_VARIANTS[variant].fields.items():
        value = fields.get(name)
        if not value:
            continue
        keyval = typ.keyval or name
        if typ.type.is_bool:
            out.append(f"{keyval}=true")
            continue
        if isinstance(value, (list, tuple)):
            value = "\\\\".join(str(v) for v in value)
        out.append(f"{keyval}={{{value}}}")
    return out


def _slot_schema(slot: str) -> dict:
    variants = _VARIANTS[slot]
    text = _SLOT_TEXT[slot]
    bare = "; ".join(f"'{name}' ({v.description[0].lower() + v.description[1:]})" for name, v in variants.items())
    forms: list[dict] = [
        {"type": "null", "description": text["empty"]},
        {"type": "string", "enum": list(variants), "description": f"{text['bare']}: {bare}."},
    ]
    for name, v in variants.items():
        props: dict = {"variant": {"const": name}}
        required = ["variant"]
        for setting, schema in v.settings.items():
            props[setting] = dict(schema)
        if v.fields:
            fields_schema: dict = {
                "type": "object",
                "additionalProperties": False,
                "description": v.fields_description,
                "properties": {name: dict(typ.schema) for name, typ in v.fields.items()},
            }
            if v.required:
                fields_schema["required"] = list(v.required)
                required.append("fields")
            props["fields"] = fields_schema
        description = v.description + "."
        if v.empty_note:
            description += " " + v.empty_note
        forms.append({
            "type": "object",
            "description": description,
            "required": required,
            "additionalProperties": False,
            "properties": props,
        })
    return {
        "description": f"{text['label']} slot: null for empty, a variant name, or an object with variant and the variant's settings.",
        "oneOf": forms,
    }


def page_template_schema(default_text: str) -> dict:
    """The JSON Schema subtree for ``page_template``, generated from the slot
    model. ``default_text`` names the surface's default for the description
    (what a left-out slot resolves to)."""
    return {
        "description": (
            "Page template as two independent slots, header and footer. Each "
            "slot is null for empty, a variant name, or an object with variant "
            f"and settings. A slot left out takes the surface's default — {default_text}."
        ),
        "type": "object",
        "additionalProperties": False,
        "properties": {
            **{key: dict(schema) for key, schema in DOCUMENT_SETTINGS.items()},
            "header": _slot_schema("header"),
            "footer": _slot_schema("footer"),
        },
    }


BLOCK_DEFAULT_TEXT = "an empty header and the page-number footer"
RECIPE_DEFAULT_TEXT = "the letterhead header and the page-number footer with the document title"


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


def list_slot_variants() -> dict[str, list[dict]]:
    """Return the predefined variants available per slot.

    Returns:
        ``{"header": [{"name", "description", "settings"}], "footer": [...]}``
    """
    return {
        slot: [
            {
                "name": variant,
                "description": info.description,
                "settings": list(info.settings),
                "fields": list(info.fields),
            }
            for variant, info in variants.items()
        ]
        for slot, variants in _VARIANTS.items()
    }
