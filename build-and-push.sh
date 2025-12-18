#!/bin/bash

# Build and push ML Gateway Docker image

# Configuration
IMAGE_NAME="pragyaa-ai/ml-gateway"
TAG="latest"
FULL_IMAGE="${IMAGE_NAME}:${TAG}"

echo "🏗️  Building Docker image: ${FULL_IMAGE}"

# Build the image
docker build -t "${FULL_IMAGE}" .

if [ $? -eq 0 ]; then
    echo "✅ Image built successfully!"

    # Check if user wants to push to registry
    read -p "Do you want to push to Docker registry? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 Pushing image to registry..."
        docker push "${FULL_IMAGE}"

        if [ $? -eq 0 ]; then
            echo "✅ Image pushed successfully!"
            echo ""
            echo "📋 To run on your VM:"
            echo "docker run -d \\"
            echo "  --name ml-gateway \\"
            echo "  -p 8000:8000 \\"
            echo "  -p 9200:9200 \\"
            echo "  -p 9600:9600 \\"
            echo "  -v opensearch-data:/usr/share/opensearch/data \\"
            echo "  ${FULL_IMAGE}"
        else
            echo "❌ Failed to push image"
        fi
    else
        echo "📦 Image ready locally. To push later:"
        echo "docker push ${FULL_IMAGE}"
        echo ""
        echo "📋 To run locally:"
        echo "docker run -d --name ml-gateway -p 8000:8000 -p 9200:9200 -p 9600:9600 ${FULL_IMAGE}"
    fi
else
    echo "❌ Failed to build image"
    exit 1
fi