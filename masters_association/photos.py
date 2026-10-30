"""Validate and normalize public member portraits without trusting filenames or MIME labels."""

import base64
import warnings
from io import BytesIO

import frappe
from frappe import _

MAX_PHOTO_SIZE = 5 * 1024 * 1024
MAX_PHOTO_DIMENSION = 4096
MAX_ENCODED_PHOTO_SIZE = 4 * ((MAX_PHOTO_SIZE + 2) // 3)


def validate_profile_photo(photo):
	"""Return clean (bytes, JPEG/PNG format) or raise a user-facing ValidationError."""
	from PIL import Image, ImageOps

	try:
		if not isinstance(photo, str) or not photo or len(photo) > MAX_ENCODED_PHOTO_SIZE + 1024:
			raise ValueError
		if photo.startswith("data:"):
			header, photo = photo.split(",", 1)
			if not header.lower().endswith(";base64"):
				raise ValueError
		if len(photo) > MAX_ENCODED_PHOTO_SIZE:
			raise ValueError
		content = base64.b64decode(photo, validate=True)
		if not content or len(content) > MAX_PHOTO_SIZE:
			raise ValueError
		with warnings.catch_warnings():
			warnings.simplefilter("error", Image.DecompressionBombWarning)
			with Image.open(BytesIO(content)) as uploaded:
				image_format = uploaded.format
				if image_format not in ("JPEG", "PNG") or not all(
					0 < dimension <= MAX_PHOTO_DIMENSION for dimension in uploaded.size
				):
					raise ValueError
				uploaded.verify()
			with Image.open(BytesIO(content)) as uploaded, ImageOps.exif_transpose(uploaded) as oriented:
				mode = (
					"RGBA"
					if image_format == "PNG"
					and ("A" in oriented.getbands() or "transparency" in oriented.info)
					else "RGB"
				)
				with oriented.convert(mode) as pixels, Image.new(mode, oriented.size) as clean:
					clean.paste(pixels)
					output = BytesIO()
					clean.save(output, format=image_format)
					content = output.getvalue()
		if len(content) > MAX_PHOTO_SIZE:
			raise ValueError
	except (ValueError, TypeError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
		frappe.throw(_("Photo must be a valid JPG or PNG image up to 5 MB and 4096 x 4096 pixels."))
	return content, image_format
