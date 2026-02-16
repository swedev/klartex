FROM texlive/texlive:latest-minimal AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN tlmgr install xetex fontspec fancyhdr geometry xcolor titlesec enumitem \
    lastpage hyperref parskip setspace etoolbox booktabs tabularx collection-fontsrecommended

WORKDIR /app
COPY . .

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir .

ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8000

CMD ["klartex", "serve", "--host", "0.0.0.0", "--port", "8000"]
