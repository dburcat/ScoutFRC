# Backend Docker image
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    ffmpeg \
    # OpenCV / cv2 runtime requirements
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies  
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --force-reinstall "joblib>=1.3.0" "yt-dlp>=2024.1.0"

# Pre-download EasyOCR models at build time into a known directory.
# Setting EASYOCR_MODULE_PATH ensures models land in a predictable writable
# location and are baked into the image layer — avoiding runtime downloads
# and the temp.zip race condition when two workers initialise simultaneously.
ENV EASYOCR_MODULE_PATH=/opt/easyocr
COPY backend/cache_easyocr.py /tmp/cache_easyocr.py
RUN mkdir -p /opt/easyocr && python /tmp/cache_easyocr.py

# Copy application code
COPY backend/ .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]