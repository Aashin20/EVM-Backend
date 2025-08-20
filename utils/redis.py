import redis.asyncio as redis
import json
import os
from typing import Any

redis_host = os.getenv("REDIS_HOST")
redis_port = int(os.getenv("REDIS_PORT"))
redis_password = os.getenv("REDIS_PASSWORD")

class RedisClient:
    _client = None

    @classmethod
    async def initialize(cls) -> bool:
        try:
            cls._client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True
            )
            
            await cls._client.ping()
            return True
            
        except Exception:
            return False

    @classmethod
    def get_client(cls):
        return cls._client

    @classmethod
    async def close(cls):
        if cls._client:
            try:
                await cls._client.close()  # closes high-level client
                await cls._client.connection_pool.disconnect()  # closes all connections
            except Exception as e:
                print(f"Error while closing Redis: {e}")
            finally:
                cls._client = None

    @classmethod
    def _serialize_value(cls, value: Any) -> str:
        """Serialize value to JSON, handling Pydantic models properly."""
        if hasattr(value, 'model_dump'):  # Pydantic v2
            serializable_value = value.model_dump()
        elif hasattr(value, 'dict'):  # Pydantic v1
            serializable_value = value.dict()
        else:
            serializable_value = value
            
        return json.dumps(serializable_value, default=str)

    @classmethod
    async def set_cache(cls, key: str, value: Any, expire: int = 3600) -> bool:
        if not cls._client:
            return False
        try:
            serialized_value = cls._serialize_value(value)
            await cls._client.setex(key, expire, serialized_value)
            return True
        except Exception as e:
            print(f"Error setting cache for key {key}: {e}")
            return False

    @classmethod
    async def get_cache(cls, key: str):
        if not cls._client:
            return None
        try:
            cached_value = await cls._client.get(key)
            if cached_value is None:
                return None
            return json.loads(cached_value)
        except Exception as e:
            print(f"Error getting cache for key {key}: {e}")
            return None

    @classmethod
    async def delete_cache(cls, key: str) -> bool:
        if not cls._client:
            return False
        try:
            await cls._client.delete(key)
            return True
        except Exception:
            return False

    @classmethod
    async def delete_pattern(cls, pattern: str) -> int:
        if not cls._client:
            return 0
        try:
            keys = await cls._client.keys(pattern)
            if keys:
                return await cls._client.delete(*keys)
            return 0
        except Exception:
            return 0