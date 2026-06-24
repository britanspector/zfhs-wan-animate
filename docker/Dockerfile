# syntax=docker/dockerfile:1
# Build from zfhs-wan-animate repo root:
#   bash scripts/prepare_docker_build.sh
#   docker build -f docker/Dockerfile -t zfhs-wan-animate:latest .

ARG COMFYUI_REF=v0.25.0

FROM node:22-alpine AS web-builder
WORKDIR /build
COPY wan-animate-web/package.json wan-animate-web/package-lock.json ./
RUN npm ci
COPY wan-animate-web/ ./
RUN npm run build

FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04 AS runtime

ARG COMFYUI_REF
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    COMFYUI_ROOT=/app/ComfyUI \
    COMFYUI_URL=http://127.0.0.1:6006 \
    COMFY_PYTHON=/opt/venv/bin/python \
    WAN_ANIMATE_DATA_DIR=/app/data \
    WAN_ANIMATE_JOBS_PATH=/app/data/jobs.json \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    ffmpeg \
    lsof \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip wheel setuptools

RUN /opt/venv/bin/pip install --no-cache-dir \
    torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu128

WORKDIR /app

RUN git clone --depth 1 --branch "${COMFYUI_REF}" https://github.com/comfyanonymous/ComfyUI.git /app/ComfyUI

COPY docker/requirements-comfy.txt /tmp/requirements-comfy.txt
COPY requirements.txt /tmp/requirements-app.txt

RUN /opt/venv/bin/pip install --no-cache-dir -r /app/ComfyUI/requirements.txt \
    && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements-comfy.txt \
    && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements-app.txt

COPY docker/vendor/custom_nodes/ /app/ComfyUI/custom_nodes/

COPY docker/patches/onnx_models.py \
    /app/ComfyUI/custom_nodes/ComfyUI-WanAnimatePreprocess/models/onnx_models.py

COPY . /app/zfhs-wan-animate/
COPY --from=web-builder /build/dist /app/zfhs-wan-animate/wan-animate-web/dist

COPY docker/entrypoint.sh /app/docker/entrypoint.sh
COPY docker/healthcheck.sh /app/docker/healthcheck.sh
RUN chmod +x /app/docker/entrypoint.sh /app/docker/healthcheck.sh

RUN mkdir -p /app/ComfyUI/models /app/ComfyUI/input /app/ComfyUI/output /app/data

WORKDIR /app/zfhs-wan-animate

EXPOSE 6020

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD ["/app/docker/healthcheck.sh"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]
