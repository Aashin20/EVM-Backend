from slowapi import Limiter
from fastapi import Request

def user_key_func(request: Request):
    return str(getattr(request.state, "user_id", request.client.host))

limiter = Limiter(key_func=user_key_func)
