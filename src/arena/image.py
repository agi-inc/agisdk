import base64
import io
from PIL import Image


class Base64Image(str):
    """A string subclass that displays nicely when printed but behaves exactly like a string"""

    def __new__(cls, base64_string):
        return super().__new__(cls, base64_string)

    def __str__(self):
        return self

    def __repr__(self):
        byte_count = len(self) * 3 // 4
        return f"Base64Image({byte_count} bytes)"

    def to_data_url(self):
        """Returns the full data URL with JPEG prefix for models"""
        return f"data:image/jpeg;base64,{self}"

    def to_pil(self):
        """Convert to PIL Image"""
        image_bytes = base64.b64decode(self)
        return Image.open(io.BytesIO(image_bytes))
