# backend/fastapi_app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from backend.fastapi_app.db.postgres_db import PostgresDB
from backend.fastapi_app.db.mongo_db import MongoDB

from backend.fastapi_app.api.v1.auth import router as auth_router
from backend.fastapi_app.api.v1.devices import router as devices_router
from backend.fastapi_app.api.v1.admin_devices import router as admin_devices_router


@asynccontextmanager
async def lifespan(app: FastAPI):

    # ---------------- Startup ----------------
    app.state.postgres = PostgresDB()
    app.state.mongo = MongoDB()

    print("Databases initialized (Postgres + MongoDB)")

    yield

    # ---------------- Shutdown ----------------
    try:
        app.state.postgres.close()
        print("Postgres connection closed")
    except Exception as e:
        print("Postgres close failed:", e)

    try:  
        app.state.mongo.client.close()
        print("MongoDB connection closed")
    except Exception:
        print("Mongo close failed:", e)

def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Attendance System API",
        version="1.0.0",
        debug=True,
        lifespan=lifespan
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers
    app.include_router(auth_router)
    app.include_router(devices_router)
    app.include_router(admin_devices_router)

    @app.get("/health")
    def health():
        return {
            "status": "ok"
        }
    
    return app

# This is what TestClient will import 
app = create_app()


# Running directly via python main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.fastapi_app.main.py",
        host="0.0.0.0",
        port=8000,
        reload=True
    )