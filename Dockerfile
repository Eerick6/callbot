FROM python:3.12-slim

# Instalar uv
RUN pip install uv

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --locked --no-install-project --no-dev

# Copy the application code
COPY ./bot.py bot.py
COPY ./tools.py tools.py
COPY ./observers.py observers.py

# Expose port
EXPOSE 7860

# 🔥 ESTA ES LA CLAVE - Usar ENTRYPOINT + CMD como en tu original
ENTRYPOINT ["uv", "run", "--no-dev", "bot.py"]
CMD ["--transport", "twilio", "--host", "0.0.0.0"]