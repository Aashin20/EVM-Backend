from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.db import Database
import uvicorn
from routers import auth_route,comp_route,allot_route,master_route,flc_route,meta_route


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

app.include_router(auth_route.router, prefix="/auth", tags=["auth"])
app.include_router(comp_route.router, prefix="/components", tags=["components"])
app.include_router(allot_route.router, prefix="/allotments", tags=["allotments"])    
app.include_router(master_route.router, prefix="/master", tags=["master"])
app.include_router(flc_route.router, prefix="/flc", tags=["flc"])
app.include_router(meta_route.router, prefix="/meta", tags=["meta"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")