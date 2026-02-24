FROM python:3.12-slim

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip

# Copy dependency file first (better layer caching)
COPY pyproject.toml .

# Install project dependencies
RUN pip install --no-cache-dir .

# Copy project source
COPY . .

# Pre-create output directory
RUN mkdir -p output

# Environment variables (override at runtime via docker run -e or .env)
ENV GROQ_API_KEY=""
ENV SERPER_API_KEY=""
ENV OPENWEATHER_API_KEY=""
ENV SERPAPI_API_KEY="4bc21397fb18334ebfb25246a8e163a8180c6b4295f54afe22fb6768b35a4b74"

CMD ["python", "main.py"]
