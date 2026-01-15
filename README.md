curl -X POST "http://localhost:8001/process" \
  -F "file=@/mnt/c/Users/HP/Pictures/image_2025-06-30_19-49-52.png" \
  -F "operations={\"resize\":{\"width\":100,\"height\":200},\"filter\":\"grayscale\",\"ocr\":true}"
