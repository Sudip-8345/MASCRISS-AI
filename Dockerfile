FROM python:3.12-slim

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip

# Copy full project source
COPY . .

# Install project dependencies from pyproject.toml
RUN pip install --no-cache-dir .

# Pre-create output directory
RUN mkdir -p output

# Runtime configuration (non-secret)
ENV AGENT_MAX_ITER="3"

CMD ["python", "main.py"]
