# backend/fastapi_app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.fastapi_app.api.v1.auth import router as auth_router
from backend.fastapi_app.api.v1.devices import router as devices_router
from backend.fastapi_app.api.v1.admin_devices import router as admin_devices_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Attendance System API",
        version="1.0.0"
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

    @app.get("/heath")
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