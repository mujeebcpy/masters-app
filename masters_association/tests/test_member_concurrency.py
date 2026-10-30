"""Provisioning race against separate DB connections on a disposable test site.

This test commits its uniquely identified fixtures so independent workers can
see them. It deletes only those fixtures afterward, including on assertion failure.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.tests import IntegrationTestCase

from masters_association import member_portal as portal


class TestMemberProvisioningConcurrency(IntegrationTestCase):
	def test_two_workers_create_one_user_and_one_invitation(self):
		site = frappe.local.site
		if not (site.startswith(("test_", "test-", "test.")) or "portal-test" in site):
			self.skipTest("Committed concurrency fixtures require a disposable test site.")
		sites_path = frappe.local.sites_path
		frappe.set_user("Administrator")
		suffix = uuid4().hex
		email = f"portal-race-{suffix}@example.com"
		fixture_name = f"Portal concurrency {suffix}"
		gst = f"PORTAL-RACE-{suffix}"
		self.enterContext(patch("frappe.enqueue"))
		mail = self.enterContext(patch("frappe.sendmail"))
		member = frappe.get_doc(
			{
				"doctype": portal.MEMBER,
				"name1": fixture_name,
				"email": email,
				"mobile_no_whatsapp": "+919876543210",
				"district": "Thrissur",
				"gst": gst,
				"membership_status": "Normal Member",
				"portal_enabled": 1,
			}
		).insert(ignore_permissions=True)
		member.db_set("application_status", "Approved")
		member_name = member.name

		def cleanup():
			frappe.set_user("Administrator")
			frappe.db.rollback()
			stored = frappe.db.get_value(portal.MEMBER, member_name, ["email", "name1", "gst"], as_dict=True)
			if stored:
				self.assertEqual((stored.email, stored.name1, stored.gst), (email, fixture_name, gst))
				frappe.delete_doc(portal.MEMBER, member_name, ignore_permissions=True, force=True)
			if frappe.db.exists("User", email):
				self.assertEqual(frappe.db.get_value("User", email, "first_name"), fixture_name)
				frappe.delete_doc("User", email, ignore_permissions=True, force=True)
			frappe.db.commit()
			frappe.clear_cache(user=email)

		self.addCleanup(cleanup)
		frappe.db.commit()
		start = Barrier(2, timeout=15)

		def provision():
			try:
				# Each worker gets its own frappe.local and real database connection.
				frappe.init(site, sites_path=sites_path, force=True)
				frappe.connect()
				connection_id = id(frappe.local.db)
				frappe.flags.mute_emails = True
				if frappe.db.db_type == "mariadb":
					frappe.db.sql("SET SESSION innodb_lock_wait_timeout = 15")
				start.wait()
				result = portal.provision_member_user(member_name)
				frappe.db.commit()
				return result, connection_id
			except Exception:
				if getattr(frappe.local, "db", None):
					frappe.db.rollback()
				raise
			finally:
				frappe.destroy()

		with ThreadPoolExecutor(max_workers=2) as workers:
			futures = [workers.submit(provision) for _ in range(2)]
			completed = [future.result(timeout=45) for future in futures]
		# Discard any main-connection snapshot from metadata reads before the race.
		frappe.db.rollback()
		self.assertEqual(len({connection_id for _, connection_id in completed}), 2)
		for result, _ in completed:
			self.assertFalse(result.get("error"), result)
			self.assertEqual(result["user"], email)
		self.assertEqual(frappe.db.count("User", {"name": email}), 1)
		self.assertEqual(frappe.db.count(portal.MEMBER, {"user": email}), 1)
		self.assertEqual(frappe.db.get_value(portal.MEMBER, member_name, "user"), email)
		self.assertFalse(frappe.db.get_value(portal.MEMBER, member_name, "account_setup_error"))
		self.assertEqual(mail.call_count, 1)
		self.assertEqual(mail.call_args.kwargs["recipients"], email)
