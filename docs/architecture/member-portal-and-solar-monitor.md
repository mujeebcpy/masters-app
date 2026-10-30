# Member portal and Solar Monitor

This document records the account boundary implemented in Masters Association and the Solar Monitor
ownership model migrated from `wahni_solar`. Member-owned provider connections, the `/solar` monitoring
pages and the read-only global viewer role are implemented. Automatic polling, a solar manager role and
public solar statistics remain **future work**; the homepage shows no solar cards and never calls providers.

## Current account and permission model

`User` owns authentication, password policy and sessions. `Association Member` owns the member profile.
Its unique, staff-controlled `user` Link provides a one-to-one relationship; document `owner` is not an
authorization key because staff and imports create member records. A member record remains the stable
business identity when the login email changes.

| Role | Account and access | Status |
| --- | --- | --- |
| Association Member | Website User; edit own eligible member profile through the portal | Implemented |
| Masters Manager | System User; manage Masters members, approval, website content and new-account invitations | Implemented |
| Solar Monitor Viewer | Desk role; read all members' monitoring data at `/solar` and in Desk lists; no credential changes, refreshes or management | Implemented, explicitly assigned |
| Solar Monitor Manager | Manage all members' monitoring accounts, ownership, refreshes and settings | Future, explicitly assigned |
| System Manager / Administrator | Site administration, role assignment and explicit existing-User linkage | Frappe administration |

The member role has `desk_access=0` and no general Association Member CRUD permissions. Masters Manager
has Desk access, with Masters permissions separated from other installed apps. Automatic roles such as
`All`, `Guest` and `Desk User` must not grant Masters accounts business access to another app; explicit
additional roles and normal Frappe document/user permissions still apply. A System Manager retains site
administration rights. An unchecked whitelisted method, SQL query or `get_all` in another app still needs
its own authorization: menus and this app's permission hooks cannot secure an unrelated permission bypass.

`Solar Monitor Viewer` keeps Desk access so staff can use the read-only Desk lists, but grants only read
on solar DocTypes (permlevel 0, so identifying account configuration stays hidden) and no ERPNext roles.
System Manager has the same read-only solar access; Administrator bypasses DocPerm in Desk but the portal
methods still refuse its writes, because only the owning member may manage an account.

Every protected member operation calls `get_session_member()`, which checks the enabled session User,
member role, exactly one linked member, `portal_enabled`, Approved application status and Normal/Lifetime
membership. Pending, Rejected or Not A Member records have no member portal access. Revoking eligibility
blocks the portal immediately without deleting the User or removing deliberately granted permissions
for another app. The existing public directory remains governed by approval and visibility settings.

### External application RPC access

Masters accounts also have a request guard after cookie/OAuth/API-key authentication. External installed
apps' RPC methods are denied by default, including methods that use `get_all` without checking document
permissions. Giving a user an explicit business role permits its normal REST operations but does not
automatically unlock an app's whitelisted methods. Frappe authentication, REST, framework methods and
Masters portal methods keep their normal authorization checks. Guests, ordinary unrelated staff and
System Managers retain their existing behavior.

An administrator can opt in an **audited exact method** in site configuration, with a target DocType,
permission operation and eligible roles. For example, using placeholder application/DocType names:

```json
{
  "masters_external_rpc_permissions": {
    "example_app.api.get_status": {
      "doctype": "Example Record",
      "permission": "read",
      "roles": ["Example Reader"]
    }
  }
}
```

Replace the placeholders with the vetted endpoint and its actual business permission. The account must
hold a listed role that has the requested operation on that DocType in **effective** permission metadata
(including Custom DocPerm), at level 0, with a grant that is not owner-only. Automatic roles and Masters
roles cannot satisfy this requirement. An unrelated additional role, a permission at a higher field
level or an owner-only grant does not unlock an unchecked endpoint. Prefix/app-wide entries are ignored;
configure the full effective dotted method name after any Frappe method override. Audit the endpoint's
row filtering and returned fields before enabling it; the configuration is not a substitute for fixing
an unsafe application endpoint.

The guard resolves legacy `cmd` before API routing, matching Frappe dispatch precedence, then supports
v1/v2 dotted methods and v2 short DocType methods through Frappe's API route map. Run it after any custom
authentication hook that changes the session user. Normal generic REST and framework document methods
continue using Frappe and the app's document/query permission hooks.

The same external-method policy covers callbacks delegated through Frappe's tree `get_all_nodes`
(`tree_method`), upload handlers (`method`, including the native v2 upload route), and custom Link/search
queries (`query`, including a configured `standard_queries` fallback). Invalid callback types fail
closed. Callback overrides follow the actual wrapper: tree callbacks apply Frappe overrides; upload and
search callbacks use their supplied dotted path directly. Ordinary framework uploads and searches
without external callbacks remain available.

The optional `/api/v2/mcp` endpoint is denied entirely for scoped member/manager accounts, including
when site MCP support is enabled. These accounts use the portal and normal REST APIs; external RPC
configuration does not enable MCP. Administrators and unrelated users retain Frappe's existing behavior.

## Portal behavior and operations

- Login and password setup/reset use Frappe authentication. Members land at `/member/profile`; account
  settings live at `/member/account`. Anonymous visitors authenticate through `/login`.
- Direct edits cover name, designation, WhatsApp phone, district, Google Maps link, directory/contact
  visibility and the four existing project/capacity statistics. Counts/capacities remain nonnegative
  whole numbers, matching the current DocType. Their units are not reinterpreted as monitoring data.
- GST identity/details, membership class, approval, positions, payments, bank details, review notes,
  User linkage and portal eligibility remain staff-controlled. Server payload allowlists enforce this.
- The member is the source of truth for name, phone and photo. These synchronize to the linked User;
  alternate generic User/profile edits cannot silently create a second divergent member profile.
- Profile writes require the last `modified` timestamp. A stale editor must reload before saving.
- Photo upload validates and re-encodes JPG/PNG pixels, up to 5 MB and 4096 × 4096 pixels, attaches the File to that member's
  `photo`, and synchronizes the User avatar. Portraits use public `/files` URLs for the existing public
  directory. Hiding a directory entry does not make a previously public file private.
- Maps input retains coordinate extraction and address geocoding. Server resolution accepts HTTPS
  Google Maps hosts/paths only, validates every short-link redirect and never fetches an arbitrary
  submitted URL. Unsupported legacy links remain stored but produce no resolved pin.

Newly eligible approved members are provisioned after the member transaction commits. A new enabled
Website User receives only the member role and the standard Frappe password-setup invitation. Missing
email, an existing User collision, account creation failure or invitation failure is recorded in
`account_setup_error`; approval remains saved. Correct the problem and use **Retry Account Setup** or
**Send Invitation**. A retry reuses the linked account instead of creating a duplicate. Running workers
and correctly configured outgoing email are required.

An existing email is never automatically claimed, downgraded or silently linked. A System Manager uses
**Link Existing User**, reviews the member/User comparison, then confirms. Member name, phone and photo
become the User profile; the existing login email and permissions are preserved. A User already linked
to another member is rejected. Masters Manager alone cannot perform this linkage or assign arbitrary
User roles.

Members change their single contact/login email through account settings, with current-password
confirmation and a one-use verification link sent to the new address. The token expires after 30
minutes and confirmation requires the current account session. The old address works until confirmation.
Confirmation rechecks uniqueness, renames the Frappe User without merging, updates Link fields and the
member email atomically, notifies the old address and requires login with the new address. Generic
self-renames cannot bypass verification. Password changes use Frappe's standard old-password/reset-key
flow and configured password policy; direct User password setters are guarded for linked members.

### Backend interface

Methods below are under `masters_association.member_portal`, called through the existing
`/api/v2/method/<dotted method>` convention. Writes use POST with the Frappe session and CSRF protection.
Self-service methods derive the member from the session, never a submitted member/User identifier.

| Method | Inputs / purpose |
| --- | --- |
| `get_session` (GET) | Safe session and member-access status; available to guests |
| `get_my_profile` (GET) | Allowlisted own profile and current `modified` timestamp |
| `update_my_profile` | `data`, `modified`; validated profile changes |
| `upload_my_photo` | `photo` (encoded content), `photo_name`, `modified` |
| `remove_my_photo` | `modified`; clear profile photo/avatar |
| `request_email_change` | `new_email`, `current_password` |
| `confirm_email_change` | `token`; confirmed email and `login_required` result |
| `create_member_user` | Staff-only `member_name`; provision/retry an eligible account |
| `send_member_invitation` | Staff-only `member_name`; resend password setup |
| `get_user_link_preview` (GET) | System Manager-only `member_name`, `user`; compare before linkage |
| `link_member_user` | System Manager-only `member_name`, `user`; explicit linkage |

Deployment runs the normal `bench --site <site> migrate` and frontend build. The migration replaces
app-owned Membership Reviewer references with Masters Manager and preserves unrelated role grants and
site customizations. If another app still uses the old role, it is retained for that use. Migration
does not bulk-create accounts or send invitations to existing approved members: provision these
individually after reviewing their email and eligibility. Verify one invitation, one portal login,
cross-member denial and the manager approval flow before inviting the remaining members.

## Solar Monitor ownership and administration

Implemented in `solar_monitor/access.py` and `solar_monitor/api.py`; see `solar_monitor/README.md` for
operations. Each Solar API Account has an immutable `member` Link set from the creating member's session; the
ownership graph is `Member -> API Account -> Station -> Device / Alert / Production`. All read, list,
count, summary, export, credential, test-connection and refresh methods enforce this graph on the server.
Members operate only on their own graph. The global viewer role enables cross-member reads only; no
membership or client-submitted filter can grant global access. A future manager role would add
cross-member management and ownership transfer, which are not implemented.

Retain provider adapters, encrypted Password fields, token renewal, cooldowns, bounded retries and job
deduplication from Wahni. Never return provider secrets, passwords or access/refresh tokens to the browser
or public API. Queueing checks ownership and current capability; jobs recheck authorization/eligibility
and ownership before execution. Bind OAuth state to the initiating session/member and target account;
validate it again on callback. Ownership transfers and account disablement invalidate pending access.

Every overview aggregate and count, including unpaginated totals, search and "all accounts" actions,
applies the session ownership filter. The Wahni Desk dashboard page was replaced by the Masters Vue
portal (`/solar`, `/solar/station/<name>`, `/solar/accounts`); Desk exposes only read-only lists.

Provider polling remains manual until an operator configures an approved schedule and request budget.
Enphase and Deye have different quotas/reporting cadence. Reverify the current provider contracts when
copying the integrations; do not infer that a supported per-minute rate permits continuous polling under
a monthly quota. Public traffic must never enqueue refreshes or call a provider.

## Future public homepage totals

The agreed homepage measures are **monitored canonical physical plants**, not members' self-reported
installation statistics: installed capacity, lifetime energy production, total stations and today's
energy production. Keep capacity in kW and energy in kWh internally; format MW/MWh only for display.
The reporting day is `Asia/Kolkata`. All eligible participating members contribute anonymous totals
under a separately documented publication policy; member details remain private.

- Establish a canonical physical-plant identity before aggregation. Wahni's current unique key uses
  account plus external ID and cannot deduplicate one plant seen through two members' accounts. Provider,
  region and external identity must be reconciled, with staff resolution for overlapping sources.
  Count and sum one canonical plant once; do not add two provider views of the same production.
- Use eligible, enabled accounts and current inventory. Normalize Deye and Enphase units and honor
  reading-availability flags. Enphase capacity may arrive only after its first production update.
  Missing readings remain unavailable rather than becoming zero. Report coverage for capacity and
  each energy measure so partial totals are recognizable.
- Today's energy must describe one Asia/Kolkata calendar day. Station-local daily counters from another
  timezone cannot simply be summed into that day; obtain an appropriate history/time series or exclude
  them with explicit coverage until supported. Persist daily history if a graph is added later: the
  source implementation currently stores only the latest snapshot.
- A background process creates a safe, site-scoped public snapshot/cache with aggregate numbers,
  reporting date, coverage and freshness only. Exclude member/account/station identifiers, names,
  locations, credentials, detailed errors and per-member drilldowns. The guest homepage endpoint reads
  this limited snapshot; it never reuses an authenticated cross-member response.
- Preserve the last successful snapshot during provider failures, showing its age and partial coverage.
  Do not label a collection as freshly updated because only one station succeeded. At day rollover,
  yesterday's daily number must not appear as today's. If no readings exist, show unavailable instead
  of fabricated zeroes. No public solar cards or placeholder totals are added by the current portal work.

Before enabling this phase, document the publication/participation policy, provider budget and refresh
schedule, canonical-plant reconciliation and treatment of unsupported timezones. Keep those operational
decisions with the future module implementation and operator setup.

## Acceptance checks

Current portal tests cover provisioning/retry/collision, explicit existing-account linkage, role
boundaries, revoked access, member A versus B, protected-field payloads, stale profile edits, image
validation/avatar synchronization, password bypasses, and email expiry/replay/collision/atomic rename.
Maps tests mock all HTTP and cover hostile hosts/ports, private-address redirects, redirect loops,
valid short links, coordinates and fixed-endpoint geocoding.

`solar_monitor/tests/test_access.py` covers member A versus B, global viewer/System Manager read-only
access, REST denial, secret redaction, per-member labels, revoked eligibility during queued work and
OAuth state binding. Future solar tests must additionally cover a manager role, ownership reassignment, secret redaction, cross-account duplicate plants, provider unit
normalization, missing/zero/stale readings, midnight rollover and timezones, partial provider failures,
coverage, safe public responses and proof that homepage requests never call providers or enqueue jobs.
