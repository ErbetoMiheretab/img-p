import base64
import io
import pytesseract
from typing import Optional
from src.image_service.app.processors.celery_app import celery_app
from PIL import Image, ImageFilter


@celery_app.task(bind=True)
def process_image_task(
    self, image_data_b64: str, operations: dict[str, any]
) -> Optional[Image.Image]:
    """
    Decodes base64 image, applies operations, returns result
     Args:
        self: Celery task context (if used inside a Celery task class).
        image_data_b64 (str): Base64-encoded image data.
        operations (dict): Dictionary of operations to apply. Example:
            {
                "resize": {"width": 100, "height": 200},
                "filter": "greyscale"
            }

    Returns:
        PIL.Image.Image or None if an error occurs.

    """

    try:
        # Decode image

        image_bytes: bytes = base64.b64decode(image_data_b64)
        img: Image.Image = Image.open(io.BytesIO(image_bytes))

        # Resize

        if "resize" in operations:
            w: Optional[int] = operations["resize"].get("width")
            h: Optional[int] = operations["resize"].get("height")

            if w and h:
                img = img.resize((w, h))

        # Filters
        if "filter" in operations:
            filter_type = operations["filter"]

            if filter_type == "grayscale":
                img = img.convert("L")
            elif filter_type == "blur":
                img = img.filter(ImageFilter.BLUR)
            elif filter_type == "sharpen":
                img: Image.Image = img.filter(ImageFilter.SHARPEN)

        # OCR
        ocr_text: Optional[str] = None
        if operations.get("ocr", False):
            # Convert to RGB just in case
            ocr_text = pytesseract.image_to_string(img)

        # Encode back to base64 for return

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        processed_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return {"status": "completed", "image_b64": processed_b64, "ocr_text": ocr_text}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
