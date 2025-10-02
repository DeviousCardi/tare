# Two stages, so the build tools never reach the image we actually ship.
FROM python:3.12-slim AS builder

WORKDIR /build

# The package and what it needs at runtime, installed into a prefix we can
# lift out whole. Nothing from the dev extra comes with it: the image runs the
# service, it does not run the suite.
COPY pyproject.toml ./
COPY tare ./tare
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# The service is the same on any machine at any hour; pin the clock's zone too.
ENV TZ=UTC

COPY --from=builder /install /usr/local
COPY tare ./tare

EXPOSE 8000

CMD ["uvicorn", "tare.main:app", "--host", "0.0.0.0", "--port", "8000"]
