import os
from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    debug = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    print(f"Starting KARE Viva Evaluation System on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=debug)
