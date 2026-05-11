"""Pre-download EasyOCR models into /opt/easyocr at image build time."""
import easyocr  # type: ignore[import]

print("Downloading EasyOCR models to /opt/easyocr ...")
easyocr.Reader(["en"], gpu=False, verbose=True, model_storage_directory="/opt/easyocr")
print("EasyOCR models cached successfully.")