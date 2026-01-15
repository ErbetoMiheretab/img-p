from fastapi import FastAPI, UploadFile, File, Form
from pydantic import Json
from typing import Any
from celery.result import AsyncResult

from src.image_service.app.tasks import process_image_task, celery_app
import base64


app = FastAPI(title="Image Processing Service")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/process")
async def enqueue_image(
    file: UploadFile = File(...), operations: Json = Form(...)
) -> dict[str, str]:
    # Read file and convert to b64 (For celery, it needs serializable data)
    file_content: bytes = await file.read()
    image_b64: str = base64.b64encode(file_content).decode("utf-8")

    # Enqueue task
    task = process_image_task.delay(image_b64, operations)

    return {"task_id": task.id, "status": "processing"}


@app.get("/status/{task_id}")
async def get_status(task_id: str) -> dict[str, Any]:
    task_result = AsyncResult(task_id, app=celery_app)
    if task_result.ready():
        return {"task_id": task_id, "status": "completed", "result": task_result.result}
    return {"task_id": task_id, "status": "pending"}
