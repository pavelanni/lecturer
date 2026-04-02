# Lecturer — video lecture generation toolkit
#
# Build:
#   docker build -t lecturer .
#
# Usage:
#   docker run -v ./my-course:/course -e ELEVENLABS_API_KEY=sk_... \
#       lecturer generate-slides
#
# The /course directory should contain:
#   lecturer.toml          — course configuration
#   content/<lecture>/     — lecture artifacts
#   output/               — generated videos (created automatically)
#   themes/               — Marp CSS themes (optional, defaults included)

FROM python:3.12-slim AS base

# Install system dependencies: ffmpeg, Node.js (for Marp CLI)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        chromium \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @marp-team/marp-cli \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /root/.npm

# Tell Marp/Puppeteer where to find Chromium
ENV CHROME_PATH=/usr/bin/chromium
# Run Chromium without sandbox (required in containers)
ENV PUPPETEER_CHROMIUM_REVISION=skip
ENV PUPPETEER_LAUNCH_ARGS="--no-sandbox --disable-gpu --disable-dev-shm-usage"

# Install uv for Python dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set up the application
WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock .python-version README.md ./

# Install Python dependencies (skip mlx-whisper — Apple Silicon only)
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

# Copy application code
COPY src/ src/
COPY themes/ themes/

# Copy shell scripts
COPY generate_slides.sh generate_all_audio.sh build_all_videos.sh concat_videos.sh ./
RUN chmod +x *.sh

# Copy skill files (useful as reference inside the container)
COPY .claude/ .claude/

# The entrypoint script routes commands to the right tool
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Signal to scripts that we're running inside the container
ENV LECTURER_DOCKER=1

# Mount point for course content
VOLUME /course
WORKDIR /course

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["help"]
