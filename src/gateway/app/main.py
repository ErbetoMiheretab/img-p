from .logger import setup_logging
import redis
import json
import os
import structlog
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from slowapi.util import get_remote_address
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


setup_logging()
logger = structlog.get_logger()


IMAGE_SERVICE_URL = os.getenv("IMAGE_SERVICE_URL", "http://localhost:8001")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Rate Limiter setup
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])
redis_client = redis.Redis.from_url(REDIS_URL)

app = FastAPI(title="API Gateway")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    logger.info("request_started", path=request.url.path, method=request.method)
    response = await call_next(request)
    logger.info("request_finished", status_code=response.status_code)
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/api/v1/images/process")
@limiter.limit("5/minute")
async def proxy_process_image(request: Request):
    """
    Proxy request to Image Service.
    We must stream the body to avoid loading large files into Gateway memory.
    """

    client = httpx.AsyncClient(base_url=IMAGE_SERVICE_URL)

    try:
        # Read the form data (files/json) from the incoming request
        form = await request.form()

        # Validate required fields
        if "file" not in form:
            logger.warning("validation_error", detail="Missing 'file' in request")
            raise HTTPException(status_code=400, detail="Missing 'file' field")
        
        if "operations" not in form:
            logger.warning("validation_error", detail="Missing 'operations' in request")
            raise HTTPException(status_code=400, detail="Missing 'operations' field")

        # Construct parameters for the downstream service
        files = {
            "file": (
                form["file"].filename,
                form["file"].file,
                form["file"].content_type,
            )
        }
        data = {"operations": form["operations"]}

        response = await client.post("/process", data=data, files=files)
        
        if response.status_code >= 400:
            logger.error("upstream_error_response", status_code=response.status_code, content=response.text)
            raise HTTPException(status_code=502, detail="Upstream Image Service Error")

        return response.json()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("gateway_proxy_error", error=str(e))
        raise HTTPException(status_code=502, detail="Image Service Unavailable")

    finally:
        await client.aclose()


@app.get("/api/v1/images/status/{task_id}")
async def proxy_check_status(task_id: str, request: Request):
    """
    Check status with caching.
    If the task is completed, we cache the result in Redis for 1 hour to save calls.
    """
    cache_key = f"task_result:{task_id}"

    # Check Gateway Cache
    if cached := redis_client.get(cache_key):
        logger.info("cache_hit", task_id=task_id)
        return JSONResponse(content=json.loads(cached))

    # Call Upstream
    client = httpx.AsyncClient(base_url=IMAGE_SERVICE_URL)

    try:
        resp = await client.get(f"/status/{task_id}")
        data = resp.json()

        # Cache if completed
        if resp.status_code == 200 and data.get("status") == "completed":
            redis_client.setex(cache_key, 3600, json.dumps(data))

        return data
    except Exception as e:
        logger.error("upstream_error", error=str(e))
        raise HTTPException(status_code=502, detail="Image Service Unavailable")
    finally:
        await client.aclose()