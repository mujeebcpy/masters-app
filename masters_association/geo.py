"""Resolve a member's Google Maps link to coordinates for the website's member map."""

import json
import re
from urllib.parse import parse_qs, unquote_plus, urljoin, urlparse

import frappe
import requests

USER_AGENT = "Mozilla/5.0 (compatible; MastersAssociationWebsite/1.0)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
TIMEOUT = 5
MAX_MAP_REDIRECTS = 5
MAPS_HOSTS = frozenset({"google.com", "www.google.com", "google.co.in", "www.google.co.in"})
MAPS_SUBDOMAIN_HOSTS = frozenset({"maps.google.com", "maps.google.co.in"})
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
# Address parts OpenStreetMap can't match, like the "P.O" in "…, P.O, Thalikulam, …"
FILLER_PART = re.compile(r"^(p\.?\s*o\.?|post|post office)$", re.I)
# At least a locality and "State PIN"
MIN_GEOCODE_PARTS = 2

# Google Search share links (share.google/…) carry only a business name, never a location
SEARCH_LINK_HOSTS = ("share.google", "g.co")
MAPS_LINK_HELP = (
	"Get the link from the Google Maps app or google.com/maps instead: open your business, "
	"tap <b>Share</b> and choose <b>Copy link</b>. It looks like https://maps.app.goo.gl/…"
)

# A place link pins the place at !3d<lat>!4d<lng>; @<lat>,<lng> is only the viewport centre
PIN_PATTERN = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
VIEWPORT_PATTERN = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")
QUERY_PATTERN = re.compile(r"[?&](?:q|query|ll|destination)=(-?\d+\.\d+)(?:,|%2C)\s*(-?\d+\.\d+)", re.I)
PLACE_PATTERN = re.compile(r"/maps/place/([^/@?]+)")
# Coordinates typed in instead of a link, e.g. "9.934167, 76.242833"
TYPED_PATTERN = re.compile(r"(-?\d{1,2}\.\d{4,})\D.*?(-?\d{1,3}\.\d{4,})")
COORDINATE_INPUT_PATTERN = re.compile(r"(-?\d{1,2}\.\d{4,})(?:\s*[,;]\s*|\s+)(-?\d{1,3}\.\d{4,})")
POSTCODE_PATTERN = re.compile(r"\b\d{6}\b")


def is_search_share_link(link: str) -> bool:
	host = urlparse((link or "").strip()).netloc.lower().removeprefix("www.")
	return host in SEARCH_LINK_HOSTS


def is_supported_maps_input(link: str | None) -> bool:
	"""Validate changed inputs without resolving them or making any network request."""
	if link is None:
		return True
	if not isinstance(link, str):
		return False
	link = link.strip()
	if not link:
		return True
	if match := COORDINATE_INPUT_PATTERN.fullmatch(link):
		return _valid(float(match[1]), float(match[2])) is not None
	return _is_allowed_maps_url(link)


def coordinates_from_maps_link(link: str) -> tuple[float, float] | None:
	"""Return (lat, lng) for a Google Maps link, following short links and
	falling back to geocoding the address in the link with OpenStreetMap."""
	link = (link or "").strip()
	if not link:
		return None

	if not link.startswith("http"):
		match = TYPED_PATTERN.search(link)
		return _valid(float(match[1]), float(match[2])) if match else None

	url = _resolve(link)
	if not url:
		return None
	for pattern in (PIN_PATTERN, QUERY_PATTERN, VIEWPORT_PATTERN):
		if match := pattern.search(url):
			return _valid(float(match[1]), float(match[2]))

	if address := _address(url):
		return _geocode(address)


def _address(url):
	"""The address in a /maps/place/<address> or /maps?q=<address> link."""
	parsed = urlparse(url)
	if match := PLACE_PATTERN.search(parsed.path):
		return unquote_plus(match[1])
	if parsed.path.startswith("/maps"):
		return (parse_qs(parsed.query).get("q") or [None])[0]


def _is_allowed_maps_url(link):
	"""Only Google-owned Maps endpoints may receive a member-controlled request."""
	try:
		parsed = urlparse(link)
		if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443):
			return False
		host = (parsed.hostname or "").lower()
		maps_path = parsed.path == "/maps" or parsed.path.startswith("/maps/")
		return (
			(host in MAPS_HOSTS and maps_path)
			or (host in MAPS_SUBDOMAIN_HOSTS and (maps_path or parsed.path in ("", "/")))
			or (host == "goo.gl" and maps_path)
			or (host == "maps.app.goo.gl" and bool(parsed.path.strip("/")))
		)
	except (TypeError, ValueError):
		return False


def _resolve(link):
	"""Resolve short links without following an unchecked redirect, including legacy values."""
	for _redirect in range(MAX_MAP_REDIRECTS + 1):
		if not _is_allowed_maps_url(link):
			return None
		if (urlparse(link).hostname or "").lower() in MAPS_HOSTS | MAPS_SUBDOMAIN_HOSTS:
			return link
		try:
			response = requests.get(
				link,
				headers={"User-Agent": USER_AGENT},
				timeout=TIMEOUT,
				allow_redirects=False,
				stream=True,
			)
			try:
				if response.status_code not in REDIRECT_STATUSES:
					return link
				location = response.headers.get("Location")
				if not location:
					return None
				link = urljoin(link, location)
			finally:
				response.close()
		except requests.RequestException:
			return link
	return None


def _geocode(address):
	"""Geocode an address like "Business, Street, Area, City, State PIN", dropping
	leading parts until OpenStreetMap finds a match, then trying just the postcode.
	The first part is the business name, which OpenStreetMap rarely knows, so it is
	never sent."""
	parts = [p.strip() for p in address.replace("Keralam", "Kerala").split(",")]
	parts = [p for p in parts[1:] if p and not FILLER_PART.match(p)]
	queries = [", ".join(parts[start:]) for start in range(len(parts) - MIN_GEOCODE_PARTS + 1)]
	if parts and (postcode := POSTCODE_PATTERN.search(parts[-1])):
		queries.append(f"{postcode[0]}, {POSTCODE_PATTERN.sub('', parts[-1]).strip() or 'Kerala'}")

	for query in queries:
		try:
			response = requests.get(
				NOMINATIM_URL,
				params={"q": query, "format": "json", "limit": 1, "countrycodes": "in"},
				headers={"User-Agent": USER_AGENT},
				timeout=TIMEOUT,
				allow_redirects=False,
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
				{
					"type": "Feature",
					"properties": {},
					"geometry": {"type": "Point", "coordinates": [lng, lat]},
				}
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
