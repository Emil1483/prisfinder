import os

from src.services.redis_service import RedisService


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis: RedisService = RedisService.from_url(REDIS_URL)
