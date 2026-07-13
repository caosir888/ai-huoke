from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, content, publish, platform, payment, quota, feedback

app = FastAPI(title="AI获客", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(content.router)
app.include_router(publish.router)
app.include_router(platform.router)
app.include_router(payment.router)
app.include_router(quota.router)
app.include_router(feedback.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
