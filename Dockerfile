# ── Stage 1: Build CSS ──────────────────────────────────
FROM node:18-alpine AS css-builder
WORKDIR /build
COPY package.json package-lock.json* tailwind.config.js ./
COPY static/src/ static/src/
COPY templates/ templates/
RUN npm ci --silent && npm run build:css

# ── Stage 2: Production Python app ─────────────────────
FROM python:3.12-slim
WORKDIR /app

RUN adduser --disabled-password --no-create-home app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY --from=css-builder /build/static/css/style.min.css static/css/style.min.css

RUN chown -R app:app /app
USER app

ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE 5050

CMD ["gunicorn", "web:app", "--bind", "0.0.0.0:5050", "--workers", "2", "--timeout", "120"]
