"""Keep native File operations from bypassing the canonical member portrait.

Frappe may attach the same blob to both Member.photo and User.user_image.
Changing a File's privacy can move that blob and write a User field directly,
without running User validation. Protect both aliases and prior attachment
values, and check destructive controller methods before they touch the disk.
"""

import frappe
from frappe import _

MEMBER = "Association Member"


def _trusted_photo_operation():
	from masters_association.member_portal import _trusted_operation

	return bool(_trusted_operation.get().intersection({"identity", "photo"}))


def _snapshots(doc):
	previous = None
	if doc.name:
		# Controller-method RPC can construct a File from client-provided data.
		# It may spoof attachment metadata, __islocal or _doc_before_save;
		# always retrieve the persisted identity before destructive operations.
		previous = frappe.db.get_value(
			"File",
			doc.name,
			["file_url", "content_hash", "attached_to_doctype", "attached_to_name", "attached_to_field"],
			as_dict=True,
		)
	return (doc, previous) if previous else (doc,)


def _is_existing_file(doc):
	# Native document-method RPC accepts a client document, including __islocal.
	# That marker cannot authorize an overwrite of an existing File record.
	return not doc.is_new() or bool(doc.name and frappe.db.exists("File", doc.name))


def _references_member_portrait(doc):
	snapshots = _snapshots(doc)
	urls = {row.get("file_url") for row in snapshots if isinstance(row.get("file_url"), str)}
	hashes = {row.get("content_hash") for row in snapshots if isinstance(row.get("content_hash"), str)}
	# Native privacy changes rewrite every File with the same content hash, even
	# when two aliases have different URLs. Protect those references as well.
	if hashes:
		urls.update(
			frappe.get_all("File", filters={"content_hash": ["in", sorted(hashes)]}, pluck="file_url")
		)
	urls.discard("")
	urls.discard(None)
	return bool(urls and frappe.db.exists(MEMBER, {"user": ["is", "set"], "photo": ["in", sorted(urls)]}))


def _targets_linked_user_field(doc):
	# A fresh unrelated file with attached_to_field=user_image (or even an
	# arbitrary User data field) can otherwise be used for a later privacy move
	# that calls db.set_value(User, ...), bypassing the User profile guard.
	return any(
		row.get("attached_to_doctype") == "User"
		and row.get("attached_to_name")
		and row.get("attached_to_field")
		and frappe.db.exists(MEMBER, {"user": row.get("attached_to_name")})
		for row in _snapshots(doc)
	)


def _guard_member_file(doc, *, deleting=False):
	if _trusted_photo_operation() or frappe.flags.in_install or frappe.flags.in_migrate:
		return
	if (not deleting and _targets_linked_user_field(doc)) or (
		(_is_existing_file(doc) or deleting) and _references_member_portrait(doc)
	):
		frappe.throw(
			_("Use the Association Member profile to change or remove a member photo."),
			frappe.PermissionError,
		)


def validate_member_file(doc, method=None):
	"""File before_validate hook: runs before native privacy moves or URL rewrites."""
	_guard_member_file(doc)


class MemberPhotoFileMixin:
	def on_trash(self):
		# A doc_events on_trash hook runs after File.on_trash has deleted the
		# physical blob; an extension must check before calling the controller.
		_guard_member_file(self, deleting=True)
		return super().on_trash()

	def save_file(self, *args, **kwargs):
		# File.optimize_file writes bytes before calling save()/before_validate.
		# Intercept that write too, without changing unrelated upload behavior.
		if _is_existing_file(self):
			_guard_member_file(self)
		return super().save_file(*args, **kwargs)
