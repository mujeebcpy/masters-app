"""Guest APIs backing the public Masters Association website (the Vue app in /frontend)."""

import re

import frappe
from pypika import Case

from frappe import _
from frappe.query_builder.functions import Count, Max, Sum
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, flt, getdate, today

from masters_association.geo import point_from_geojson
from masters_association.photos import validate_profile_photo

REGISTRATION_WEB_FORM = "members-registration"
COMMITTEES = ("State Secretariat", "State Executive", "District Coordinator")
YOUTUBE_ID_PATTERN = re.compile(r"(?:youtu\.be/|v=|embed/|shorts/|live/)([A-Za-z0-9_-]{11})")


def _public_member_condition(member):
	return (member.application_status == "Approved") & (member.show_on_website == 1)


def _member_card(row):
	card = {
		"id": row.name,
		"name": row.name1,
		"photo": row.photo,
		"designation": row.designation,
		"company": row.gst_company_name or row.mnre_empanelled_name,
		"district": row.district,
		"membership_status": row.membership_status,
		"is_mnre_empaneled": bool(row.is_mnre_empaneled),
	}
	if row.show_contact_on_website:
		card["email"] = row.email
		card["phone"] = row.mobile_no_whatsapp
	return card


MEMBER_FIELDS = (
	"name",
	"name1",
	"photo",
	"designation",
	"gst_company_name",
	"mnre_empanelled_name",
	"district",
	"membership_status",
	"is_mnre_empaneled",
	"show_contact_on_website",
	"email",
	"mobile_no_whatsapp",
)


def _get_position_holders():
	member = frappe.qb.DocType("Association Member")
	position = frappe.qb.DocType("Association Member Position")

	return (
		frappe.qb.from_(position)
		.join(member)
		.on(position.parent == member.name)
		.select(
			*(member[f] for f in MEMBER_FIELDS),
			position.committee,
			position.position,
			position.term,
			position.display_order,
			position.show_on_home_page,
		)
		.where(position.parenttype == "Association Member")
		.where(_public_member_condition(member))
		.orderby(position.display_order)
		.orderby(member.name1)
		.run(as_dict=True)
	)


def _get_committees(holders):
	"""Group position holders by committee, keeping only each committee's latest term."""
	committees = []
	for committee in COMMITTEES:
		rows = [r for r in holders if r.committee == committee]
		if not rows:
			continue

		latest_term = max(r.term for r in rows)
		committees.append(
			{
				"committee": committee,
				"term": latest_term,
				"members": [
					{**_member_card(r), "position": r.position} for r in rows if r.term == latest_term
				],
			}
		)
	return committees


@frappe.whitelist(allow_guest=True)
def get_members():
	member = frappe.qb.DocType("Association Member")
	members = (
		frappe.qb.from_(member)
		.select(*(member[f] for f in MEMBER_FIELDS))
		.where(_public_member_condition(member))
		.where(member.membership_status.isin(["Lifetime Member", "Normal Member"]))
		.orderby(member.name1)
		.run(as_dict=True)
	)

	return {
		"committees": _get_committees(_get_position_holders()),
		"lifetime": [_member_card(m) for m in members if m.membership_status == "Lifetime Member"],
		"ordinary": [_member_card(m) for m in members if m.membership_status == "Normal Member"],
		"locations": _get_member_locations(),
	}


def _get_member_locations():
	member = frappe.qb.DocType("Association Member")
	rows = (
		frappe.qb.from_(member)
		.select(
			member.name,
			member.name1,
			member.gst_company_name,
			member.mnre_empanelled_name,
			member.district,
			member.location,
			member.google_maps_link,
		)
		.where(_public_member_condition(member))
		.where(member.location.isnotnull())
		.orderby(member.name1)
		.run(as_dict=True)
	)

	locations = []
	for row in rows:
		if point := point_from_geojson(row.location):
			locations.append(
				{
					"id": row.name,
					"name": row.name1,
					"company": row.gst_company_name or row.mnre_empanelled_name,
					"district": row.district,
					"lat": point[0],
					"lng": point[1],
					"maps_link": row.google_maps_link,
				}
			)
	return locations


def _get_home_stats():
	"""Public aggregates only; never fetch providers, enqueue work or change snapshots.

	Count all approved members, regardless of directory/portal visibility. Solar
	figures include their present stations even when an account is disabled.
	Daily/monthly readings must belong to the current site date/month; missing
	readings stay unavailable rather than masquerading as measured zeroes.
	"""
	member = frappe.qb.DocType("Association Member")
	account = frappe.qb.DocType("Solar API Account")
	station = frappe.qb.DocType("Solar Station")
	current_date = getdate(today())
	month_start = current_date.replace(day=1)
	readings = {
		"daily_production_kwh": (station.has_daily == 1) & (station.production_date == current_date),
		"monthly_production_kwh": (station.has_monthly == 1)
		& (station.production_date >= month_start)
		& (station.production_date <= current_date),
		"total_production_kwh": station.has_total == 1,
	}
	fields = [
		Count(station.name).as_("station_count"),
		Sum(station.capacity_kw).as_("capacity_kw"),
		Max(station.last_production_fetch).as_("last_production_fetch"),
	]
	for field, condition in readings.items():
		valid = condition & station[field].isnotnull()
		fields.extend(
			[
				Sum(Case().when(valid, station[field])).as_(field),
				Count(Case().when(valid, station.name)).as_(field + "_coverage"),
			]
		)
	result = (
		frappe.qb.from_(station)
		.join(account)
		.on(station.account == account.name)
		.join(member)
		.on(account.member == member.name)
		.select(*fields)
		.where(member.application_status == "Approved")
		.where(station.present == 1)
		.run(as_dict=True)
	)[0]
	result["member_count"] = frappe.db.count("Association Member", {"application_status": "Approved"})
	result["station_count"] = cint(result["station_count"])
	result["capacity_kw"] = flt(result["capacity_kw"])
	for field in readings:
		result[field] = flt(result[field]) if result[field] is not None else None
		result[field + "_coverage"] = cint(result[field + "_coverage"])
	result["production_date"] = str(current_date)
	return result


@frappe.whitelist(allow_guest=True)
def get_home_data():
	holders = _get_position_holders()
	team = [{**_member_card(r), "position": r.position} for r in holders if r.show_on_home_page]
	if not team:
		# nobody picked for the home page yet: show the current State Secretariat
		secretariat = next(
			(c for c in _get_committees(holders) if c["committee"] == "State Secretariat"), None
		)
		team = secretariat["members"][:4] if secretariat else []

	return {
		"stats": _get_home_stats(),
		"team": team,
		"glimpses": get_gallery(media_type="Photo", home_page_only=True, limit=12),
		"upcoming_events": get_events()["upcoming"][:3],
	}


@frappe.whitelist(allow_guest=True)
def get_gallery(media_type: str | None = None, home_page_only: bool = False, limit: int | None = None):
	filters = {"published": 1}
	if media_type in ("Photo", "Video"):
		filters["media_type"] = media_type
	if frappe.utils.sbool(home_page_only):
		filters["show_on_home_page"] = 1

	items = frappe.get_all(
		"Gallery Item",
		filters=filters,
		fields=["name", "title", "media_type", "album", "image", "video_url", "description", "event_date"],
		order_by="display_order asc, event_date desc, creation desc",
		limit=frappe.utils.cint(limit) or None,
	)

	for item in items:
		if item.media_type == "Video":
			match = YOUTUBE_ID_PATTERN.search(item.video_url or "")
			item.youtube_id = match.group(1) if match else None

	return items


@frappe.whitelist(allow_guest=True)
def get_events():
	events = frappe.get_all(
		"Association Event",
		filters={"published": 1},
		fields=[
			"name",
			"title",
			"start_date",
			"end_date",
			"venue",
			"cover_image",
			"registration_url",
			"summary",
			"description",
		],
		order_by="start_date desc",
	)

	current_date = getdate(today())
	upcoming, past = [], []
	for event in events:
		if getdate(event.end_date or event.start_date) >= current_date:
			upcoming.append(event)
		else:
			past.append(event)

	# soonest upcoming event first
	upcoming.reverse()
	return {"upcoming": upcoming, "past": past}


@frappe.whitelist(allow_guest=True)
def get_documents():
	return frappe.get_all(
		"Association Document",
		filters={"published": 1},
		fields=["name", "title", "category", "file", "description", "document_date"],
		order_by="display_order asc, document_date desc, creation desc",
	)


@frappe.whitelist(allow_guest=True)
def get_registration_options():
	meta = frappe.get_meta("Association Member")

	def options(fieldname):
		return [o for o in (meta.get_field(fieldname).options or "").split("\n") if o]

	return {
		"districts": options("district"),
		"membership_statuses": options("membership_status"),
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60 * 60)
def submit_enquiry(
	enquiry_type: str,
	full_name: str,
	mobile: str,
	message: str,
	email: str | None = None,
	place: str | None = None,
	subject: str | None = None,
	complainant_type: str | None = None,
	on_behalf_of: str | None = None,
):
	if enquiry_type not in ("Contact", "Grievance"):
		frappe.throw(_("Invalid enquiry type"))

	doc = frappe.get_doc(
		{
			"doctype": "Website Enquiry",
			"enquiry_type": enquiry_type,
			"full_name": full_name,
			"mobile": mobile,
			"email": email,
			"place": place,
			"subject": subject,
			"message": message,
			"complainant_type": complainant_type if enquiry_type == "Grievance" else None,
			"on_behalf_of": on_behalf_of if enquiry_type == "Grievance" else None,
		}
	)
	doc.insert(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60 * 60)
def register_member(data: str, photo: str | None = None, photo_name: str | None = None):
	"""Submit the Members Registration web form, optionally with a photo.

	Field handling and validation stay with the web form's own `accept`. The photo is attached
	here because `accept` saves base64 attachments with the caller's permissions, which a guest
	does not have on File.
	"""
	from frappe.website.doctype.web_form.web_form import accept

	content = None
	if photo:
		content, image_format = validate_profile_photo(photo)

	doc = accept(REGISTRATION_WEB_FORM, data)

	if content:
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{doc.name}-profile.{'jpg' if image_format == 'JPEG' else 'png'}",
				"attached_to_doctype": doc.doctype,
				"attached_to_name": doc.name,
				"attached_to_field": "photo",
				"is_private": 0,
				"content": content,
			}
		).insert(ignore_permissions=True)
		doc.db_set("photo", file.file_url)

	return {"name": doc.name}
