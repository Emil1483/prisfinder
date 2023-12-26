import os

from dotenv import load_dotenv

from src.services.redis_service import RedisService


load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis: RedisService = RedisService.from_url(REDIS_URL)
