FROM python:3.12-slim

# System deps: Node.js (for claude CLI) + DejaVu fonts (for QA screenshots)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        fonts-dejavu-core \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI (uses Max subscription — no API key needed)
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# /projects is the mount point for external projects to fix
VOLUME ["/projects"]

CMD ["python", "main.py"]
