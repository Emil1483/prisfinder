from datetime import timedelta
from typing import Any
from redis import Redis
from redis.client import Pipeline


class CustomRedis(Redis):
    def __init__(self, *args, **kwargs):
        self.cache = {}
        return super().__init__(*args, **kwargs)

    def get(self, name: str, use_cache=False) -> Any | None:
        if use_cache and name in self.cache:
            return self.cache[name]

        result = super().get(name)
        self.cache[name] = result
        return result

    def set(
        self,
        name: str,
        value: str,
        ex: float | timedelta | None = None,
        px: float | timedelta | None = None,
        nx: bool = False,
        xx: bool = False,
        keepttl: bool = False,
        get: bool = False,
        **kwargs,
    ) -> bool | None:
        self.cache[name] = value
        return super().set(name, value, ex, px, nx, xx, keepttl, get, **kwargs)

    def pipeline(self, transaction: bool = True, shard_hint: Any = None) -> Pipeline:
        return CustomPipeline(
            self.connection_pool, self.response_callbacks, transaction, shard_hint, self
        )


class CustomPipeline(Pipeline):
    def __init__(
        self,
        connection_pool,
        response_callbacks,
        transaction,
        shard_hint,
        r: CustomRedis,
    ) -> None:
        self.r = r
        super().__init__(connection_pool, response_callbacks, transaction, shard_hint)

    def set(
        self,
        name: str,
        value: str,
        ex: int | timedelta | None = None,
        px: int | timedelta | None = None,
        nx: bool = False,
        xx: bool = False,
        keepttl: bool = False,
        get: bool = False,
        **kwargs,
    ) -> Pipeline:
        self.r.cache[name] = value
        return super().set(name, value, ex, px, nx, xx, keepttl, get, **kwargs)
