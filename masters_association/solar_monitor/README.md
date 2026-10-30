# Solar Monitor

## Access model

Each Solar API Account belongs to one Association Member (`member`, set from the session and immutable). Stations, devices and alerts inherit it (`member` fetched from the account). All authorization lives in `access.py`; portal methods are in `api.py`.

| Who | Can |
| --- | --- |
| Eligible Association Member | Add, edit and disable **own** API accounts in the portal at `/solar/accounts`; test, authorize, fetch inventory, update production and check alerts for **own** accounts; view own dashboard at `/solar` |
| Solar Monitor Viewer, System Manager, Administrator | Read every member's accounts (status fields only), stations, devices, production and alerts at `/solar` (member filter) and in Desk lists. No create/write/delete and no provider calls, so viewers never use a member's API quota |

Members have no DocPerm on solar DocTypes; their REST access is denied and every portal query applies an explicit ownership filter from the session. Secrets are write-only: the portal reports only whether each is saved. Identifying configuration fields (app ID, email, company ID, client ID, usernames) are permlevel 1, which no role can read in Desk. Every provider call goes through `service.account_doc`, which rechecks that the owning member is still eligible, so revoking membership stops queued jobs. Account labels are unique per member.

Members create a Deye account with region, app ID, app secret, email, **normal password**, and company ID. Save and use **Test connection**, then **Fetch stations & devices**. Workers must be running; inventory is fetched on the long queue. Dashboard navigation reads saved records only.

Company details are fetched once when missing during the first successful connection/fetch. Failed discovery does not break authentication or repeat automatically. Use **Fetch / Update Company Details** to retry or update. Company names are Deye-only display labels; API calls use company/station IDs and tokens.

Access and refresh tokens are encrypted Password values, never returned by dashboard methods. Access tokens are reused until five minutes before expiry. Phase 1 renews through the documented login endpoint with saved credentials; refresh-token exchange is intentionally not assumed. Tokens and inventory are never polled; see *API usage and daily refresh* for the scheduled production and alert refresh. API secrets and the site's encryption key must be included in appropriate protected backup procedures.

Solar Monitor Settings controls cooldown (120 seconds), renewal margin (300 seconds), and app/region request rate (30/minute). The configured rate applies across account records sharing application credentials. HTTP 429/5xx requests use bounded backoff. Pending inventory jobs are reused for up to two hours before stale job recovery.

Solarman accounts can be saved disabled for future use; its integration is not implemented yet. Deye and Enphase production snapshots are available as described below.

## Enphase (Monitoring API v4)

Create an account with provider **Enphase** and enter the **Client ID**, **Client Secret** and **API Key** of the application from the Enphase developer portal (the numeric application ID is not used by the API). Save, then click **Authorize with Enphase** in the portal: open the Enphase sign-in, log in with the installer (or system owner) Enlighten account, approve access and paste the code shown on the Enphase page (pasting the whole address from the browser bar also works). The account is now connected; use **Fetch Stations & Devices** as for Deye.

- **Automatic callback (optional):** set Redirect URI to `https://<site>/api/method/masters_association.solar_monitor.api.enphase_callback` and register the same URI on the Enphase application. Authorize then returns to `/solar/accounts` without pasting a code. The OAuth state is bound to the member's session and rechecked against the account owner.
- **Partner plan (recommended, our plan):** fill Enlighten Username/Password with the installer login. The server then gets and renews tokens with the password grant on its own, so **Test Connection** works without the browser step and an expired refresh token never needs re-authorization.
- Access tokens last one day and are renewed with the refresh token (valid one month). If the refresh token expires (e.g. the account was not used for a month) without Partner credentials, the connection shows an error asking to authorize again.
- Each request sends the OAuth bearer token and the API key (`key` header). Requests are paced per application by **Enphase Requests Per Minute** (Solar Monitor Settings, default 300, the Partner plan limit). Per-minute 429s are retried with backoff. A 429 for the monthly quota is reported instead of retried.
- API usage: see *API usage and daily refresh* below. Mind the plan's monthly quota (Partner: 10,000 free hits per application).
- Production: power from the summary's `current_power` (W), today from `energy_today` (Wh), lifetime from `energy_lifetime` (until yesterday) + today, this month from lifetime until yesterday minus the cached lifetime before the 1st (`summary_date` = the 1st, read once a month, free on the 1st) + today; the `energy_lifetime` daily series is the fallback when that baseline is unusable. Installed capacity comes from the summary's `size_w` and is filled on the first production update. Enphase gateways report every 15 minutes, so readings are flagged stale only after 30 minutes.
- Alerts use `/open_alarms`, which returns every currently open alarm, so open Enphase alerts not returned anymore are closed (no lookback window). Severity: FATAL/ERROR → Critical, WARNING → Warning, others → Notice. Alarm names come from `/systems/event_types`, cached for a week for all accounts. A normal alert check reads `/systems` (status of up to 100 systems per hit) and calls `/open_alarms` only for systems that are not *normal* or still have open alerts; the Sunday scheduled check sweeps every system.
- Station connection shows the Enlighten system status (e.g. System Normal, Envoy Not Reporting); only System Normal counts as online.

Tests (inside the bench container, on a site with `allow_tests`):

```sh
for m in test_access test_service test_production test_alerts test_enphase; do
  bench --site <site> run-tests --module masters_association.solar_monitor.tests.$m
done
```

The Desk workspace (`/app/solar-monitor`) lists the read-only DocTypes and links to the portal dashboard.

## Production dashboard

API accounts are named by their Account Label. Station names are used for station record names; device names use `device type - station name`. Collisions get a numeric suffix (`Plant-1`). The identity key still uses account plus external identifier, so repeat imports update existing records.

Fetch inventory after a reset, then click **Update production** to queue all of your enabled stations (or the selected account), or open a station and use its **Update production** button. Click a station name for saved production details, devices and alerts.

Cards aggregate all present stations in the selected member/provider/account, independent of the table's pagination or search. Readings show coverage and stale counts; missing energy is not displayed as zero. Today/month rollover follows station timezone. Individual updates use a configurable cooldown (Deye 300 seconds, Enphase 900 seconds) and pending-job reuse. Deye workers read latest power from a shared `/station/list` (cached four minutes per account) and the current month's daily energy; lifetime is the cached lifetime before this month plus this month, rebuilt from annual readings since commissioning (or year 2000) once a month. No production requests happen on navigation.

All timestamps are stored and shown in the site time zone (System Settings → Time Zone, e.g. Asia/Kolkata for UTC+05:30). Station today/month rollover still follows each station's own time zone.

## Alerts

The dashboard shows open alerts first. **Check alerts** queues one long-queue job per enabled account of the member (or the selected account) that calls `/v1.0/station/alertList` for every present station, covering the last *Alert Lookback* days (Solar Monitor Settings, default 30, Deye maximum 180). Alerts are saved as Solar Alert records; the daily refresh also checks them. A failing station is reported on the account without discarding the stations that succeeded.

Severity comes from Deye's `impact` (0 none, 1 production, 2 safety, 3 production & safety) and `level` (0 notice, 1 warning, 2 failure):

- **Critical** (needs immediate installer attention): safety impact (2 or 3) or failure level (2).
- **Warning**: production impact (1) or warning level (1).
- **Notice**: everything else.

Open alerts are listed Critical first, then newest first. Open alerts inside the checked window that Deye no longer returns are closed.

## API usage and daily refresh

Every provider request is counted per developer application (Enphase client ID, Deye region + app ID) for the calendar month and shown on the account (**API hits this month**). OAuth token requests are not counted. Once an Enphase application reaches **Enphase Monthly Hit Budget** (Solar Monitor Settings, default 9,000 of the Partner plan's 10,000 free hits), further Enphase calls fail with a clear message until next month.

A scheduled job (`masters_association.solar_monitor.schedule.daily_refresh`, 19:00 system time) queues a production update for every present station of each enabled account and a triaged alert check (a full sweep on Sundays). Accounts that are disabled, whose owner is no longer eligible, or over budget are skipped.

| Enphase action (N stations) | Calls |
| --- | --- |
| Fetch stations & devices | 1 per 100 systems + 1 per **new** system (**Refresh all devices**: + 1 per system) |
| Production update | 1 per station (+1 on the month's first update when it is not the 1st) |
| Alert check | 1 per 100 systems + 1 per station that is not normal or has open alerts (Sunday: + 1 per station) |

Example: 90 stations with the daily refresh use about 90 × 30 (production) + 90 (monthly baselines) + 30 × (1 + problem stations) + 4 × 90 (Sunday sweeps) ≈ 3,500 hits a month, against about 8,200 before these optimizations. Enphase has no multi-system production endpoint (`/systems/summary` returns 404), so production stays one call per station.

Deye: a production update costs one `/station/history` call per station plus one shared `/station/list` call per 200 stations (yearly history once a month); alerts cost one call per station per page.
