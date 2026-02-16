% klartex-base.cls - Klartex Document Base Class
% Generalized from wingframe.cls for branded document generation
% https://github.com/swedev/klartex

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{klartex-base}[2026/02/16 Klartex Document Base Class]

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
\tolerance=2000
\emergencystretch=2em
\hbadness=2000

% Font setup — Lato as default, loaded from assets/fonts/
\newcommand{\fontpath}{fonts/}
\setmainfont{Lato}[
    Path = \fontpath,
    Extension = .ttf,
    UprightFont = *-Reg,
    BoldFont = *-Bol,
    ItalicFont = *-RegIta,
    BoldItalicFont = *-BolIta
]

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
\newcommand{\setdoclang}[1]{\renewcommand{\wf@lang}{#1}}

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

% Path to assets
\graphicspath{{assets/}{../assets/}{./}}

% Header and footer setup
\pagestyle{fancy}
\fancyhf{}

% Header — org info on left, logo on right (skip if no branding)
\fancyhead[L]{%
    \ifdefempty{\orgname}{}{%
    \color{brandsecondary}%
    \begin{minipage}[t]{0.20\textwidth}
        \fontsize{6pt}{9pt}\selectfont
        \textbf{\orgname}%
        \ifdefempty{\orgaddress}{}{\\
        \orgaddress}%
    \end{minipage}%
    \begin{minipage}[t]{0.22\textwidth}
        \fontsize{6pt}{9pt}\selectfont
        \orgwebsite%
        \ifdefempty{\orgemail}{}{\\
        \orgemail}%
        \ifdefempty{\orgphone}{}{\\
        \orgphone}%
    \end{minipage}%
    }%
}
\fancyhead[R]{%
    \ifdefempty{\brandlogo}{}{%
        \raisebox{-0.6cm}[0pt][0pt]{\includegraphics[height=0.855cm]{\brandlogo}}%
    }%
}

% Footer — document title and page number (language-aware)
\fancyfoot[C]{%
    \wf@setlang%
    \fontsize{6pt}{9pt}\selectfont\color{brandsecondary}%
    \doctitle\ \textbullet\ \wf@page\ \thepage\ \wf@of\ \pageref{LastPage}%
}

% Header/footer rules
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

% Legal clause numbering
\newcounter{clausecounter}
\newcounter{subclausecounter}[clausecounter]

\newlist{clauses}{enumerate}{1}
\setlist[clauses]{
    label=\textbf{\arabic{clausecounter}.},
    ref=\arabic{clausecounter},
    leftmargin=1.0cm,
    labelwidth=0.76cm,
    labelsep=0.24cm,
    itemindent=0pt,
    align=left,
    before=\setcounter{clausecounter}{0},
    itemsep=20pt,
    parsep=0pt,
    topsep=12pt
}
\newcommand{\clause}[1]{\stepcounter{clausecounter}\item \textbf{#1}}

\newlist{subclauses}{enumerate}{1}
\setlist[subclauses]{
    label=\arabic{clausecounter}.\arabic*.,
    ref=\arabic{clausecounter}.\arabic*,
    leftmargin=0pt,
    labelwidth=0.76cm,
    labelsep=0.24cm,
    itemindent=0pt,
    align=left,
    itemsep=0.5em,
    parsep=0pt,
    topsep=0.5em
}

% Hyperlink setup
\hypersetup{
    colorlinks=true,
    linkcolor=brandprimary,
    urlcolor=brandprimary,
}

% Title page command (language-aware)
\newcommand{\makedoctitle}[3]{%
    \wf@setlang%
    \begin{center}
        \vspace*{4cm}
        {\Large\bfseries #1}\\[1em]
        \wf@and\\[1em]
        {\Large\bfseries #2}\\[4cm]
        {\LARGE\bfseries #3}
    \end{center}
    \thispagestyle{fancy}
    \newpage
}

% Dotted line for signatures
\newcommand{\dottedline}[1][6cm]{\makebox[#1]{\dotfill}}

% Signature block (language-aware)
\newcommand{\signatureblock}[4]{%
    \wf@setlang%
    \clearpage
    \section*{\wf@signatures}
    \addcontentsline{toc}{section}{\wf@signatures}

    \wf@sigintro

    \vspace{1.5cm}

    \noindent
    \begin{minipage}[t]{0.45\textwidth}
        \textbf{#1}\\[0.5cm]
        \wf@locationdate\\[1cm]
        \dottedline\\[0.5cm]
        \wf@signature\\[1cm]
        \dottedline\\[0.3cm]
        #3
    \end{minipage}%
    \hfill
    \begin{minipage}[t]{0.45\textwidth}
        \textbf{#2}\\[0.5cm]
        \wf@locationdate\\[1cm]
        \dottedline\\[0.5cm]
        \wf@signature\\[1cm]
        \dottedline\\[0.3cm]
        #4
    \end{minipage}
}

\endinput
