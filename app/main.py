"""tax-return-ai — FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="tax-return-ai",
    description=(
        "Australian individual tax-ready data generator. "
        "This tool organises tax documents and prepares a review package. "
        "It does not provide final tax advice, lodge returns, or replace a registered tax agent."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "product": "tax-return-ai", "advice": "none provided"}
