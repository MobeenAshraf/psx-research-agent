FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY pyproject.toml ./

# Install Python dependencies using pip (simple and reliable)
# Removed: pdfplumber, openai, langchain, langchain-community, numpy (unused)
RUN pip install --no-cache-dir \
    fastapi>=0.100.0 \
    "uvicorn[standard]>=0.23.0" \
    requests>=2.31.0 \
    beautifulsoup4>=4.12.0 \
    pandas>=1.5.0 \
    langchain-core>=1.0.0 \
    langgraph>=1.0.0 \
    python-dotenv>=1.0.0

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/financial_statements data/results

# Set PYTHONPATH so Python can find the modules
ENV PYTHONPATH=/app

EXPOSE 8080

# Run uvicorn directly
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
