"""The single authorization layer for Solar Monitor data.

Ownership graph: Association Member -> Solar API Account -> Station -> Device / Alert.
Members have no DocPerm on solar DocTypes, so every portal read uses get_all with an
explicit ownership filter derived from the session, never from client input. Global
viewers read everything and change nothing; only the owning member manages an account.
"""

import frappe
from frappe import _

from masters_association import member_portal

ACCOUNT = "Solar API Account"
VIEWER_ROLE = "Solar Monitor Viewer"
GLOBAL_ROLES = frozenset({"System Manager", VIEWER_ROLE})


def _deny(message=None):
	frappe.throw(message or _("You do not have access to this solar monitoring data."), frappe.PermissionError)


def can_view_all(user=None):
	user = user or frappe.session.user
	return user == "Administrator" or bool(GLOBAL_ROLES.intersection(frappe.get_roles(user)))


def _session_member():
	if frappe.session.user == "Guest":
		return None
	try:
		return member_portal.get_session_member()
	except frappe.PermissionError:
		frappe.clear_last_message()
		return None


def get_scope():
	"""Return {member, can_view_all}; a user with neither capability is denied."""
	scope = frappe._dict(member=_session_member(), can_view_all=can_view_all())
	if not scope.member and not scope.can_view_all:
		_deny(_("Please log in with an eligible member account to use the solar monitor."))
	return scope


def session_access():
	"""Safe value for the portal session: "all", "own" or None. Never throws."""
	if frappe.session.user == "Guest":
		return None
	if can_view_all():
		return "all"
	return "own" if _session_member() else None


def require_member():
	member = _session_member()
	if not member:
		_deny(_("Only an eligible member can manage solar API accounts."))
	return member


def account_filters(scope, member_filter=None):
	if not scope.can_view_all:
		return {"member": scope.member.name}
	return {"member": member_filter} if member_filter else {}


def require_account(name, write=False):
	"""Read: owner or global viewer. Write/refresh: owner only."""
	owner = frappe.db.get_value(ACCOUNT, name, "member") if name else None
	if not owner:
		_deny()
	if write:
		member = require_member()
		if member.name != owner:
			_deny()
		return member
	scope = get_scope()
	if not scope.can_view_all and scope.member.name != owner:
		_deny()
	return scope


def require_station(name, write=False):
	account = frappe.db.get_value("Solar Station", name, "account") if name else None
	if not account:
		_deny()
	require_account(account, write=write)
	return account


def member_active(member_name):
	"""Whether provider calls may run for an account owned by this member (rechecked by jobs)."""
	if not member_name:
		return False
	member = frappe.db.get_value(
		member_portal.MEMBER,
		member_name,
		["user", "portal_enabled", "application_status", "membership_status"],
		as_dict=True,
	)
	if not member or not member.user or not member_portal.is_eligible(member):
		return False
	return bool(frappe.db.get_value("User", member.user, "enabled"))
