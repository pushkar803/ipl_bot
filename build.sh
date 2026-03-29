#!/usr/bin/env bash
set -euo pipefail

echo "══════════════════════════════════════════"
echo "  Cricket Predictor — Production Build"
echo "══════════════════════════════════════════"

# 1. Install Python deps
echo ""
echo "→ Installing Python dependencies..."
pip install -q -r requirements.txt

# 2. Install Node deps (for CSS build)
if ! command -v npm &>/dev/null; then
    echo "✗ npm not found. Install Node.js to build CSS."
    exit 1
fi

echo "→ Installing Node dependencies..."
npm ci --silent 2>/dev/null || npm install --silent

# 3. Build minified CSS
echo "→ Building production CSS..."
npm run build:css

# 4. Download HTMX if missing
if [ ! -f static/js/htmx.min.js ]; then
    echo "→ Downloading HTMX..."
    mkdir -p static/js
    curl -sL https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js -o static/js/htmx.min.js
fi

# 5. Summary
CSS_SIZE=$(wc -c < static/css/style.min.css | tr -d ' ')
JS_SIZE=$(wc -c < static/js/htmx.min.js | tr -d ' ')

echo ""
echo "✓ Build complete!"
echo "  CSS: static/css/style.min.css (${CSS_SIZE} bytes)"
echo "  JS:  static/js/htmx.min.js   (${JS_SIZE} bytes)"
echo ""
echo "Run locally:"
echo "  FLASK_ENV=development python web.py"
echo ""
echo "Run production:"
echo "  gunicorn web:app --bind 0.0.0.0:5050"
echo ""
