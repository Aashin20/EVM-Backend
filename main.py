from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.db import Database
import uvicorn
from core.auth import register, login


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Connecting to Database.....")
    if Database.initialize():
        print("Connected to Database")
    else:
        print("Failed to connect to Database")
        raise RuntimeError("Database connection failed")
    yield
    print("Disconnecting from Database.....")
    Database._engine.dispose()
    print("Disconnected from Database")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/register")
async def register_user(username: str, password: str, role: str):
    return register(username, password, role)


@app.post("/login")
async def login_user(username: str, password: str):
    return login(username, password)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")