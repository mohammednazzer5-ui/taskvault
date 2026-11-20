FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE=/data/app.sqlite

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY manage.py run.py ./

# Run as a non-root user; /data holds the SQLite file (mount a volume here)
RUN useradd --create-home appuser && mkdir /data && chown appuser /data
USER appuser
VOLUME /data

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app:create_app()"]
