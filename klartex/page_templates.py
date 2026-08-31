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
        "header_font": "Futura",
        "margins": {"top": "3.4cm", "bottom": "2cm", "left": "3cm", "right": "3cm"}
    }

``font`` and ``header_font`` also accept an object naming font files that
travel with the render as assets — ``{"file": "Inter-Regular.ttf", "bold":
"Inter-Bold.ttf"}`` — for fonts the render environment does not install.

Custom sources are not part of the JSON payload; they travel as keyword
arguments to ``render()``: ``header_source`` and ``footer_source`` own one
slot each, and ``page_template_source`` is one whole-page source owning both
slots. The document-level settings above apply in every mode.
"""

import re
from dataclasses import dataclass, field
from fractions import Fraction
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

#: A LaTeX dimension: a non-negative number with an explicit unit. The four
#: units are the supported set — font-relative units (em, ex) have no stable
#: meaning before \setmainfont resolves. The pattern admits no LaTeX special
#: character, so a value passes escape_data() untouched and is safe inside
#: the emitted \geometry call.
#:
#: The trailing lookahead is what makes that true: Python's ``$`` also matches
#: before a final newline, so ``"2cm\n"`` would otherwise satisfy both this
#: pattern and jsonschema's ``pattern`` keyword. ``(?![\s\S])`` says "nothing
#: follows" in every regex flavour a JSON Schema validator may use.
DIMENSION_PATTERN = r"^[0-9]+(\.[0-9]+)?(cm|mm|pt|in)$(?![\s\S])"

_DIMENSION_RE = re.compile(DIMENSION_PATTERN)

#: Exact conversion factors to TeX points, so boundary comparisons carry no
#: float wobble.
_UNIT_IN_PT: dict[str, Fraction] = {
    "pt": Fraction(1),
    "in": Fraction(7227, 100),
    "cm": Fraction(7227, 254),
    "mm": Fraction(7227, 2540),
}

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

# ---------------------------------------------------------------------------
# Margins. The values are text-block margins — paper edge to body text — so
# the chrome geometry adapts to them: a set top becomes both a headsep
# adjustment (header renders) and a \kxreclaimtop renewal (header reclaimed),
# and the LaTeX-time \ifdefempty reclaim picks the regime.
# ---------------------------------------------------------------------------

MARGIN_KEYS = ("top", "bottom", "left", "right")


def _cm(value: Fraction) -> str:
    """A Fraction of centimetres as a LaTeX dimension string."""
    return f"{float(value):g}cm"


#: Bottom edge of the header band, from the paper edge: the class geometry's
#: top (0.9cm) plus headheight (1.2cm) in klartex-base.cls. A set margins.top
#: places the text block there, so the header–text gap absorbs the difference.
#: tests/test_renderer.py locks this against the two values in the cls.
HEADER_BAND_BOTTOM_CM = Fraction(21, 10)
HEADER_BAND_BOTTOM = _cm(HEADER_BAND_BOTTOM_CM)

#: Clearance the columns footer keeps below its band — the difference between
#: klartex-footer.sty's own bottom and footskip defaults. A set margins.bottom
#: moves both and preserves it.
FOOTER_BAND_CLEARANCE = "1cm"

_MARGIN_KEY_DESCRIPTIONS = {
    "top": (
        "Paper edge to the first line of body text. With a header the band "
        f"stays put and the header–text gap absorbs the change, so top must "
        f"exceed {HEADER_BAND_BOTTOM} (the band's bottom edge); with an empty "
        "or content-less header the header space is reclaimed and any positive "
        "value works."
    ),
    "bottom": (
        "Paper edge to the last line of body text. The footer hangs below the "
        "text block, so leave room for it — a small value clips it."
    ),
    "left": "Paper edge to the left of the body text. The header and footer band follows the text width.",
    "right": "Paper edge to the right of the body text. The header and footer band follows the text width.",
}

MARGINS_SETTING: dict = {
    "type": ["object", "null"],
    "additionalProperties": False,
    "description": (
        "Page margins as the distance from the paper edge to the body text "
        "block, e.g. {\"top\": \"3.4cm\", \"left\": \"2cm\"}. Each key is "
        "independent and optional; the chrome adapts, so the header band and "
        "the footer keep their place relative to the text. Values are LaTeX "
        "dimensions with an explicit unit (cm, mm, pt, in). A custom slot "
        "source that emits its own geometry wins, like it does for font."
    ),
    "properties": {
        key: {
            "type": "string",
            "pattern": DIMENSION_PATTERN,
            "description": _MARGIN_KEY_DESCRIPTIONS[key],
        }
        for key in MARGIN_KEYS
    },
}


def _to_points(value: str) -> Fraction:
    """A validated dimension string in TeX points."""
    match = _DIMENSION_RE.fullmatch(value)
    unit = match.group(2)
    return Fraction(value[: -len(unit)]) * _UNIT_IN_PT[unit]


def _check_margins(margins) -> dict:
    """Validate the ``margins`` setting and return it as a dict.

    ``None`` and ``{}`` both mean "no margins given".

    Raises:
        ValueError: If the value is not an object, carries an unknown key, or
                    holds a value that is not a LaTeX dimension.
    """
    if margins is None:
        return {}
    if not isinstance(margins, dict):
        raise ValueError(
            "page_template.margins must be an object with the keys "
            f"{', '.join(MARGIN_KEYS)}, got {type(margins).__name__}"
        )
    for key, value in margins.items():
        if key not in MARGIN_KEYS:
            raise ValueError(
                f"Unknown margins key '{key}'. Allowed: {', '.join(MARGIN_KEYS)}"
            )
        if not isinstance(value, str) or not _DIMENSION_RE.fullmatch(value):
            raise ValueError(
                f"margins.{key} must be a LaTeX dimension with an explicit "
                f"unit (cm, mm, pt, in), e.g. '2.5cm', got {value!r}"
            )
    return dict(margins)


#: Font families the render environment guarantees. The Microsoft core fonts
#: come from ttf-mscorefonts-installer, the rest from Debian font packages;
#: docker/Dockerfile.base installs both and fails the image build unless every
#: name here is an exact family in ``fc-list : family``. The font and
#: header_font descriptions below enumerate this tuple, so the discovery
#: surface and the image are one list, and a parametrized xelatex test renders
#: each family.
GUARANTEED_FONTS: tuple[str, ...] = (
    # Microsoft core fonts
    "Arial",
    "Courier New",
    "Georgia",
    "Times New Roman",
    "Trebuchet MS",
    "Verdana",
    # Open families from Debian packages
    "EB Garamond",
    "IBM Plex Mono",
    "IBM Plex Sans",
    "IBM Plex Serif",
    "Inter",
    "Lato",
    "Noto Sans",
    "Noto Serif",
    "Open Sans",
    "Roboto",
)

_GUARANTEED_FONTS_TEXT = ", ".join(GUARANTEED_FONTS)


# ---------------------------------------------------------------------------
# Font files. Beside a family name, ``font`` and ``header_font`` accept an
# object naming .ttf/.otf files that travel with the render as assets, so a
# document can use a font the render environment does not install.
# ---------------------------------------------------------------------------

#: A font face file: a bare basename with a lowercase .ttf/.otf extension, at
#: most 128 characters. The pattern admits no path separator and no LaTeX
#: special character — underscore included — so a value passes escape_data()
#: byte-identical and is safe inside the emitted fontspec call. It is stricter
#: than the server's own asset-name rule, so every name the schema admits is
#: one the endpoint accepts.
#:
#: The trailing lookahead does here what it does for DIMENSION_PATTERN:
#: Python's ``$`` also matches before a final newline, so ``"Inter.ttf\n"``
#: would otherwise satisfy jsonschema's ``pattern`` keyword.
FONT_FILENAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9.-]{0,123}\.(ttf|otf)$(?![\s\S])"

_FONT_FILENAME_RE = re.compile(FONT_FILENAME_PATTERN)

#: The keys of the font file form, in fontspec emission order, mapped to the
#: fontspec option each becomes. ``file`` is the font itself, so it has none.
FONT_FACE_OPTIONS: dict[str, str | None] = {
    "file": None,
    "bold": "BoldFont",
    "italic": "ItalicFont",
    "bold_italic": "BoldItalicFont",
}

_FONT_FACE_DESCRIPTIONS = {
    "file": "The regular face — the file the family is named by. Required.",
    "bold": "The bold face, used by **bold** markup.",
    "italic": "The italic face, used by *italic* markup.",
    "bold_italic": "The bold-italic face, used where both apply.",
}

#: The file form, described once for both settings.
_FONT_FILE_FORM = (
    "An object instead of a name loads font files that travel with the render "
    "as assets: {\"file\": \"Inter-Regular.ttf\", \"bold\": \"Inter-Bold.ttf\", "
    "\"italic\": \"Inter-Italic.ttf\", \"bold_italic\": \"Inter-BoldItalic.ttf\"}. "
    "Only file is required, and a style whose face file is missing renders in "
    "the regular face — nothing is synthesised, so supply the faces the "
    "document actually uses. The files are looked up in asset_dir alone (the "
    "working directory when no asset_dir is set); there is no search chain, "
    "and a file that is not there is an error before rendering starts. A name "
    "is a bare file name ending in .ttf or .otf, with no directory part and no "
    "underscore or other LaTeX special character — rename the file if it has "
    "one. Over klartex serve the faces ride the request's assets map, which "
    "takes at most 10 files of 5 MB each."
)


def _font_forms(name_description: str) -> list[dict]:
    """The two accepted forms of a font setting: a family name, or a file object."""
    return [
        {"type": "string", "description": name_description},
        {
            "type": "object",
            "description": "Font files travelling with the render as assets.",
            "additionalProperties": False,
            "required": ["file"],
            "properties": {
                key: {
                    "type": "string",
                    "pattern": FONT_FILENAME_PATTERN,
                    "description": _FONT_FACE_DESCRIPTIONS[key],
                }
                for key in FONT_FACE_OPTIONS
            },
        },
    ]


def _check_font(key: str, value):
    """Validate one font setting in either form and return it.

    ``None`` means unset. The hand-rolled errors mirror ``_check_margins``:
    ``load_page_template`` is reachable from callers that never ran the JSON
    Schema, so the loader states the contract itself.

    Raises:
        ValueError: If the value is neither a family name nor a well-formed
                    font file object.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        raise ValueError(
            f"page_template.{key} must be a fontspec family name or an object "
            f"naming font files, got {type(value).__name__}"
        )
    unknown = [k for k in value if k not in FONT_FACE_OPTIONS]
    if unknown:
        raise ValueError(
            f"Unknown {key} key(s): {', '.join(unknown)}. "
            f"Allowed: {', '.join(FONT_FACE_OPTIONS)}"
        )
    if not value.get("file"):
        raise ValueError(
            f"page_template.{key} as an object requires 'file' — the regular "
            "face the family is named by."
        )
    for face, filename in value.items():
        if not isinstance(filename, str) or not _FONT_FILENAME_RE.fullmatch(filename):
            raise ValueError(
                f"{key}.{face} must be a font file name ending in .ttf or "
                f".otf, with no directory part and no underscore or other "
                f"LaTeX special character, got {filename!r}"
            )
    return dict(value)


def _fontspec_setup(command: str, value) -> str:
    """The fontspec call selecting ``value`` for ``command``, or empty.

    The file form emits ``Path=./`` — explicitly relative, so the engine
    resolves the faces against its working directory, which the renderer sets
    to the asset root. Face options are emitted only for the faces supplied;
    fontspec then falls back to the regular face for the rest.
    """
    if not value:
        return ""
    if isinstance(value, str):
        return command + "{" + value + "}"
    options = ["Path=./"]
    options += [
        f"{option}={value[face]}"
        for face, option in FONT_FACE_OPTIONS.items()
        if option and value.get(face)
    ]
    return command + "{" + value["file"] + "}[" + ", ".join(options) + "]"


def font_files(spec: dict | None) -> list[str]:
    """Every font face file a ``page_template`` payload references, in
    reference order and without duplicates.

    The renderer preflights these against the asset root before compiling, so
    a face file that never arrived is a named error instead of a fontspec
    failure buried in the TeX log.
    """
    if not isinstance(spec, dict):
        return []
    out: list[str] = []
    for key in ("font", "header_font"):
        value = _check_font(key, spec.get(key))
        if not isinstance(value, dict):
            continue
        for face in FONT_FACE_OPTIONS:
            name = value.get(face)
            if name and name not in out:
                out.append(name)
    return out


# Document-level settings on the page_template object.
DOCUMENT_SETTINGS: dict[str, dict] = {
    "page_numbers": {"type": "boolean", "description": "Show page numbers in the footer"},
    "first_page_header": {"type": "boolean", "description": "Show the header on the first page"},
    "font": {
        "description": (
            "Document font, as a fontspec family name or as font files. These "
            "families are guaranteed to be installed in the render "
            "environment (ghcr.io/swedev/klartex-base): "
            f"{_GUARANTEED_FONTS_TEXT}. Any other family name renders only "
            "where that font happens to be installed on the machine doing the "
            f"rendering. {_FONT_FILE_FORM}"
        ),
        "oneOf": _font_forms(
            "A fontspec family name installed where the rendering happens, "
            "e.g. \"Georgia\"."
        ),
    },
    "header_font": {
        "description": (
            "Font for the header and footer, as a fontspec family name or as "
            "font files — the guaranteed families are the same as for font, "
            "and the file form works the same way. Default: same as font, "
            "in whichever form font was given."
        ),
        "oneOf": _font_forms(
            "A fontspec family name installed where the rendering happens."
        ),
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
    "margins": MARGINS_SETTING,
}


# Header-space reclaim: emitted after both slots, so the \ifdefempty test at
# preamble end sees the final value of the contract macros.
_RECLAIM = r"\geometry{top=\kxreclaimtop, headheight=0pt, headsep=0pt, includehead=false}"
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
    #: True when ``source`` is a whole-page source shared with the other
    #: slot, so the composition emits it once.
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
    font: str | dict | None = None
    header_font: str | dict | None = None
    diff_style: str = "color"
    margins: dict = field(default_factory=dict)

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
    def font_setup(self) -> str:
        """The ``\\setmainfont`` call for the ``font`` setting, empty when unset."""
        return _fontspec_setup(r"\setmainfont", self.font)

    @property
    def header_font_setup(self) -> str:
        """The header font family and the ``\\kxheaderfont`` renewal that
        points the chrome at it, empty when unset."""
        setup = _fontspec_setup(r"\newfontfamily\kxheaderfontfamily", self.header_font)
        if not setup:
            return ""
        return setup + "\n" + r"\renewcommand{\kxheaderfont}{\kxheaderfontfamily}"

    @property
    def margin_setup(self) -> str:
        """The geometry setup for the ``margins`` setting, empty when unset.

        ``top`` is emitted for both top-geometry regimes at once — a headsep
        adjustment for the header that renders, a ``\\kxreclaimtop`` renewal
        for the header whose space is reclaimed — because which one applies is
        decided at LaTeX time, by the reclaim block's ``\\ifdefempty`` tests.
        """
        if not self.margins:
            return ""
        lines: list[str] = []
        keys: list[str] = []
        top = self.margins.get("top")
        if top:
            lines.append(r"\renewcommand{\kxreclaimtop}{" + top + "}")
        bottom = self.margins.get("bottom")
        if bottom:
            # The columns footer enlarges the bottom geometry for its band;
            # these renewals make the user's bottom the value it enlarges to,
            # keeping the band's clearance below the text block.
            lines.append(r"\renewcommand{\kxfooterbottom}{" + bottom + "}")
            lines.append(
                r"\renewcommand{\kxfooterfootskip}{\dimexpr "
                + bottom
                + "-"
                + FOOTER_BAND_CLEARANCE
                + r"\relax}"
            )
        for key in ("left", "right", "bottom"):
            value = self.margins.get(key)
            if value:
                keys.append(f"{key}={value}")
        if top:
            keys.append(r"headsep=\dimexpr " + top + "-" + HEADER_BAND_BOTTOM + r"\relax")
        lines.append(r"\geometry{" + ", ".join(keys) + "}")
        if self.margins.get("left") or self.margins.get("right"):
            # fancyhdr's \headwidth does not track a \textwidth changed after
            # the class loaded it, so the band would keep the old text width.
            lines.append(r"\setlength{\headwidth}{\textwidth}")
        return "\n".join(lines)

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
    page_template_source: str | None = None,
) -> PageTemplate:
    """Resolve a page template from its payload value and any custom sources.

    Args:
        spec: The ``page_template`` object from the payload, or None.
        defaults: Slot values, in payload syntax, for the slots ``spec``
                 leaves out — the rendering surface's own default
                 (``BLOCK_DEFAULT_SLOTS`` when omitted).
        header_source: Raw ``.tex.jinja`` content owning the header slot.
        footer_source: Raw ``.tex.jinja`` content owning the footer slot.
        page_template_source: Raw content owning both slots. In this mode the
                 payload's ``header`` and ``footer`` are not read; the
                 document-level settings still apply.

    Returns:
        Resolved PageTemplate.

    Raises:
        ValueError: If ``spec`` is not an object, a key, variant or setting
                    is unknown, or ``page_template_source`` is combined with
                    a per-slot source.
    """
    if page_template_source is not None and (
        header_source is not None or footer_source is not None
    ):
        raise ValueError(
            "page_template_source owns both slots and cannot be combined "
            "with header_source or footer_source"
        )
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
    font = _check_font("font", overrides.get("font"))
    header_font = _check_font("header_font", overrides.get("header_font")) or font
    diff_style = overrides.get("diff_style") or "color"
    margins = _check_margins(overrides.get("margins"))

    if page_template_source is not None:
        # One source owns both slots, so no chrome is read from the payload.
        header = SlotSpec(source=page_template_source)
        footer = SlotSpec(source=page_template_source, shared_source=True)
    else:
        if header_source is not None:
            header = SlotSpec(source=header_source)
        else:
            header = _resolve_slot(
                "header", overrides.get("header", _MISSING), defaults["header"]
            )

        if footer_source is not None:
            footer = SlotSpec(source=footer_source)
        else:
            footer = _resolve_slot(
                "footer", overrides.get("footer", _MISSING), defaults["footer"]
            )

    page_numbers = overrides.get("page_numbers")
    if page_numbers is None:
        page_numbers = True
    first_page_header = overrides.get("first_page_header")
    if first_page_header is None:
        # A header that puts nothing on the page has nothing to suppress on
        # page one either, so the empty slot defaults this off.
        first_page_header = not header.is_empty

    template = PageTemplate(
        header=header,
        footer=footer,
        page_numbers=page_numbers,
        first_page_header=first_page_header,
        font=font,
        header_font=header_font,
        diff_style=diff_style,
        margins=margins,
    )
    _check_margin_top(template)
    return template


def _check_margin_top(template: PageTemplate) -> None:
    """Reject a ``margins.top`` that leaves no header–text gap.

    Only checked where Python can tell the header will render: a predefined
    variant with content. An empty or content-less header reclaims the header
    space, and a custom source owns its own geometry — both take any positive
    top.
    """
    top = template.margins.get("top")
    if not top or not template.header.is_predefined or not template.header_macros:
        return
    if _to_points(top) <= _to_points(HEADER_BAND_BOTTOM):
        raise ValueError(
            f"margins.top must be greater than {HEADER_BAND_BOTTOM} when the "
            f"header renders — the header band ends there, and {top} leaves no "
            "gap between it and the body text. Use a larger top, or an empty "
            "header (header: null) to reclaim the header's space."
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
