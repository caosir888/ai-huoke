from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_huoke"
    REDIS_URL: str = "redis://localhost:6379/0"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "ai-huoke"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    ALIYUN_ACCESS_KEY: str = ""
    ALIYUN_SECRET_KEY: str = ""
    DOUYIN_CLIENT_KEY: str = ""
    DOUYIN_CLIENT_SECRET: str = ""
    DOUYIN_REDIRECT_URI: str = "http://localhost:8000/platform/oauth/douyin/callback"
    DOUYIN_OAUTH_SCOPE: str = "user_info"
    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()
