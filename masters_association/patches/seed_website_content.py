import frappe

GALLERY_BASE = "/assets/masters_association/images"

EXPO_PHOTOS = [f"gallery/expo-2025-{i:02d}.jpg" for i in range(1, 13)]
ASSOCIATION_PHOTOS = [
	("photos/members-gathering.jpg", "Members gathering"),
	("photos/executive-committee.jpg", "Executive committee"),
	("photos/members-meeting.jpg", "General body meeting"),
	("photos/training-session.jpg", "Vendor training session"),
]


def execute():
	"""Seed the website gallery and documents with the content of the previous mastersassociation.org site.

	Only runs on a fresh install, so items edited or deleted by admins are never recreated.
	"""
	if not frappe.db.count("Gallery Item"):
		for idx, path in enumerate(EXPO_PHOTOS, 1):
			_add_gallery_item(f"Masters Expo 2025 - {idx}", path, "Masters Expo 2025", idx, show_on_home_page=1)

		for idx, (path, title) in enumerate(ASSOCIATION_PHOTOS, len(EXPO_PHOTOS) + 1):
			_add_gallery_item(title, path, "Association Meetings", idx)

	if not frappe.db.count("Association Document"):
		frappe.get_doc(
			{
				"doctype": "Association Document",
				"title": "Masters Brand Book",
				"category": "Brand",
				"description": "Logo print formats, colours and usage guidelines.",
				"file": "/assets/masters_association/docs/masters-brand-book.pdf",
				"display_order": 1,
			}
		).insert(ignore_permissions=True)


def _add_gallery_item(title, path, album, display_order, show_on_home_page=0):
	frappe.get_doc(
		{
			"doctype": "Gallery Item",
			"title": title,
			"media_type": "Photo",
			"album": album,
			"image": f"{GALLERY_BASE}/{path}",
			"display_order": display_order,
			"show_on_home_page": show_on_home_page,
		}
	).insert(ignore_permissions=True)
