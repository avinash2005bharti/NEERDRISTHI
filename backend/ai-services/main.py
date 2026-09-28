import os
import sys
from pathlib import Path
import uvicorn

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from app.config import settings
    default_port = settings.effective_port
except Exception:
    default_port = 8000

if __name__ == "__main__":
    port = int(os.environ.get("PORT", default_port))
    print(f"Starting ORCA AI Services (FastAPI) on 0.0.0.0:{port} ...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

