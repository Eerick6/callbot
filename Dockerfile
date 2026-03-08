FROM dailyco/pipecat-base:latest

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies - SIN mounts problemáticos para Render
RUN uv sync --locked --no-install-project --no-dev

# Copy the application code
COPY ./bot.py bot.py
COPY ./tools.py tools.py
COPY ./observers.py observers.py

# Expose port
EXPOSE 7860

# Usar variable de entorno PORT (Render la asigna, local usa 7860 por defecto)
CMD uv run --no-dev bot.py --transport twilio --host 0.0.0.0 --port ${PORT:-7860}