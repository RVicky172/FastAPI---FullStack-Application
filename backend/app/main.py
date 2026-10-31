"""
Entry point. Run with:   fastapi dev app/main.py
Swagger docs:            http://localhost:8000/docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import ALLOWED_ORIGINS
from .database import init_db
from .middleware import RequestIDMiddleware, TimingLoggingMiddleware
from .routers import auth, todos

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("todo_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code before `yield` runs once at startup, code after it at shutdown.
    init_db()  # create tables in Postgres if they don't exist
    logger.info("Database ready")
    yield


app = FastAPI(title="Todo API", version="1.0.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# 1) Decorator-style middleware (quick & simple)
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_powered_by_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Powered-By"] = "FastAPI"
    return response


# ---------------------------------------------------------------------------
# 2) Class-based middleware (see middleware.py)
#
# ORDER MATTERS: each add_middleware() wraps around everything added before
# it, so the LAST one added is the OUTERMOST (runs first on the request).
#   request -> CORS -> RequestID -> Timing -> powered_by -> route
# ---------------------------------------------------------------------------
app.add_middleware(TimingLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

# ---------------------------------------------------------------------------
# 3) CORS (Cross-Origin Resource Sharing)
#
# The React app runs on http://localhost:5173 and the API on :8000.
# Different port = different "origin", so the BROWSER blocks the response
# unless the API replies with Access-Control-Allow-Origin. For non-simple
# requests (JSON body, Authorization header) the browser first sends an
# OPTIONS "preflight" request - CORSMiddleware answers it for us.
#
# Added last => outermost, so even error responses get CORS headers.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,          # never use ["*"] together with credentials
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Process-Time"],  # lets JS read these headers
)


# ---------------------------------------------------------------------------
# Global error handler: unexpected crashes return clean JSON, not HTML.
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Routers
app.include_router(auth.router)
app.include_router(todos.router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
