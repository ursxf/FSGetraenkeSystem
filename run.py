"""Application entry point.

Run locally with:
    python run.py

Or with gunicorn:
    gunicorn "run:app"
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
