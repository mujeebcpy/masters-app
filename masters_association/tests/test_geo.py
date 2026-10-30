"""Maps resolution tests; all HTTP requests are mocked and no site is required."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests


def load_geo():
	spec = importlib.util.spec_from_file_location(
		"_masters_geo_test", Path(__file__).resolve().parents[1] / "geo.py"
	)
	module = importlib.util.module_from_spec(spec)
	with patch.dict(sys.modules, {"frappe": types.ModuleType("frappe")}):
		spec.loader.exec_module(module)
	return module


class TestMapsResolution(unittest.TestCase):
	def setUp(self):
		self.geo = load_geo()
		self.http = patch.object(self.geo.requests, "get").start()
		self.addCleanup(patch.stopall)

	def redirect(self, destination):
		return Mock(status_code=302, headers={"Location": destination})

	def test_supported_input_validation_accepts_only_blank_coordinates_or_maps(self):
		for value in (
			None,
			"",
			"   ",
			"9.934167, 76.242833",
			"-9.934167 76.242833",
			"9.934167; -76.242833",
			"90.0000, 180.0000",
			"https://www.google.com/maps?q=9.934167,76.242833",
			"https://maps.app.goo.gl/example",
			"https://goo.gl/maps/example",
		):
			with self.subTest(value=value):
				self.assertTrue(self.geo.is_supported_maps_input(value))
		for value in (
			"javascript:alert(1)",
			"https://example.com",
			"9.934167, 76.242833 extra",
			"coordinates: 9.934167, 76.242833",
			"91.0000, 76.242833",
			"9.934167, 181.0000",
			"https://maps.app.goo.gl:invalid/example",
			"http://google.com/maps",
			{},
		):
			with self.subTest(value=value):
				self.assertFalse(self.geo.is_supported_maps_input(value))
		self.http.assert_not_called()

	def test_coordinates_and_full_maps_links_need_no_http(self):
		for link in (
			"9.934167, 76.242833",
			"https://www.google.com/maps?q=9.934167,76.242833",
			"https://google.co.in/maps/place/Business/!3d9.934167!4d76.242833",
			"https://maps.google.com/?q=9.934167,76.242833",
		):
			with self.subTest(link=link):
				self.assertEqual(self.geo.coordinates_from_maps_link(link), (9.934167, 76.242833))
		self.http.assert_not_called()

	def test_unsafe_or_unsupported_legacy_urls_never_receive_requests(self):
		for link in (
			"https://127.0.0.1/maps?q=9.934167,76.242833",
			"https://169.254.169.254/latest/meta-data/",
			"https://[::1]/maps",
			"https://localhost/maps",
			"http://maps.app.goo.gl/example",
			"https://google.com.evil.example/maps",
			"https://google.com@127.0.0.1/maps",
			"https://www.google.com:8443/maps",
			"https://www.google.com/url?url=https://127.0.0.1/",
			"https://evil.example/maps?google.com",
			"https://share.google/example",
			"https://www.google.com/maps-other",
			"https://maps.app.goo.gl:invalid/example",
		):
			with self.subTest(link=link):
				self.assertIsNone(self.geo.coordinates_from_maps_link(link))
		self.http.assert_not_called()

	def test_short_link_redirect_is_checked_before_following(self):
		response = self.redirect("https://www.google.com/maps?q=9.934167,76.242833")
		self.http.return_value = response
		self.assertEqual(
			self.geo.coordinates_from_maps_link("https://maps.app.goo.gl/example"),
			(9.934167, 76.242833),
		)
		self.assertEqual(self.http.call_count, 1)
		self.assertFalse(self.http.call_args.kwargs["allow_redirects"])
		response.close.assert_called_once()

	def test_redirects_to_private_or_unapproved_destinations_are_not_followed(self):
		for destination in (
			"https://127.0.0.1/maps",
			"http://maps.app.goo.gl/another",
			"//169.254.169.254/latest/meta-data/",
			"https://evil.example/maps",
			"https://www.google.com/url?url=https://localhost/",
		):
			with self.subTest(destination=destination):
				self.http.reset_mock()
				self.http.return_value = self.redirect(destination)
				self.assertIsNone(self.geo.coordinates_from_maps_link("https://maps.app.goo.gl/example"))
				self.assertEqual(self.http.call_count, 1)

	def test_relative_short_redirects_and_loop_limit(self):
		self.http.side_effect = [
			self.redirect("/another"),
			self.redirect("https://google.com/maps?q=9.934167,76.242833"),
		]
		self.assertEqual(
			self.geo.coordinates_from_maps_link("https://maps.app.goo.gl/example"),
			(9.934167, 76.242833),
		)
		self.assertEqual(self.http.call_args_list[1].args[0], "https://maps.app.goo.gl/another")
		self.http.reset_mock()
		self.http.side_effect = None
		self.http.return_value = self.redirect("/loop")
		self.assertIsNone(self.geo.coordinates_from_maps_link("https://maps.app.goo.gl/loop"))
		self.assertEqual(self.http.call_count, self.geo.MAX_MAP_REDIRECTS + 1)

	def test_network_failure_keeps_safe_link_without_coordinates(self):
		self.http.side_effect = requests.Timeout()
		self.assertIsNone(self.geo.coordinates_from_maps_link("https://maps.app.goo.gl/example"))

	def test_address_geocoding_uses_only_fixed_endpoint_without_redirects(self):
		self.http.return_value = Mock(ok=True)
		self.http.return_value.json.return_value = [{"lat": "9.934167", "lon": "76.242833"}]
		self.assertEqual(
			self.geo.coordinates_from_maps_link(
				"https://google.com/maps/place/Business,+Edappally,+Kerala+682024"
			),
			(9.934167, 76.242833),
		)
		self.assertEqual(self.http.call_args.args[0], self.geo.NOMINATIM_URL)
		self.assertFalse(self.http.call_args.kwargs["allow_redirects"])


if __name__ == "__main__":
	unittest.main()
