FROM python:3.11-slim

# Install system dependencies for OpenSearch
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install OpenSearch
RUN wget -qO - https://artifacts.opensearch.org/publickeys/opensearch.pgp | apt-key add - && \
    echo "deb https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/apt stable main" | tee /etc/apt/sources.list.d/opensearch-2.x.list && \
    apt-get update && apt-get install -y opensearch=2.11.0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p config templates logs /usr/share/opensearch/data

# Configure OpenSearch
RUN chown -R opensearch:opensearch /usr/share/opensearch/data

# Expose ports (gateway and OpenSearch)
EXPOSE 8000 9200 9600

# Health check for gateway
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start OpenSearch and then the gateway
COPY start-with-opensearch.sh /app/start-with-opensearch.sh
RUN chmod +x /app/start-with-opensearch.sh

CMD ["/app/start-with-opensearch.sh"]
