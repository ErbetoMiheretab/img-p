curl -X POST "http://localhost:8001/process" \
  -F "file=@/mnt/c/Users/HP/Pictures/image_2025-06-30_19-49-52.png" \
  -F "operations={\"resize\":{\"width\":100,\"height\":200},\"filter\":\"grayscale\",\"ocr\":true}"


curl -X 'GET' \                                                       
  'http://localhost:8001/status/a3ddb229-c876-4b76-9a39-8b8f2ef92ea6' \
  -H 'accept: application/json'