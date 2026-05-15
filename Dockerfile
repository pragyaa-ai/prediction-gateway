FROM python:3.11-slim

# System deps: curl for healthcheck probes, libgomp1 required by XGBoost,
# build-essential for packages that compile C extensions.
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    libgomp1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install OpenSearch (for audit/request logging). Safe to skip if not needed –
# the gateway falls back gracefully when OpenSearch is unreachable.
RUN wget -qO - https://artifacts.opensearch.org/publickeys/opensearch.pgp | apt-key add - && \
    echo "deb https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/apt stable main" \
        | tee /etc/apt/sources.list.d/opensearch-2.x.list && \
    apt-get update && apt-get install -y opensearch=2.11.0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer is cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source (respects .dockerignore)
COPY . .

# Ensure the local-models directory exists even if not committed
RUN mkdir -p models/local-models

# Ensure log and template directories exist
RUN mkdir -p logs templates config

# OpenSearch data directory ownership
RUN chown -R opensearch:opensearch /usr/share/opensearch/data 2>/dev/null || true

EXPOSE 8000 9200 9600

# Give local Azure AutoML models enough time to deserialize before the
# health check starts failing (first cold-load can take 30-60 s).
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

COPY start-with-opensearch.sh /app/start-with-opensearch.sh
RUN chmod +x /app/start-with-opensearch.sh

CMD ["/app/start-with-opensearch.sh"]
