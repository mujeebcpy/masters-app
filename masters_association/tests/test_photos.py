"""Portrait validation tests without a running Frappe site or file storage."""

import base64
import importlib.util
import sys
import types
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image, PngImagePlugin


class PhotoValidationError(Exception):
	pass


def load_photos():
	frappe_stub = types.ModuleType("frappe")
	frappe_stub._ = lambda message: message

	def throw(message):
		raise PhotoValidationError(message)

	frappe_stub.throw = throw
	spec = importlib.util.spec_from_file_location(
		"_masters_photos_test", Path(__file__).resolve().parents[1] / "photos.py"
	)
	module = importlib.util.module_from_spec(spec)
	with patch.dict(sys.modules, {"frappe": frappe_stub}):
		spec.loader.exec_module(module)
	return module


class TestProfilePhotoValidation(unittest.TestCase):
	def setUp(self):
		self.photos = load_photos()

	def picture(self, image_format="PNG", size=(4, 4), mode="RGB", color="red", **options):
		with Image.new(mode, size, color) as image:
			output = BytesIO()
			image.save(output, format=image_format, **options)
		return output.getvalue()

	def encoded(self, content):
		return base64.b64encode(content).decode("ascii")

	def test_jpeg_and_png_are_detected_from_pixels(self):
		for image_format in ("JPEG", "PNG"):
			with self.subTest(image_format=image_format):
				photo = self.encoded(self.picture(image_format))
				content, detected = self.photos.validate_profile_photo(photo)
				self.assertEqual(detected, image_format)
				with Image.open(BytesIO(content)) as saved:
					self.assertEqual(saved.format, image_format)
					self.assertEqual(saved.size, (4, 4))

	def test_data_url_mime_is_not_trusted(self):
		photo = "data:image/gif;base64," + self.encoded(self.picture())
		self.assertEqual(self.photos.validate_profile_photo(photo)[1], "PNG")

	def test_other_actual_formats_are_rejected(self):
		for image_format in ("GIF", "BMP", "TIFF", "WEBP"):
			with self.subTest(image_format=image_format), self.assertRaises(PhotoValidationError):
				self.photos.validate_profile_photo(self.encoded(self.picture(image_format)))

	def test_invalid_base64_and_image_contents_have_clear_errors(self):
		for photo in (
			None,
			{},
			"",
			"%%%",
			"data:image/png,plain",
			"data:image/png;base64",
			self.encoded(b"hello"),
		):
			with self.subTest(photo=photo), self.assertRaisesRegex(PhotoValidationError, "JPG or PNG"):
				self.photos.validate_profile_photo(photo)

	def test_encoded_size_is_checked_before_decoding(self):
		photo = "A" * (self.photos.MAX_ENCODED_PHOTO_SIZE + 1)
		with patch.object(self.photos.base64, "b64decode") as decode:
			with self.assertRaises(PhotoValidationError):
				self.photos.validate_profile_photo(photo)
			decode.assert_not_called()

	def test_decoded_size_is_checked_before_opening(self):
		with patch.object(self.photos, "MAX_PHOTO_SIZE", 20), patch.object(Image, "open") as opened:
			with self.assertRaises(PhotoValidationError):
				self.photos.validate_profile_photo(self.encoded(b"a" * 21))
			opened.assert_not_called()

	def test_dimensions_and_decompression_bombs_are_rejected(self):
		for size in ((4097, 1), (1, 4097)):
			with self.subTest(size=size), self.assertRaises(PhotoValidationError):
				self.photos.validate_profile_photo(self.encoded(self.picture(size=size)))
		photo = self.encoded(self.picture())
		with patch.object(Image, "MAX_IMAGE_PIXELS", 1), self.assertRaises(PhotoValidationError):
			self.photos.validate_profile_photo(photo)

	def test_metadata_and_appended_payload_are_removed(self):
		metadata = PngImagePlugin.PngInfo()
		metadata.add_text("private-metadata", "remove-me")
		payload = b"<script>appended-payload</script>"
		content = self.picture(pnginfo=metadata) + payload
		clean, _image_format = self.photos.validate_profile_photo(self.encoded(content))
		self.assertNotIn(payload, clean)
		self.assertNotIn(b"remove-me", clean)
		with Image.open(BytesIO(clean)) as saved:
			self.assertNotIn("private-metadata", saved.info)

	def test_png_transparency_is_preserved(self):
		clean, _image_format = self.photos.validate_profile_photo(
			self.encoded(self.picture(mode="RGBA", color=(255, 0, 0, 64)))
		)
		with Image.open(BytesIO(clean)) as saved:
			self.assertEqual(saved.getpixel((0, 0)), (255, 0, 0, 64))


if __name__ == "__main__":
	unittest.main()
