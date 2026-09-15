FROM python:3.13-slim@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MPLCONFIGDIR=/tmp/matplotlib

RUN python -m pip install --no-cache-dir numpy==2.3.3 pandas==2.3.3 babypandas==1.0.0
WORKDIR /app
COPY worker.py /app/worker.py
USER 65534:65534
ENTRYPOINT ["python", "/app/worker.py"]
