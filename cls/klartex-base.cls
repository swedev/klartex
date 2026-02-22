% klartex-base.cls - Klartex Document Base Class
% Generalized from wingframe.cls for branded document generation
% https://github.com/swedev/klartex

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{klartex-base}[2026/02/18 Klartex Document Base Class]

% Base class
\LoadClass[10pt,a4paper]{article}

% Required packages
\RequirePackage{fontspec}
\RequirePackage[
    left=3cm,
    right=3cm,
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

% Set line spacing
\setstretch{1.3}

% Prefer line breaks over tight word spacing
\tolerance=800
\emergencystretch=3em
\hbadness=800

% Font — no default override; fontspec uses Latin Modern automatically.
% Branding can set a custom font via \setmainfont in the preamble.

% Brand colors — configurable via \definecolor in document preamble
\definecolor{brandprimary}{HTML}{1A1A1A}
\definecolor{brandsecondary}{HTML}{666666}
\definecolor{brandaccent}{HTML}{0066CC}

% Organization information — set via \renewcommand in document
\newcommand{\orgname}{}
\newcommand{\orgaddress}{}
\newcommand{\orgwebsite}{}
\newcommand{\orgemail}{}
\newcommand{\orgphone}{}
\newcommand{\orgnumber}{}
\newcommand{\brandlogo}{}

% Document metadata
\newcommand{\doctitle}{}
\newcommand{\setdoctitle}[1]{\renewcommand{\doctitle}{#1}}

% Language support (default: Swedish)
\newcommand{\wf@lang}{sv}
\newcommand{\setdoclang}[1]{\renewcommand{\wf@lang}{#1}\wf@setlang}

% Language-dependent strings
\newcommand{\wf@and}{Och}
\newcommand{\wf@page}{Sida}
\newcommand{\wf@of}{av}
\newcommand{\wf@signatures}{Underskrifter}
\newcommand{\wf@sigintro}{Detta avtal har upprättats i två (2) likalydande exemplar, av vilka parterna tagit var sitt.}
\newcommand{\wf@locationdate}{Ort och datum}
\newcommand{\wf@signature}{Underskrift}

\newcommand{\wf@lang@en}{en}
\newcommand{\wf@setlang}{%
    \ifx\wf@lang\wf@lang@en
        \renewcommand{\wf@and}{And}%
        \renewcommand{\wf@page}{Page}%
        \renewcommand{\wf@of}{of}%
        \renewcommand{\wf@signatures}{Signatures}%
        \renewcommand{\wf@sigintro}{This Agreement has been executed in two (2) original copies of which the parties have kept one each.}%
        \renewcommand{\wf@locationdate}{Location and Date}%
        \renewcommand{\wf@signature}{Signature}%
    \fi
}

% Graphics search path
\graphicspath{{./}}

% Header and footer setup — layout is injected via branding preamble
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

% Hyperlink setup
\hypersetup{
    colorlinks=true,
    linkcolor=brandprimary,
    urlcolor=brandprimary,
}

% Fieldset-style box (like HTML <fieldset> with <legend>)
% Usage: \fieldset{Label}{Content}
\RequirePackage[most]{tcolorbox}
\newcommand{\fieldset}[2]{%
    \begin{tcolorbox}[
        enhanced,
        title={\small\textbf{#1}},
        attach boxed title to top left={xshift=0.6em, yshift=-\tcboxedtitleheight/2},
        boxed title style={colback=white, frame hidden, size=small},
        colback=white,
        colframe=black!20,
        coltitle=black,
        boxrule=0.4pt,
        arc=4pt,
        top=1.6em,
        bottom=1.2em,
        left=1.2em,
        right=1.2em
    ]
    #2
    \end{tcolorbox}%
}

% Load extracted components
% These .sty files use \providecommand so the language strings
% defined above take precedence (no redefinition conflicts).
\RequirePackage{klartex-klausuler}
\RequirePackage{klartex-titelsida}
\RequirePackage{klartex-signaturblock}

\endinput
