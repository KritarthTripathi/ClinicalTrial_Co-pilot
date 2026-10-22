FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app/src HF_HUB_OFFLINE=1 LANGCHAIN_TRACING_V2=false
WORKDIR /app
COPY requirements.txt .
# Build-time only: needs internet. Runtime containers have none.
RUN pip install --no-cache-dir -r requirements.txt \
 && python -m spacy download en_core_web_lg
COPY src ./src
COPY scripts ./scripts
COPY tests ./tests
CMD ["python", "-m", "app.main", "--help"]
