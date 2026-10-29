# Test image only; never referenced by Render.
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace/macro-dashboard
COPY requirements.txt requirements.txt
COPY backend/requirements.txt backend/requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt -r backend/requirements.txt && python -m pip freeze > /runtime-packages.txt
COPY backend/app backend/app
COPY macro_engine macro_engine
COPY scripts scripts
CMD ["python", "scripts/validate_phase4c.py"]

