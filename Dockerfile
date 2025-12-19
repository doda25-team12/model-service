# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.12.9

# ------------------------------
# 1 - Builder stage: install deps into venv
# ------------------------------
FROM --platform=$BUILDPLATFORM python:${PYTHON_VERSION}-slim AS builder
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /app

# Build tooling stays in builder only
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    libpng-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY model-service/requirements.txt .
RUN python -m venv "$VIRTUAL_ENV" \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ------------------------------
# 2 - Runtime stage: slimmer image
# ------------------------------
FROM python:${PYTHON_VERSION}-slim
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /app

# Only runtime libs; no compilers
RUN apt-get update && apt-get install -y --no-install-recommends \
    libatlas-base-dev \
    libblas-dev \
    liblapack-dev \
    libpng-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY model-service/ .

# Ensure a versioned model filename exists for the default deployment (uses 'latest')
# so the runtime can find `model-<VERSION>.joblib` when MODEL_VERSION=latest.
RUN if [ -f output/model.joblib ]; then cp output/model.joblib output/model-latest.joblib || true; fi

# Set environment variable with default
ENV MODEL_SERVICE_PORT=8081

# Expose default port (configurable via MODEL_SERVICE_PORT env variable)
EXPOSE ${MODEL_SERVICE_PORT}

CMD ["python", "src/serve_model.py"]
