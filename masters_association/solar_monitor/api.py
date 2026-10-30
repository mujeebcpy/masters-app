"""Solar Monitor portal methods.

Every method authorizes through access.py. Members see and manage only their own
accounts; global viewers (Administrator, System Manager, Solar Monitor Viewer) read all
accounts and cannot change anything or trigger provider calls. Secrets are write-only.
"""

import json
from collections import Counter
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint, get_datetime
from frappe.utils.background_jobs import is_job_enqueued
from frappe.utils.password import get_decrypted_password

from masters_association.solar_monitor import access, alerts, service

PROVIDER_CHOICES = ("Deye", "Enphase", "Solarman")
# Non-secret account fields shown in the dashboard to anyone who may read the account.
STATUS_FIELDS = [
	"name",
	"account_label",
	"member",
	"provider",
	"enabled",
	"company_name",
	"connection_status",
	"authentication_error",
	"last_successful_sync",
	"sync_status",
	"sync_error",
	"company_lookup_error",
	"alert_status",
	"last_alert_sync",
	"alert_error",
	"month_hits",
	"month_hits_period",
]
# Owner-only configuration fields: identifying but not secret.
CONFIG_FIELDS = [
	"region",
	"app_id",
	"email",
	"company_id",
	"client_id",
	"redirect_uri",
	"enphase_username",
	"expires_at",
]
SECRET_FIELDS = ("app_secret", "password", "api_key", "client_secret", "enphase_password")
EDITABLE_FIELDS = frozenset(
	{"account_label", "provider", "enabled", *CONFIG_FIELDS[:-1], *SECRET_FIELDS}
)


def _member_names(names):
	rows = frappe.get_all("Association Member", filters={"name": ["in", list(names)]}, fields=["name", "name1"])
	return {r.name: r.name1 or r.name for r in rows}


@frappe.whitelist(methods=["GET"])
def get_my_accounts():
	member = access.require_member()
	rows = frappe.get_all(
		service.ACCOUNT,
		filters={"member": member.name},
		fields=STATUS_FIELDS + CONFIG_FIELDS,
		order_by="account_label",
	)
	period, budget = service.month_period(), service.setting("enphase_monthly_budget", 9000)
	for row in rows:
		if row.month_hits_period != period:
			row.month_hits = 0
		row.hit_budget = budget if row.provider == "Enphase" else None
		for field in SECRET_FIELDS:
			row["has_" + field] = bool(
				get_decrypted_password(service.ACCOUNT, row.name, field, raise_exception=False)
			)
	return rows


@frappe.whitelist(methods=["POST"])
def save_my_account(data, name: str | None = None):
	member = access.require_member()
	if isinstance(data, str):
		data = json.loads(data)
	if not isinstance(data, dict):
		frappe.throw(_("Invalid account details."))
	unknown = set(data) - EDITABLE_FIELDS
	if unknown:
		frappe.throw(_("These fields cannot be changed: {0}").format(", ".join(sorted(unknown))))
	if data.get("provider") and data["provider"] not in PROVIDER_CHOICES:
		frappe.throw(_("Unknown provider."))
	if name:
		access.require_account(name, write=True)
		doc = frappe.get_doc(service.ACCOUNT, name, for_update=True)
	else:
		doc = frappe.new_doc(service.ACCOUNT)
		doc.member = member.name
		doc.enabled = 1
	for key, value in data.items():
		# A blank secret keeps the stored value; secrets are never sent back to the browser.
		if key in SECRET_FIELDS and not value:
			continue
		doc.set(key, cint(value) if key == "enabled" else (value.strip() if isinstance(value, str) else value))
	doc.save(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist(methods=["POST"])
def disable_my_account(account: str):
	access.require_account(account, write=True)
	frappe.db.set_value(service.ACCOUNT, account, {"enabled": 0, "connection_status": "Not connected"})
	return {"status": "Disabled"}


@frappe.whitelist(methods=["POST"])
def enable_my_account(account: str):
	access.require_account(account, write=True)
	doc = frappe.get_doc(service.ACCOUNT, account, for_update=True)
	doc.enabled = 1
	doc.save(ignore_permissions=True)
	return {"status": "Enabled"}


@frappe.whitelist(methods=["POST"])
def test_connection(account: str):
	access.require_account(account, write=True)
	service.account_doc(account)
	with service.lock(
		"solar-monitor-test:" + account, 300, 1, _("A connection test is already running for this account.")
	):
		key = "solar-monitor-test-time:" + account
		if frappe.cache().get_value(key):
			frappe.throw(_("Wait 30 seconds before testing again."))
		frappe.cache().set_value(key, 1, expires_in_sec=30)
		try:
			service.ensure_token(account)
			service.company_details(account)
			frappe.db.set_value(
				service.ACCOUNT, account, {"connection_status": "Connected", "authentication_error": ""}
			)
			return {
				"status": "Connected",
				"expires_at": frappe.db.get_value(service.ACCOUNT, account, "expires_at"),
			}
		except service.ProviderError as exc:
			if isinstance(exc, service.Busy):
				raise
			frappe.db.set_value(
				service.ACCOUNT, account, {"connection_status": "Error", "authentication_error": str(exc)}
			)
			return {"status": "Error", "error": str(exc)}


def enphase_account(account):
	doc = service.account_doc(account)
	if doc.provider != "Enphase":
		frappe.throw(_("Select an enabled Enphase account."))
	return doc


@frappe.whitelist(methods=["POST"])
def enphase_authorize_url(account: str):
	"""Start the browser authorization; the one-time state ties the callback to this session and owner."""
	member = access.require_account(account, write=True)
	from masters_association.solar_monitor import enphase

	doc = enphase_account(account)
	state = frappe.generate_hash(length=32)
	frappe.cache().set_value(
		"solar-monitor-enphase-state:" + state,
		{"account": account, "user": frappe.session.user, "member": member.name},
		expires_in_sec=900,
	)
	return {"url": enphase.authorize_url(doc, state), "redirect_uri": enphase.redirect_uri(doc)}


def finish_authorization(account, code):
	from masters_association.solar_monitor import enphase

	try:
		enphase.exchange_code(account, code)
		frappe.db.set_value(
			service.ACCOUNT, account, {"connection_status": "Connected", "authentication_error": ""}
		)
		return {"status": "Connected"}
	except service.ProviderError as exc:
		if isinstance(exc, service.Busy):
			raise
		frappe.db.set_value(
			service.ACCOUNT, account, {"connection_status": "Error", "authentication_error": str(exc)}
		)
		return {"status": "Error", "error": str(exc)}


@frappe.whitelist(methods=["POST"])
def enphase_authorize(account: str, code: str):
	"""Exchange an authorization code pasted from the Enphase redirect page."""
	access.require_account(account, write=True)
	enphase_account(account)
	return finish_authorization(account, code)


@frappe.whitelist(methods=["GET"])
def enphase_callback(code: str | None = None, state: str | None = None, error: str | None = None):
	"""OAuth redirect target when the account's Redirect URI points at this method."""
	key = "solar-monitor-enphase-state:" + (state or "")
	pending = frappe.cache().get_value(key) if state else None
	frappe.cache().delete_value(key)
	if not pending or pending.get("user") != frappe.session.user:
		frappe.throw(_("Authorization request expired or is invalid. Start again from the API account."))
	account = pending["account"]
	# Ownership may have changed since the authorization started.
	if access.require_account(account, write=True).name != pending.get("member"):
		frappe.throw(_("Authorization request expired or is invalid. Start again from the API account."))
	if error or not code:
		message = _("Enphase authorization was not granted.")
		frappe.db.set_value(
			service.ACCOUNT, account, {"connection_status": "Error", "authentication_error": message}
		)
	else:
		enphase_account(account)
		finish_authorization(account, code)
	frappe.db.commit()
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = "/solar/accounts?account=" + quote(account)


@frappe.whitelist(methods=["POST"])
def fetch_company_details(account: str):
	access.require_account(account, write=True)
	key = "solar-monitor-company-click:" + account
	with service.lock(key + ":lock", 300, 1, _("Company details are already being fetched.")):
		if frappe.cache().get_value(key):
			frappe.throw(_("Wait 30 seconds before updating company details again."))
		frappe.cache().set_value(key, 1, expires_in_sec=30)
		service.company_details(account, manual=True)
	return frappe.db.get_value(
		service.ACCOUNT, account, ["company_name", "company_lookup_error"], as_dict=True
	)


@frappe.whitelist(methods=["POST"])
def sync_inventory(account: str, refresh_devices: int = 0):
	"""Queue an inventory fetch. Enphase device lists (one hit per system) are fetched only for new
	systems unless `refresh_devices` is set."""
	access.require_account(account, write=True)
	with service.lock(
		"solar-monitor-enqueue:" + account,
		30,
		5,
		_("Inventory fetch is already being queued for this account."),
	):
		doc = service.account_doc(account)
		elapsed = (
			(service.now() - get_datetime(doc.sync_started_at)).total_seconds()
			if doc.sync_started_at
			else 999999
		)
		job_id = "solar-monitor-inventory-job:" + account
		# A status left behind by a job that crashed or was lost must not block a new sync.
		if doc.sync_status in ("Queued", "Running") and elapsed < 7200 and is_job_enqueued(job_id):
			return {"status": doc.sync_status}
		if elapsed < service.setting("refresh_cooldown", 120):
			frappe.throw(_("Inventory was requested recently. Wait for the refresh cooldown."))
		frappe.db.set_value(
			service.ACCOUNT,
			account,
			{"sync_status": "Queued", "sync_started_at": service.now(), "sync_error": ""},
		)
		frappe.enqueue(
			"masters_association.solar_monitor.service.sync_job",
			queue="long",
			timeout=7200,
			account=account,
			refresh_devices=bool(cint(refresh_devices)),
			job_id=job_id,
			enqueue_after_commit=True,
		)
	return {"status": "Queued"}


@frappe.whitelist(methods=["GET"])
def get_overview(
	provider: str | None = None,
	account: str | None = None,
	member: str | None = None,
	station: str | None = None,
	start: int = 0,
	search: str | None = None,
):
	from masters_association.solar_monitor import production

	scope = access.get_scope()
	if provider and provider not in PROVIDER_CHOICES:
		frappe.throw(_("Unknown provider."))
	account_filters = access.account_filters(scope, member)
	if provider:
		account_filters["provider"] = provider
	accounts = frappe.get_all(
		service.ACCOUNT, filters=account_filters, fields=STATUS_FIELDS, order_by="account_label"
	)
	allowed = {x.name for x in accounts}
	if account and account not in allowed:
		frappe.throw(_("Select one of the listed accounts."))
	selected = [account] if account else list(allowed)
	filters = {"account": ["in", selected or [""]]}
	rows = frappe.get_all(
		"Solar Station",
		filters=dict(filters, present=1),
		fields=production.FIELDS,
		order_by="station_name",
	)
	providers = {x.name: x.provider for x in accounts}
	rows = [production.display(row, production.stale_after(providers.get(row.account))) for row in rows]
	summary = production.totals(rows)
	station_names = {r.name: r.station_name or r.name for r in rows}
	open_alerts = frappe.get_all(
		alerts.ALERT,
		filters=dict(filters, status="Open"),
		fields=alerts.FIELDS,
		order_by="priority desc, alert_start desc",
		page_length=100,
	)
	for row in open_alerts:
		row.station_name = station_names.get(row.station, row.station)
	alert_counts = dict(
		Counter(frappe.get_all(alerts.ALERT, filters=dict(filters, status="Open"), pluck="severity"))
	)
	members = _member_names({x.member for x in accounts})
	for row in accounts:
		row.member_name = members.get(row.member)
	if station:
		rows = [r for r in rows if r.name == station]
	if search:
		rows = [r for r in rows if search.lower() in (r.station_name or r.name).lower()]
	offset = max(0, cint(start))
	own = scope.member.name if scope.member else None
	return {
		"scope": "all" if scope.can_view_all else "own",
		"members": [{"name": k, "label": v} for k, v in sorted(members.items(), key=lambda x: x[1])]
		if scope.can_view_all
		else [],
		"accounts": accounts,
		"alerts": open_alerts,
		"alert_counts": alert_counts,
		"stations": rows[offset : offset + 100],
		"filtered_count": len(rows),
		"summary": summary,
		"station_count": summary["station_count"],
		"device_count": frappe.db.count("Solar Device", dict(filters, present=1)),
		"manageable_accounts": [x.name for x in accounts if own and x.member == own and x.enabled],
		"busy": any(r.production_status in ("Queued", "Running") for r in rows),
	}


@frappe.whitelist(methods=["GET"])
def get_station(station: str):
	from masters_association.solar_monitor import production

	account = access.require_station(station)
	doc = frappe.get_doc("Solar Station", station)
	row = frappe._dict({key: doc.get(key) for key in production.FIELDS})
	info = frappe.db.get_value(
		service.ACCOUNT, account, ["provider", "account_label", "member", "enabled"], as_dict=True
	)
	member = access._session_member()
	return {
		"station": production.display(row, production.stale_after(info.provider)),
		"account": {"name": account, "label": info.account_label, "provider": info.provider},
		"devices": frappe.get_all(
			"Solar Device",
			filters={"station": station, "present": 1},
			fields=["name", "external_id", "device_type", "last_seen"],
			order_by="device_type, name",
		),
		"alerts": frappe.get_all(
			alerts.ALERT,
			filters={"station": station, "status": "Open"},
			fields=alerts.FIELDS,
			order_by="priority desc, alert_start desc",
		),
		"can_manage": bool(member and member.name == info.member and info.enabled),
	}


@frappe.whitelist(methods=["POST"])
def refresh_station(station: str):
	from masters_association.solar_monitor import production

	access.require_station(station, write=True)
	return production.enqueue(station)


def enabled_accounts(account):
	"""The session member's enabled accounts, optionally narrowed to one of them."""
	member = access.require_member()
	accounts = frappe.get_all(
		service.ACCOUNT,
		filters={"member": member.name, "enabled": 1, "provider": ["in", service.PROVIDERS]},
		pluck="name",
	)
	if account and account not in accounts:
		frappe.throw(_("Select one of your enabled accounts."))
	return [account] if account else accounts


@frappe.whitelist(methods=["POST"])
def refresh_production(account: str | None = None):
	from masters_association.solar_monitor import production

	accounts = enabled_accounts(account)
	rows = frappe.get_all(
		"Solar Station", filters={"account": ["in", accounts or [""]], "present": 1}, pluck="name"
	)
	result = {"Queued": 0, "Running": 0, "Cached": 0}
	for station in rows:
		try:
			state = production.enqueue(station)["status"]
		except service.Busy:
			# Another request is queueing this station right now.
			state = "Running"
		result[state] += 1
	return result


@frappe.whitelist(methods=["POST"])
def check_alerts(account: str | None = None):
	"""Queue an alert check covering every present station of one or all of the member's accounts."""
	result = {"Queued": 0, "Running": 0, "Cached": 0}
	for name in enabled_accounts(account):
		try:
			state = alerts.enqueue(name)["status"]
		except service.Busy:
			state = "Running"
		result[state] += 1
	return result
