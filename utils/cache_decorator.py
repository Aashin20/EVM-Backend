import functools
import hashlib
import json
import inspect
from typing import get_type_hints
from fastapi import Request
from utils.redis import RedisClient

def cache_response(expire: int = 3600, key_prefix: str = "", include_user: bool = True):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            cache_key = _generate_cache_key(func.__name__, request, kwargs, key_prefix, include_user)
            
            cached_result = await RedisClient.get_cache(cache_key)
            if cached_result is not None:
                # Get the return type from the function signature
                return_type = _get_return_type(func)
                
                if return_type and _is_pydantic_model(return_type):
                    try:
                        # Reconstruct Pydantic model from cached data
                        if hasattr(return_type, 'model_validate'):  # Pydantic v2
                            return return_type.model_validate(cached_result)
                        elif hasattr(return_type, 'parse_obj'):  # Pydantic v1
                            return return_type.parse_obj(cached_result)
                    except Exception as e:
                        print(f"Error reconstructing cached model: {e}")
                        # Fall through to re-execute function
                
                # Return cached result as-is if it's not a Pydantic model
                print("Fetched from cache:", cache_key)
                return cached_result
            
            result = await func(*args, **kwargs)
            await RedisClient.set_cache(cache_key, result, expire)
            return result
                
        return wrapper
    return decorator

def _get_return_type(func):
    """Extract return type annotation from function."""
    try:
        type_hints = get_type_hints(func)
        return type_hints.get('return')
    except Exception:
        # Fallback to inspect for older Python versions
        try:
            sig = inspect.signature(func)
            return sig.return_annotation if sig.return_annotation != inspect.Signature.empty else None
        except Exception:
            return None

def _is_pydantic_model(type_obj):
    """Check if the type is a Pydantic model."""
    if type_obj is None:
        return False
    
    # Check for Pydantic v2
    if hasattr(type_obj, 'model_validate') and hasattr(type_obj, 'model_dump'):
        return True
    
    # Check for Pydantic v1
    if hasattr(type_obj, 'parse_obj') and hasattr(type_obj, 'dict'):
        return True
    
    return False

def _generate_cache_key(func_name: str, request, kwargs: dict, key_prefix: str, include_user: bool) -> str:
    key_parts = []
    
    if key_prefix:
        key_parts.append(key_prefix)
    
    key_parts.append(func_name)
    
    if include_user and request and hasattr(request.state, 'user_id'):
        key_parts.append(f"user:{request.state.user_id}")
    
    if request and request.query_params:
        query_hash = hashlib.md5(str(sorted(request.query_params.items())).encode()).hexdigest()[:8]
        key_parts.append(f"query:{query_hash}")
    
    path_params = {k: v for k, v in kwargs.items() if k != 'request'}
    if path_params:
        params_hash = hashlib.md5(json.dumps(path_params, sort_keys=True, default=str).encode()).hexdigest()[:8]
        key_parts.append(f"params:{params_hash}")
    
    return ":".join(key_parts)