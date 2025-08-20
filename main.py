from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.db import Database
import uvicorn
from routers import (auth_route,comp_route,allot_route,
                     master_route,flc_route,meta_route,
                     return_route,logs_route,announce_route,
                     pdf_route,msr_route)
import logging
from logging.handlers import RotatingFileHandler
import os
from utils.rate_limiter import user_key_func
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from utils.redis import RedisClient

limiter = Limiter(key_func=user_key_func)


if not os.path.exists("logs"):
    os.makedirs("logs")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        RotatingFileHandler("logs/app.log", maxBytes=5*1024*1024, backupCount=5),
        logging.StreamHandler()  
    ]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Connecting to Database.....")
    if Database.initialize():
        print("Connected to Database")
    else:
        print("Failed to connect to Database")
        raise RuntimeError("Database connection failed")
    print("Initializing Redis.....")
    if await RedisClient.initialize():
        print("Redis initialized successfully")
    else:
        print("Failed to initialize Redis")
        raise RuntimeError("Redis initialization failed")
    yield
    print("Disconnecting from Database.....")
    Database._engine.dispose()
    print("Disconnected from Database")
    
    print("Closing Redis connection.....")
    await RedisClient.close()
    print("Redis closed successfully")


app = FastAPI(lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
       "*"
    ],
    allow_credentials=True, 
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth_route.router, prefix="/auth", tags=["auth"])
app.include_router(comp_route.router, prefix="/components", tags=["components"])
app.include_router(allot_route.router, prefix="/allotments", tags=["allotments"])    
app.include_router(master_route.router, prefix="/master", tags=["master"])
app.include_router(flc_route.router, prefix="/flc", tags=["flc"])
app.include_router(meta_route.router, prefix="/meta", tags=["meta"])
app.include_router(return_route.router,prefix="/status", tags=["status"])
app.include_router(logs_route.router,prefix="/logs", tags=["logs"])
app.include_router(announce_route.router, prefix="/announcements", tags=["announcements"])
app.include_router(pdf_route.router, prefix="/pdf", tags=["pdf"])
app.include_router(msr_route.router, prefix="/msr", tags=["msr"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")