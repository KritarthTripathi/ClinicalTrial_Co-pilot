#!/bin/sh
# Builds an offline bundle so the stack can be rebuilt on an air-gapped host.
# Run on a connected machine AFTER `docker compose build` and `--profile setup up ollama-setup`.
set -e
mkdir -p bundle/wheels
docker save -o bundle/images.tar zerobytes-app ollama/ollama:latest arizephoenix/phoenix:latest alpine/socat
docker run --rm -v zerobytes_ollama_models:/m -v "$PWD/bundle":/b alpine tar czf /b/ollama_models.tgz -C /m .
pip download -r requirements.txt -d bundle/wheels
cp -r docker-compose.yml docker-compose.gpu.yml .env.example Dockerfile requirements.txt src scripts bundle/ 2>/dev/null || true
(cd bundle && find . -type f -exec sha256sum {} \; > SHA256SUMS)
echo "bundle/ ready. Restore on target: docker load -i images.tar; restore ollama_models volume; docker compose up -d"
