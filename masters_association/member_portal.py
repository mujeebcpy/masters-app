"""Member self-service. Authentication belongs to User; membership belongs to the member.

The portal role deliberately has no Association Member DocPerm. Every permission
bypass below follows session-derived ownership, eligibility and payload checks.
ContextVars authorize internal identity writes; document/client flags cannot.
"""

import hashlib
import hmac
import re
import secrets
import warnings
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import timedelta
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.model.rename_doc import rename_doc
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, get_datetime, get_url, now_datetime, validate_email_address
from frappe.utils.html_utils import escape_html

MEMBER = "Association Member"
PORTAL_ROLE = "Association Member"
MANAGER_ROLE = "Masters Manager"
EMAIL_REQUEST = "Member Email Change Request"
MAX_PHOTO_SIZE = 5 * 1024 * 1024
STAT_FIELDS = frozenset(
	{
		"total_mnre_projects_done_till_date",
		"total_capacity_done_till_this_date",
		"total_number_of_hybrid",
		"total_storage_capacity_of_hybrid",
	}
)
EDITABLE_FIELDS = (
	frozenset(
		{
			"name1",
			"designation",
			"mobile_no_whatsapp",
			"district",
			"google_maps_link",
			"show_on_website",
			"show_contact_on_website",
		}
	)
	| STAT_FIELDS
)
PROFILE_FIELDS = (
	*sorted(EDITABLE_FIELDS),
	"name",
	"modified",
	"email",
	"photo",
	"membership_status",
	"gst_company_name",
)
_trusted_operation = ContextVar("masters_member_operation", default=frozenset())


@contextmanager
def _trusted(*operations):
	token = _trusted_operation.set(_trusted_operation.get() | frozenset(operations))
	try:
		yield
	finally:
		_trusted_operation.reset(token)


def _is_admin():
	return frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()


def _require_manager(administrator_only=False):
	if frappe.session.user == "Guest" or not (
		_is_admin() or (not administrator_only and MANAGER_ROLE in frappe.get_roles())
	):
		frappe.throw(_("You do not have permission to manage member accounts."), frappe.PermissionError)


def is_eligible(member):
	return bool(
		cint(member.get("portal_enabled"))
		and member.get("application_status") == "Approved"
		and member.get("membership_status") in ("Normal Member", "Lifetime Member")
	)


def get_session_member(*, for_update=False):
	"""The sole authorization entry point for member and future solar operations."""
	user = frappe.session.user
	if user == "Guest" or not frappe.db.get_value("User", user, "enabled"):
		frappe.throw(_("Please log in to access your member profile."), frappe.PermissionError)
	if PORTAL_ROLE not in frappe.get_roles(user):
		frappe.throw(_("Your account does not have member portal access."), frappe.PermissionError)
	names = frappe.get_all(MEMBER, filters={"user": user}, pluck="name", limit=2)
	if len(names) != 1:
		frappe.throw(
			_("Your account is not linked to an association member. Please contact Masters."),
			frappe.PermissionError,
		)
	member = frappe.get_doc(MEMBER, names[0], for_update=for_update)
	# Recheck the link after acquiring the row lock, including reassignment races.
	if member.user != user or not is_eligible(member):
		frappe.throw(
			_("Your member portal access is currently unavailable. Please contact Masters."),
			frappe.PermissionError,
		)
	return member


def _profile(member):
	return {field: member.get(field) for field in PROFILE_FIELDS}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_session():
	user = frappe.session.user
	result = {
		"user": user,
		"is_logged_in": user != "Guest",
		"has_member_access": False,
		"member_name": None,
		"display_name": None,
		"photo": None,
		"reason": None,
		"solar_access": None,
		"has_desk_access": False,
	}
	if user == "Guest":
		return result
	result["has_desk_access"] = bool(frappe.get_doc("User", user).has_desk_access())
	from masters_association.solar_monitor.access import session_access

	result["solar_access"] = session_access()
	try:
		member = get_session_member()
	except frappe.PermissionError as exc:
		frappe.clear_last_message()
		result["reason"] = str(exc)
		return result
	result.update(
		has_member_access=True, member_name=member.name, display_name=member.name1, photo=member.photo
	)
	return result


@frappe.whitelist(methods=["GET"])
def get_my_profile():
	return _profile(get_session_member())


def _check_modified(member, modified):
	if not modified or get_datetime(member.modified) != get_datetime(modified):
		frappe.throw(
			_("Your profile has changed. Reload it before saving again."), frappe.TimestampMismatchError
		)


def _validate_profile_data(data):
	if isinstance(data, str):
		data = frappe.parse_json(data)
	if not isinstance(data, dict) or set(data) - EDITABLE_FIELDS:
		frappe.throw(_("Only editable profile fields may be updated."), frappe.PermissionError)
	for field, value in data.items():
		if field in STAT_FIELDS:
			if value in (None, ""):
				data[field] = 0
			elif isinstance(value, bool) or not re.fullmatch(r"[0-9]{1,10}", str(value)):
				frappe.throw(_("Project counts and capacities must be nonnegative whole numbers."))
			else:
				data[field] = int(value)
				if data[field] > 2_147_483_647:
					frappe.throw(_("Project counts and capacities must not exceed 2,147,483,647."))
		elif field in ("show_on_website", "show_contact_on_website"):
			if value not in (0, 1, "0", "1", True, False):
				frappe.throw(_("Invalid visibility setting."))
			data[field] = cint(value)
		elif value is not None and not isinstance(value, str):
			frappe.throw(_("Invalid profile field value."))
	return data


@frappe.whitelist(methods=["POST"])
def update_my_profile(data, modified):
	data = _validate_profile_data(data)
	member = get_session_member(for_update=True)
	_check_modified(member, modified)
	member.update(data)
	member.save(ignore_permissions=True)
	return _profile(member)


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=20, seconds=60 * 60)
def upload_my_photo(photo, photo_name, modified):
	from masters_association.photos import validate_profile_photo

	member = get_session_member(for_update=True)
	_check_modified(member, modified)
	content, image_format = validate_profile_photo(photo)
	with _trusted("photo"):
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{member.name}-profile.{'jpg' if image_format == 'JPEG' else 'png'}",
				"attached_to_doctype": MEMBER,
				"attached_to_name": member.name,
				"attached_to_field": "photo",
				"is_private": 0,
				"content": content,
			}
		).insert(ignore_permissions=True)
		member.photo = file.file_url
		member.save(ignore_permissions=True)
	return _profile(member)


@frappe.whitelist(methods=["POST"])
def remove_my_photo(modified):
	member = get_session_member(for_update=True)
	_check_modified(member, modified)
	with _trusted("photo"):
		member.photo = None
		member.save(ignore_permissions=True)
	return _profile(member)


def validate_member_account(member):
	"""Also enforce linkage/email invariants on Desk, imports and generic REST."""
	if member.has_value_changed("user") and member.get("user") and "link" not in _trusted_operation.get():
		frappe.throw(_("Use the member account actions to create or link a User."), frappe.PermissionError)
	if not member.is_new() and member.has_value_changed("user") and "link" not in _trusted_operation.get():
		frappe.throw(
			_("The linked User can only be changed through an account action."), frappe.PermissionError
		)
	if member.get("user") and member.email != member.user and "email" not in _trusted_operation.get():
		frappe.throw(
			_(
				"Change the login email through Member Account Settings or rename the User as an administrator."
			)
		)
	for field in STAT_FIELDS:
		if member.has_value_changed(field) and member.get(field) is not None:
			value = member.get(field)
			if (
				isinstance(value, bool)
				or not re.fullmatch(r"[0-9]{1,10}", str(value))
				or int(value) > 2_147_483_647
			):
				frappe.throw(_("Project counts and capacities must be nonnegative whole numbers."))


def member_updated(member):
	if member.get("user"):
		sync_user_profile(member)
	previous = member.get_doc_before_save()
	if (
		not member.get("user")
		and is_eligible(member)
		and (previous is None or not is_eligible(previous))
		and not any(frappe.flags.get(flag) for flag in ("in_install", "in_migrate", "in_patch"))
	):
		frappe.enqueue(
			"masters_association.member_portal.provision_member_user",
			member_name=member.name,
			enqueue_after_commit=True,
		)


def sync_user_profile(member):
	user = frappe.get_doc("User", member.user)
	values = {
		"first_name": member.name1,
		"middle_name": None,
		"last_name": None,
		"phone": member.mobile_no_whatsapp,
		"user_image": member.photo,
	}
	if any((user.get(field) or "") != (value or "") for field, value in values.items()):
		with _trusted("identity"):
			user.update(values)
			user.save(ignore_permissions=True)


def validate_user_account(doc, method=None):
	if doc.is_new():
		return
	member = frappe.db.get_value(MEMBER, {"user": doc.name}, "name")
	if not member:
		return
	if doc.get("new_password") and frappe.session.user == doc.name and not _is_admin():
		frappe.throw(
			_("Use Account Settings to change your password with your current password."),
			frappe.PermissionError,
		)
	if doc.has_value_changed("mobile_no") and frappe.session.user == doc.name and not _is_admin():
		frappe.throw(
			_("Contact an administrator to change your login mobile number."), frappe.PermissionError
		)
	if "identity" not in _trusted_operation.get():
		fields = ("first_name", "middle_name", "last_name", "phone", "user_image")
		if any(doc.has_value_changed(field) for field in fields):
			frappe.throw(
				_("Update your name, phone and photo through the Association Member profile."),
				frappe.PermissionError,
			)


def before_user_rename(doc, method=None, old_name=None, new_name=None, merge=False):
	if not frappe.db.exists(MEMBER, {"user": old_name}):
		return
	if merge or ("email" not in _trusted_operation.get() and not _is_admin()):
		frappe.throw(
			_("Use the verified member email-change process. Linked member accounts cannot be merged."),
			frappe.PermissionError,
		)


def after_user_rename(doc, method=None, old_name=None, new_name=None, merge=False):
	name = frappe.db.get_value(MEMBER, {"user": new_name}, "name")
	if name:
		with _trusted("email"):
			member = frappe.get_doc(MEMBER, name, for_update=True)
			member.email = new_name
			member.save(ignore_permissions=True)


class MemberUserMixin:
	"""Keep Frappe v16's session invalidation inside the identity transaction.

	User.after_rename clears sessions, whose delete_session normally commits.
	Use the same per-connection nesting guard as Document event hooks so the
	User, linked member, token and password rename commit together. No global
	method patching or replacement of the core User implementation is needed.
	"""

	def after_rename(self, old_name, new_name, merge=False):
		if not frappe.db.exists(MEMBER, {"user": new_name}):
			return super().after_rename(old_name, new_name, merge)
		sessions = frappe.qb.DocType("Sessions")
		session_ids = (
			frappe.qb.from_(sessions)
			.select(sessions.sid)
			.where(sessions.user.isin([old_name, new_name]))
			.run(pluck=True)
		)
		database = frappe.db
		database.after_rollback.add(lambda: _clear_identity_caches(old_name, new_name))
		database._disable_transaction_control += 1
		try:
			with warnings.catch_warnings():
				warnings.filterwarnings(
					"ignore", message="Commit/rollback are disabled during certain events.*"
				)
				super().after_rename(old_name, new_name, merge)
		finally:
			database._disable_transaction_control -= 1

		# Another request could reload a session cache entry before SQL commits.
		# Evict it again after commit, using the IDs captured before native deletion.
		def evict_sessions():
			_clear_identity_caches(old_name, new_name)
			for sid in session_ids:
				frappe.cache.hdel("session", sid)

		database.after_commit.add(evict_sessions)


def _clear_identity_caches(old_name, new_name):
	frappe.clear_cache(user=old_name)
	frappe.clear_cache(user=new_name)


def _normalize_email(value):
	if not isinstance(value, str):
		frappe.throw(_("Enter a valid email address."))
	email = (value or "").strip().lower()
	validate_email_address(email, throw=True)
	if not email or len(email) > 140:
		frappe.throw(_("Enter a valid email address."))
	return email


def _new_member_user(member):
	if not is_eligible(member):
		frappe.throw(_("Only approved, active members with portal access enabled can receive an account."))
	if member.get("user"):
		return {"user": member.user, "message": _("A User is already linked. Use Send Invitation if needed.")}
	email = _normalize_email(member.email)
	if frappe.db.exists("User", email):
		frappe.throw(
			_("This email already belongs to a User. A System Manager must link the existing account.")
		)
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": member.name1,
			"phone": member.mobile_no_whatsapp,
			"user_image": member.photo,
			"user_type": "Website User",
			"enabled": 1,
			"send_welcome_email": 0,
			"roles": [{"role": PORTAL_ROLE}],
		}
	).insert(ignore_permissions=True)
	# Link before sending: a failed invitation can be retried without a duplicate User.
	with _trusted("link", "email"):
		member.user = user.name
		member.email = user.name
		member.account_setup_error = None
		member.save(ignore_permissions=True)
	return {"user": user.name, "message": _("User created and linked.")}


def _record_setup_error(member_name, message):
	frappe.db.set_value(MEMBER, member_name, "account_setup_error", message, update_modified=False)
	return {"user": frappe.db.get_value(MEMBER, member_name, "user"), "error": message, "message": message}


def provision_member_user(member_name):
	"""Internal after-commit job and staff action. Never auto-link an existing User."""
	frappe.db.savepoint("member_account_setup")
	try:
		member = frappe.get_doc(MEMBER, member_name, for_update=True)
		already_linked = bool(member.get("user"))
		result = _new_member_user(member)
	except Exception as exc:
		frappe.db.rollback(save_point="member_account_setup")
		if isinstance(exc, frappe.ValidationError):
			message = str(exc)
		else:
			message = _("Account setup failed. An administrator can inspect the Error Log and retry.")
			frappe.log_error(title="Member account setup failed")
		return _record_setup_error(member_name, message)
	if not already_linked:
		return _send_invitation(member_name, result["user"])
	return result


@frappe.whitelist(methods=["POST"])
def create_member_user(member_name):
	_require_manager()
	frappe.get_doc(MEMBER, member_name).check_permission("write")
	return provision_member_user(member_name)


def _send_invitation(member_name, user):
	# Keep the linked account if email configuration/delivery fails.
	frappe.db.savepoint("member_invitation")
	try:
		frappe.get_doc("User", user).send_welcome_mail_to_user()
	except Exception:
		frappe.db.rollback(save_point="member_invitation")
		frappe.log_error(title="Member invitation failed")
		return _record_setup_error(
			member_name,
			_(
				"The User is linked, but the invitation could not be sent. Check outgoing email and use Send Invitation."
			),
		)
	frappe.db.set_value(MEMBER, member_name, "account_setup_error", None, update_modified=False)
	return {"user": user, "message": _("Password setup invitation sent.")}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=10, seconds=60 * 60)
def send_member_invitation(member_name):
	_require_manager()
	member = frappe.get_doc(MEMBER, member_name, for_update=True)
	member.check_permission("write")
	if (
		not member.get("user")
		or not is_eligible(member)
		or not frappe.db.get_value("User", member.user, "enabled")
	):
		frappe.throw(_("An eligible member and enabled linked User are required."))
	return _send_invitation(member.name, member.user)


def _existing_user_for_link(member_name, user, *, for_update=False):
	_require_manager(administrator_only=True)
	member = frappe.get_doc(MEMBER, member_name, for_update=for_update)
	member.check_permission("write")
	account = frappe.get_doc("User", user, for_update=for_update)
	if user in frappe.STANDARD_USERS or not account.enabled or not is_eligible(member):
		frappe.throw(_("Select an enabled personal account for an eligible member."))
	if account.user_type not in ("Website User", "System User"):
		frappe.throw(
			_("This account uses a custom User Type. An administrator must convert it before linking.")
		)
	if member.get("user") and member.user != user:
		frappe.throw(_("This member already has a linked User."))
	if frappe.db.exists(MEMBER, {"user": user, "name": ["!=", member.name]}):
		frappe.throw(_("This User is already linked to another member."))
	return member, account


@frappe.whitelist(methods=["GET"])
def get_user_link_preview(member_name, user):
	member, account = _existing_user_for_link(member_name, user)
	return {
		"member": {
			"name": member.name,
			"display_name": member.name1,
			"email": member.email,
			"phone": member.mobile_no_whatsapp,
			"photo": member.photo,
		},
		"user": {
			"name": account.name,
			"display_name": account.full_name,
			"email": account.email,
			"phone": account.phone or account.mobile_no,
			"photo": account.user_image,
			"user_type": account.user_type,
		},
		"message": _(
			"The member name, phone and photo will become the User profile. The existing login email and permissions are preserved."
		),
	}


@frappe.whitelist(methods=["POST"])
def link_member_user(member_name, user):
	member, account = _existing_user_for_link(member_name, user, for_update=True)
	if account.role_profiles:
		if not any(row.role_profile == "Masters Member Portal" for row in account.role_profiles):
			account.append("role_profiles", {"role_profile": "Masters Member Portal"})
	else:
		account.append_roles(PORTAL_ROLE)
	account.save(ignore_permissions=True)
	with _trusted("link", "email"):
		member.user = account.name
		member.email = account.name
		member.account_setup_error = None
		member.save(ignore_permissions=True)
	return {"user": account.name, "message": _("Existing User linked. Its permissions have been preserved.")}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60, ip_based=False, user_based=True)
def request_email_change(new_email, current_password):
	member = get_session_member(for_update=True)
	if not current_password:
		frappe.throw(_("Enter your current password."))
	# Current-password verification plus the account-based attempt limit above.
	frappe.local.login_manager.check_password(member.user, current_password)
	email = _normalize_email(new_email)
	if email == member.user or frappe.db.exists("User", email):
		frappe.throw(_("Choose a different email address that is not already in use."))
	token = secrets.token_urlsafe(32)
	frappe.db.delete(EMAIL_REQUEST, {"user": member.user})
	frappe.get_doc(
		{
			"doctype": EMAIL_REQUEST,
			"user": member.user,
			"new_email": email,
			"token_hash": hashlib.sha256(token.encode()).hexdigest(),
			"expires_at": now_datetime() + timedelta(minutes=30),
			"used": 0,
		}
	).insert(ignore_permissions=True)
	link = get_url("/member/account?" + urlencode({"email_token": token}), allow_header_override=False)
	frappe.sendmail(
		recipients=[email],
		subject=_("Verify your Masters account email"),
		message=_(
			"Confirm your new email using the link below while signed in to your current Masters account. The link expires in 30 minutes."
		)
		+ f'<br><br><a href="{escape_html(link)}">{_("Confirm email change")}</a>',
	)
	return {
		"message": _(
			"A verification link has been sent to your new email. Your current login remains active until confirmation."
		)
	}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=10, seconds=60 * 60, ip_based=False, user_based=True)
def confirm_email_change(token):
	member = get_session_member(for_update=True)
	if not isinstance(token, str) or not 20 <= len(token) <= 200:
		frappe.throw(_("This email verification link is invalid or expired."))
	request_name = frappe.db.get_value(EMAIL_REQUEST, {"user": member.user}, "name")
	if not request_name:
		frappe.throw(_("This email verification link is invalid or expired."))
	request = frappe.get_doc(EMAIL_REQUEST, request_name, for_update=True)
	if (
		request.user != member.user
		or request.used
		or get_datetime(request.expires_at) <= now_datetime()
		or not hmac.compare_digest(request.token_hash, hashlib.sha256(token.encode()).hexdigest())
	):
		frappe.throw(_("This email verification link is invalid or expired."))
	new_email = _normalize_email(request.new_email)
	if frappe.db.exists("User", new_email):
		frappe.throw(_("This email address is already in use. Request another email change."))
	old_email = member.user
	request.used = 1
	request.save(ignore_permissions=True)
	try:
		with _trusted("email"):
			rename_doc("User", old_email, new_email, merge=False, ignore_permissions=True, show_alert=False)
	except Exception:
		# Also support callers rolling back to a savepoint (no after_rollback hooks).
		_clear_identity_caches(old_email, new_email)
		raise
	frappe.sendmail(
		recipients=[old_email],
		subject=_("Your Masters login email has changed"),
		message=_(
			"Your Masters login email has changed to {0}. Contact Masters immediately if you did not request this."
		).format(escape_html(new_email)),
	)
	return {
		"email": new_email,
		"login_required": True,
		"message": _("Your email has been updated. Log in with your new address."),
	}
