"""Resolve a member's Google Maps link to coordinates for the website's member map."""

import json
import re
from urllib.parse import unquote_plus, urlparse

import frappe
import requests

USER_AGENT = "Mozilla/5.0 (compatible; MastersAssociationWebsite/1.0)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
TIMEOUT = 10

# A place link pins the place at !3d<lat>!4d<lng>; @<lat>,<lng> is only the viewport centre
PIN_PATTERN = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
VIEWPORT_PATTERN = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")
QUERY_PATTERN = re.compile(r"[?&](?:q|query|ll|destination)=(-?\d+\.\d+)(?:,|%2C)\s*(-?\d+\.\d+)", re.I)
PLACE_PATTERN = re.compile(r"/maps/place/([^/@?]+)")


def coordinates_from_maps_link(link: str) -> tuple[float, float] | None:
	"""Return (lat, lng) for a Google Maps link, following short links and
	falling back to geocoding the address in the link with OpenStreetMap."""
	link = (link or "").strip()
	if not link:
		return None

	url = _resolve(link)
	for pattern in (PIN_PATTERN, QUERY_PATTERN, VIEWPORT_PATTERN):
		if match := pattern.search(url):
			return _valid(float(match[1]), float(match[2]))

	if match := PLACE_PATTERN.search(urlparse(url).path):
		return _geocode(unquote_plus(match[1]))


def _resolve(link):
	if "goo.gl" not in link and "g.co" not in link:
		return link
	try:
		response = requests.get(link, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, allow_redirects=True)
		return response.url
	except requests.RequestException:
		return link


def _geocode(address):
	"""Geocode an address like "Business, Street, Area, City, State PIN", dropping
	leading parts (usually the business name) until OpenStreetMap finds a match."""
	parts = [p.strip() for p in address.replace("Keralam", "Kerala").split(",") if p.strip()]
	for start in range(len(parts) - 1):
		try:
			response = requests.get(
				NOMINATIM_URL,
				params={"q": ", ".join(parts[start:]), "format": "json", "limit": 1, "countrycodes": "in"},
				headers={"User-Agent": USER_AGENT},
				timeout=TIMEOUT,
			)
			results = response.json() if response.ok else []
		except (requests.RequestException, ValueError):
			return None
		if results:
			return _valid(float(results[0]["lat"]), float(results[0]["lon"]))


def _valid(lat, lng):
	return (lat, lng) if -90 <= lat <= 90 and -180 <= lng <= 180 else None


def point_geojson(lat, lng):
	"""The FeatureCollection a Geolocation field stores for a single pin."""
	return json.dumps(
		{
			"type": "FeatureCollection",
			"features": [
				{"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [lng, lat]}}
			],
		}
	)


def point_from_geojson(value):
	"""Return (lat, lng) of the first point in a Geolocation field value."""
	try:
		features = json.loads(value or "{}").get("features") or []
	except (ValueError, AttributeError):
		return None
	for feature in features:
		geometry = feature.get("geometry") or {}
		if geometry.get("type") == "Point":
			lng, lat = geometry["coordinates"][:2]
			return lat, lng


def update_member_location(member: str):
	link = frappe.db.get_value("Association Member", member, "google_maps_link")
	coordinates = coordinates_from_maps_link(link)
	frappe.db.set_value(
		"Association Member",
		member,
		"location",
		point_geojson(*coordinates) if coordinates else None,
		update_modified=False,
	)
