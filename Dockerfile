# Multi-stage minimal & secure production Dockerfile
FROM python:3.12-alpine AS builder

WORKDIR /app

RUN apk add --no-cache gcc musl-dev libffi-dev

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir build && \
    python -m build --wheel

# Final Stage: Distroless/Minimal Alpine Runner
FROM python:3.12-alpine AS runner

WORKDIR /app

# SRE Best Practice: Run as non-root user
RUN addgroup -g 10001 fleetmate && \
    adduser -u 10001 -G fleetmate -s /bin/sh -D fleetmate

COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl

USER 10001:10001

EXPOSE 8089 9090

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9090/metrics')" || exit 1

ENTRYPOINT ["fleetmate"]
CMD ["start"]
