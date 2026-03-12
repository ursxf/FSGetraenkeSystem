"""Application entry point.

Run locally with:
    python run.py

Or with gunicorn:
    gunicorn "run:app"
"""

from dotenv import load_dotenv

load_dotenv()  # Load .env file if present (useful for Windows and local development)

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
