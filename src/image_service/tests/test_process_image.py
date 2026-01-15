import base64
import io
from PIL import Image

# Import from the adjacent tasks module
from app.tasks import process_image_task
import pytest


@pytest.mark.parametrize(
    "filter_mode,expected_mode",
    [
        ("grayscale", "L"),
        ("none", "RGB"),
    ],
)
def test_filters(tmp_path, filter_mode, expected_mode):
    img = Image.new("RGB", (100, 100), color="red")
    img_b64 = image_to_base64(img)
    operations = {
        "resize": {"width": 50, "height": 50},
        "filter": filter_mode,
        "ocr": False,
    }
    result = process_image_task(None, img_b64, operations)
    processed_img = Image.open(io.BytesIO(base64.b64decode(result["image_b64"])))
    assert processed_img.mode == expected_mode


def image_to_base64(img: Image.Image) -> str:
    """Helper: convert PIL image to
    base64 string."""
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def test_resize_and_filter(tmp_path):
    # Create a simple red square image (100x100)
    img = Image.new("RGB", (100, 100), color="red")
    img_b64 = image_to_base64(img)

    operations = {
        "resize": {"width": 50, "height": 50},
        "filter": "grayscale",  # Ensure spelling matches implementation
        "ocr": False,
    }

    # Use .run() to bypass Celery broker and test logic directly.
    # We pass None as 'self' because bind=True in the decorator expects the instance.
    result = process_image_task(None, img_b64, operations)

    # Assertions
    assert result["status"] == "completed"
    assert "image_b64" in result
    assert result.get("ocr_text") is None

    # Decode result and check size/mode
    processed_bytes = base64.b64decode(result["image_b64"])
    processed_img = Image.open(io.BytesIO(processed_bytes))

    assert processed_img.size == (50, 50)
    # PIL converts to "L" mode for grayscale
    assert processed_img.mode == "L"


def test_invalid_input():
    # Pass invalid base64 string
    result = process_image_task(None, "not_base64_string", {})

    assert result["status"] == "failed"
    assert "error" in result
