import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from src.hub.router import router as hub_router  # noqa: E402  (env를 먼저 읽어야 함)

app = FastAPI(title="Agent Hub")

# CORS: env CORS_ORIGINS(콤마 구분)이 있을 때만 켠다
if os.getenv("CORS_ORIGINS"):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS").split(","),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

app.include_router(hub_router)

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "0") == "1",
    )
