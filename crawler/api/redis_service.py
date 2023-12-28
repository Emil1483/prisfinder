from src.services.redis_service import RedisService


redis = RedisService.from_env_url()
