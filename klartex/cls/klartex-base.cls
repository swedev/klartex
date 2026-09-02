% klartex-base.cls - Klartex Document Base Class
% https://github.com/swedev/klartex

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{klartex-base}[2026/02/18 Klartex Document Base Class]

% Base class
\LoadClass[10pt,a4paper]{article}

% Margin profile. The `narrowmargins` class option opts a document type
% into the tighter business-document geometry (2cm side margins, 1.7cm
% reclaimed top — used by faktura/kvitto); everything else keeps the
% defaults.
\newcommand{\kxsidemargin}{3cm}
\newcommand{\kxreclaimtop}{2cm}
% Bottom geometry the multi-column footer (klartex-footer) enlarges to for
% its band. Bound here so a page template's bottom margin can renew them
% before that package loads.
\newcommand{\kxfooterbottom}{3.6cm}
\newcommand{\kxfooterfootskip}{2.6cm}
\DeclareOption{narrowmargins}{%
    \renewcommand{\kxsidemargin}{2cm}%
    \renewcommand{\kxreclaimtop}{1.7cm}%
}
\ProcessOptions\relax

% Required packages
\RequirePackage{fontspec}
\RequirePackage[
    left=\kxsidemargin,
    right=\kxsidemargin,
    top=0.9cm,
    bottom=2cm,
    includehead,
    headheight=1.2cm,
    headsep=1.3cm,
    footskip=1cm
]{geometry}
\RequirePackage{graphicx}
\RequirePackage{fancyhdr}
\RequirePackage{xcolor}
\RequirePackage{titlesec}
\RequirePackage{enumitem}
\RequirePackage{lastpage}
\RequirePackage{hyperref}
\RequirePackage{parskip}
\RequirePackage{setspace}
\RequirePackage{tabularx}
\RequirePackage{booktabs}

% Inline implementation of \kxneedspace{<dim>} matching needspace.sty's
% default (non-starred) behavior: a glue-trick that inserts removable +/-
% rubber glue around a -100 penalty so the page break is taken near the
% penalty when less than <dim> remains. Soft — TeX may stretch slightly to
% fit when conditions are close. Avoid \pagegoal/\pagetotal hard checks; in
% the block engine those interact badly with consecutive clauses by
% triggering forced breaks that strand single items on otherwise empty pages.
\newcommand{\kxneedspace}[1]{%
    \begingroup
    \setlength{\dimen@}{#1}%
    \vskip\z@\@plus\dimen@
    \penalty-100
    \vskip\z@\@plus-\dimen@
    \endgroup
    \vskip\z@\@plus\z@
}

% Set line spacing
\setstretch{1.3}

% Prefer line breaks over tight word spacing
\tolerance=800
\emergencystretch=3em
\hbadness=800

% Forbid 1- and 2-line widows (last lines of a paragraph alone on a new page)
% and orphans (first lines of a paragraph alone at the bottom of a page).
% The terminating 0 is required: eTeX clamps the line index to the array
% length, so the last value applies to every remaining line. Without it the
% 10000 repeats through the whole paragraph, forbidding every interline break
% — a paragraph longer than a page then cannot break and is clipped at the
% bottom margin (overfull \vbox, no error, content silently lost).
\widowpenalties 3 10000 10000 0
\clubpenalties 3 10000 10000 0

% Font — no default override; fontspec uses Latin Modern automatically.
% Page templates can set a custom font via \setmainfont in the preamble.

% Brand colors — configurable via \definecolor in document preamble
\definecolor{brandprimary}{HTML}{000000}
\definecolor{brandsecondary}{HTML}{000000}
\definecolor{brandaccent}{HTML}{0066CC}

% Muted grey for placeholder text — a remark about what is missing, not
% content. Redefinable like the brand colors.
\definecolor{kxmuted}{HTML}{6B6A63}

% Label mode for the columns footer: true names an empty column's gap
% instead of dropping the column. Declared here, not in klartex-footer.sty,
% so the meta-template can set it without knowing whether that package is
% loaded.
\newif\ifkxfooterlabelmissing

% Header/footer font hook — a no-op by default so header and footer follow
% the main font. Redefined (e.g. to a \newfontfamily switch) when a page
% template or the header_font page-template option selects a separate font.
\newcommand{\kxheaderfont}{}

% Page-template contract macros. A page-template slot — predefined or custom,
% either render path — redefines these at preamble top level. The predefined
% header fragments read them at shipout; the header-space reclaim block tests
% \orgname and \brandlogo at the end of the preamble, so a definition made
% later (e.g. inside \AtBeginDocument) is not seen by that test.
\providecommand{\orgname}{}
\providecommand{\orgaddress}{}
\providecommand{\orgwebsite}{}
\providecommand{\orgemail}{}
\providecommand{\orgphone}{}
\providecommand{\brandlogo}{}

% Stacked contact lines for a header column. \kx@hdrline skips an empty macro
% and emits the line separator only between lines that actually render, so a
% column whose leading fields are empty does not start with a \\ (which would
% raise "There's no line here to end"). \kx@hdrsepfalse resets the state at
% the top of each column; the flag is set inside the column's group, so
% columns do not affect each other.
\newif\ifkx@hdrsep
\newcommand{\kx@hdrline}[1]{\ifdefempty{#1}{}{\ifkx@hdrsep\\\fi#1\kx@hdrseptrue}}

% Document metadata
\newcommand{\doctitle}{}
\newcommand{\setdoctitle}[1]{\renewcommand{\doctitle}{#1}}

% Language support (default: Swedish)
\newcommand{\kx@lang}{sv}
\newcommand{\setdoclang}[1]{\renewcommand{\kx@lang}{#1}\kx@setlang}

% Language-dependent strings
\newcommand{\kx@and}{Och}
\newcommand{\kx@page}{Sida}
\newcommand{\kx@of}{av}
\newcommand{\kx@signatures}{Underskrifter}
\newcommand{\kx@sigintro}{Detta avtal har upprättats i två (2) likalydande exemplar, av vilka parterna tagit var sitt.}
\newcommand{\kx@locationdate}{Ort och datum}
\newcommand{\kx@signature}{Underskrift}

\newcommand{\kx@lang@en}{en}
\newcommand{\kx@setlang}{%
    \ifx\kx@lang\kx@lang@en
        \renewcommand{\kx@and}{And}%
        \renewcommand{\kx@page}{Page}%
        \renewcommand{\kx@of}{of}%
        \renewcommand{\kx@signatures}{Signatures}%
        \renewcommand{\kx@sigintro}{This Agreement has been executed in two (2) original copies of which the parties have kept one each.}%
        \renewcommand{\kx@locationdate}{Location and Date}%
        \renewcommand{\kx@signature}{Signature}%
    \fi
}

% Graphics search path
\graphicspath{{./}}

% Header and footer setup — layout is injected via page template
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

% Section formatting
\titleformat{\section}
    {\fontsize{14pt}{17pt}\selectfont\bfseries}
    {\thesection.}{0.5em}{}

\titleformat{\subsection}
    {\normalfont\normalsize}
    {\thesubsection.}{0.5em}{}

\titlespacing*{\section}{0pt}{20pt}{12pt}
\titlespacing*{\subsection}{0pt}{0.75em}{0.25em}

% List formatting
\setlist[enumerate]{leftmargin=*, labelsep=0.5em}
\setlist[itemize]{leftmargin=*, labelsep=0.5em}

% Scratch lengths used by clause rendering. \kxgrouplabelw holds the maximum
% rendered label width across a sibling group of clauses; \kxtempdim is a
% temporary register used by the pre-pass that computes that maximum via
% \settowidth + \ifdim.
\newlength{\kxgrouplabelw}
\newlength{\kxtempdim}

% Hyperlink setup
\hypersetup{
    colorlinks=true,
    linkcolor=brandprimary,
    urlcolor=brandprimary,
}

% Fieldset-style box (like HTML <fieldset> with <legend>)
% Usage: \fieldset[group]{Label}{Content}
% Optional group name — boxes in the same group get equal height.
\RequirePackage[most]{tcolorbox}
\newcommand{\fieldset}[3][]{%
    \begin{tcolorbox}[
        enhanced,
        title={\small\textbf{#2}},
        attach boxed title to top left={xshift=0.6em, yshift=-\tcboxedtitleheight/2},
        boxed title style={colback=white, frame hidden, size=small},
        colback=white,
        colframe=black!50,
        coltitle=black,
        boxrule=0.6pt,
        arc=4pt,
        top=1.6em,
        bottom=1.2em,
        left=1.2em,
        right=1.2em,
        equal height group/.expand once={#1}
    ]
    #3
    \end{tcolorbox}%
}

% Load extracted components
% These .sty files use \providecommand so the language strings
% defined above take precedence (no redefinition conflicts).
\RequirePackage{klartex-titelsida}
\RequirePackage{klartex-signatureblock}
\RequirePackage{klartex-agenda}
\RequirePackage{klartex-name-roster}
\RequirePackage{klartex-numformat}
\RequirePackage{klartex-resultatrakning}
\RequirePackage{klartex-budgettabell}
\RequirePackage{klartex-notapparat}
\RequirePackage{klartex-callout}
\RequirePackage{klartex-changes}

\endinput
