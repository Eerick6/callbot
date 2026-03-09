FROM python:3.12-slim

RUN pip install uv

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY ./app.py app.py
COPY ./bot.py bot.py
COPY ./tools.py tools.py
COPY ./observers.py observers.py

EXPOSE 7860

CMD ["uv", "run", "--no-dev", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]