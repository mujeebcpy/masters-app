<script setup>
import { computed, reactive, ref } from "vue"
import { Alert, Badge, Button, Dialog, FormControl, Skeleton, toast, useCall } from "frappe-ui"
import { errorText, solarMethod } from "@/api"
import { useMemberSession } from "@/member/session"
import { formatDateTime, statusTheme } from "@/solar/format"

const { session } = useMemberSession()
const accounts = useCall({ url: solarMethod("get_my_accounts") })
const save = useCall({ url: solarMethod("save_my_account"), method: "POST", immediate: false })
const ACTIONS = ["test_connection", "sync_inventory", "fetch_company_details", "disable_my_account", "enphase_authorize_url", "enphase_authorize"]
const actions = Object.fromEntries(ACTIONS.map((name) => [name, useCall({ url: solarMethod(name), method: "POST", immediate: false })]))
const pending = ref("")

const SECRETS = {
	Deye: [
		["app_secret", "App secret"],
		["password", "Deye account password"],
	],
	Enphase: [
		["client_secret", "Client secret"],
		["api_key", "API key"],
		["enphase_password", "Enlighten password (optional)"],
	],
}
const blank = () => ({
	name: null,
	account_label: "",
	provider: "Deye",
	region: "India",
	app_id: "",
	email: "",
	company_id: "",
	client_id: "",
	redirect_uri: "",
	enphase_username: "",
	app_secret: "",
	password: "",
	client_secret: "",
	api_key: "",
	enphase_password: "",
})
const form = reactive(blank())
const editing = ref(null)
const dialogOpen = ref(false)
const formError = ref("")
const enphase = reactive({ open: false, account: null, url: "", code: "", error: "" })
const memberOnly = computed(() => session.data && !session.data.has_member_access)

function openForm(account = null) {
	Object.assign(form, blank())
	editing.value = account
	if (account) {
		for (const key of Object.keys(form)) {
			if (key in account && !Object.values(SECRETS).flat().some(([field]) => field === key)) form[key] = account[key] ?? ""
		}
	}
	formError.value = ""
	dialogOpen.value = true
}

function payload() {
	const fields = ["account_label", "provider"]
	if (form.provider === "Deye") fields.push("region", "app_id", "email", "company_id")
	else fields.push("client_id", "redirect_uri", "enphase_username")
	const data = Object.fromEntries(fields.map((key) => [key, form[key]]))
	// Secrets are write-only: send only the ones typed in, so blank keeps the saved value.
	for (const [key] of SECRETS[form.provider]) if (form[key]) data[key] = form[key]
	return data
}

async function submit() {
	formError.value = ""
	try {
		await save.submit({ data: payload(), name: editing.value?.name })
		dialogOpen.value = false
		toast.success(editing.value ? "Account updated." : "Account added. Test the connection next.")
		accounts.reload()
	} catch (error) {
		formError.value = errorText(error)
	} finally {
		save.reset()
	}
}

async function call(name, account, params = {}) {
	pending.value = `${name}:${account.name}`
	try {
		return await actions[name].submit({ account: account.name, ...params })
	} catch (error) {
		toast.error(errorText(error))
		return null
	} finally {
		pending.value = ""
		actions[name].reset()
		accounts.reload()
	}
}

async function testConnection(account) {
	const result = await call("test_connection", account)
	if (!result) return
	if (result.status === "Connected") toast.success("Connected successfully.")
	else toast.error(`Connection failed: ${result.error}`)
}

async function fetchInventory(account, refreshDevices = false) {
	const result = await call("sync_inventory", account, refreshDevices ? { refresh_devices: 1 } : {})
	if (result) toast.success("Fetching stations and devices. This runs in the background.")
}

async function fetchCompany(account) {
	const result = await call("fetch_company_details", account)
	if (result) result.company_lookup_error ? toast.error(result.company_lookup_error) : toast.success(`Company: ${result.company_name}`)
}

async function disable(account) {
	if (await call("disable_my_account", account)) toast.success("Account disabled.")
}

async function startEnphase(account) {
	const result = await call("enphase_authorize_url", account)
	if (!result) return
	Object.assign(enphase, { open: true, account, url: result.url, code: "", error: "" })
	window.open(result.url, "_blank", "noopener")
}

async function finishEnphase() {
	enphase.error = ""
	const result = await call("enphase_authorize", enphase.account, { code: enphase.code.trim() })
	if (!result) return
	if (result.status === "Connected") {
		enphase.open = false
		toast.success("Enphase account connected.")
	} else enphase.error = result.error
}

const busy = (name, account) => pending.value === `${name}:${account.name}`
</script>

<template>
	<div v-if="memberOnly" class="card p-6 sm:p-8">
		<Alert theme="amber" title="Members only" description="Only members can add and manage their own solar API accounts. Use the dashboard to view all members' data." />
	</div>
	<div v-else class="space-y-6">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<p class="max-w-2xl text-p-base text-ink-gray-6">
				Connect the monitoring accounts for your installations. Only you can see your stations and production; Masters administrators can view them read-only. Your keys and passwords are encrypted and never shown again after saving.
			</p>
			<Button label="Add API account" variant="solid" theme="green" icon-left="lucide-plus" @click="openForm()" />
		</div>

		<div v-if="!accounts.data && !accounts.error" class="space-y-4" role="status" aria-label="Loading accounts">
			<Skeleton v-for="i in 2" :key="i" class="h-36 w-full rounded-6" />
		</div>
		<Alert v-else-if="accounts.error" theme="red" title="Couldn't load your accounts" :description="errorText(accounts.error)" />
		<div v-else-if="!accounts.data.length" class="card p-8 text-center text-p-base text-ink-gray-6">
			You haven't added any solar API accounts yet.
		</div>

		<div v-for="account in accounts.data || []" :key="account.name" class="card space-y-4 p-5 sm:p-6">
			<div class="flex flex-wrap items-center gap-2">
				<h2 class="text-lg-semibold text-ink-gray-9">{{ account.account_label }}</h2>
				<Badge :label="account.provider" />
				<Badge v-if="!account.enabled" theme="gray" label="Disabled" />
				<Badge v-else :theme="statusTheme(account.connection_status)" :label="account.connection_status || 'Not connected'" />
				<span v-if="account.company_name" class="text-base text-ink-gray-5">{{ account.company_name }}</span>
			</div>
			<dl class="grid gap-x-6 gap-y-2 text-base sm:grid-cols-2 lg:grid-cols-4">
				<div>
					<dt class="text-sm text-ink-gray-5">Stations fetched</dt>
					<dd class="flex items-center gap-1.5 text-ink-gray-8">
						{{ formatDateTime(account.last_successful_sync) }}
						<Badge v-if="account.sync_status" :theme="statusTheme(account.sync_status)" :label="account.sync_status" size="sm" />
					</dd>
				</div>
				<div>
					<dt class="text-sm text-ink-gray-5">Alerts checked</dt>
					<dd class="flex items-center gap-1.5 text-ink-gray-8">
						{{ formatDateTime(account.last_alert_sync) }}
						<Badge v-if="account.alert_status" :theme="statusTheme(account.alert_status)" :label="account.alert_status" size="sm" />
					</dd>
				</div>
				<div>
					<dt class="text-sm text-ink-gray-5">Token valid until</dt>
					<dd class="text-ink-gray-8">{{ formatDateTime(account.expires_at) }}</dd>
				</div>
				<div>
					<dt class="text-sm text-ink-gray-5">API hits this month</dt>
					<dd class="tabular-nums" :class="account.hit_budget && account.month_hits >= account.hit_budget ? 'text-ink-red-6' : 'text-ink-gray-8'">
						{{ (account.month_hits || 0).toLocaleString("en-IN") }}<template v-if="account.hit_budget"> / {{ account.hit_budget.toLocaleString("en-IN") }}</template>
					</dd>
				</div>
			</dl>
			<Alert
				v-for="message in [account.authentication_error, account.sync_error, account.company_lookup_error, account.alert_error].filter(Boolean)"
				:key="message"
				theme="amber"
				:description="message"
			/>
			<div class="flex flex-wrap gap-2 border-t border-outline-gray-1 pt-4">
				<Button label="Edit" icon-left="lucide-pencil" @click="openForm(account)" />
				<template v-if="account.enabled">
					<Button
						v-if="account.provider === 'Enphase'"
						label="Authorize with Enphase"
						icon-left="lucide-key-round"
						:loading="busy('enphase_authorize_url', account)"
						@click="startEnphase(account)"
					/>
					<Button label="Test connection" icon-left="lucide-plug" :loading="busy('test_connection', account)" @click="testConnection(account)" />
					<Button label="Fetch stations & devices" icon-left="lucide-download" :loading="busy('sync_inventory', account)" @click="fetchInventory(account)" />
					<Button
						v-if="account.provider === 'Enphase'"
						label="Refresh all devices"
						variant="ghost"
						tooltip="Re-reads every system's device list (one API hit per system). Normal fetches only read devices of new systems."
						:loading="busy('sync_inventory', account)"
						@click="fetchInventory(account, true)"
					/>
					<Button
						v-if="account.provider === 'Deye'"
						label="Fetch company details"
						variant="ghost"
						:loading="busy('fetch_company_details', account)"
						@click="fetchCompany(account)"
					/>
					<Button label="Disable" variant="ghost" theme="red" class="sm:ml-auto" :loading="busy('disable_my_account', account)" @click="disable(account)" />
				</template>
			</div>
		</div>

		<Dialog v-model:open="dialogOpen" :title="editing ? 'Edit API account' : 'Add API account'" size="xl">
			<form id="solar-account-form" class="space-y-4" @submit.prevent="submit">
				<div class="grid gap-4 sm:grid-cols-2">
					<FormControl v-model="form.account_label" label="Account name" placeholder="e.g. Rooftop installs" variant="outline" required />
					<FormControl
						v-model="form.provider"
						label="Provider"
						type="select"
						variant="outline"
						:options="['Deye', 'Enphase']"
						:disabled="Boolean(editing)"
					/>
				</div>
				<template v-if="form.provider === 'Deye'">
					<div class="grid gap-4 sm:grid-cols-2">
						<FormControl v-model="form.region" label="Region" type="select" variant="outline" :options="['India', 'Europe', 'Americas']" />
						<FormControl v-model="form.company_id" label="Company ID" variant="outline" inputmode="numeric" required />
						<FormControl v-model="form.app_id" label="App ID" variant="outline" required />
						<FormControl v-model="form.email" label="Deye account email" type="email" variant="outline" required />
					</div>
				</template>
				<template v-else>
					<div class="grid gap-4 sm:grid-cols-2">
						<FormControl v-model="form.client_id" label="Client ID" variant="outline" required />
						<FormControl v-model="form.enphase_username" label="Enlighten username (optional)" variant="outline" />
					</div>
					<FormControl
						v-model="form.redirect_uri"
						label="Redirect URI (optional)"
						variant="outline"
						description="Leave empty to paste the authorization code shown by Enphase."
					/>
				</template>
				<div class="grid gap-4 sm:grid-cols-2">
					<FormControl
						v-for="[key, label] in SECRETS[form.provider]"
						:key="key"
						v-model="form[key]"
						:label="label"
						type="password"
						variant="outline"
						autocomplete="new-password"
						:placeholder="editing?.['has_' + key] ? 'Saved — leave blank to keep' : ''"
					/>
				</div>
				<Alert v-if="formError" theme="red" title="Couldn't save the account" :description="formError" />
			</form>
			<template #actions>
				<div class="flex justify-end gap-2">
					<Button label="Cancel" @click="dialogOpen = false" />
					<Button type="submit" form="solar-account-form" label="Save" variant="solid" theme="green" :loading="save.loading" />
				</div>
			</template>
		</Dialog>

		<Dialog v-model:open="enphase.open" title="Authorize with Enphase" size="lg">
			<div class="space-y-4">
				<p class="text-p-base text-ink-gray-7">
					Sign in to Enphase in the new tab and approve access. Then paste the code Enphase shows (or the whole address from the browser bar) below.
				</p>
				<a :href="enphase.url" target="_blank" rel="noopener" class="inline-flex items-center gap-1 text-base-medium text-brand-700 hover:underline">
					Open Enphase sign-in again <span class="lucide-external-link size-3.5" aria-hidden="true" />
				</a>
				<FormControl v-model="enphase.code" label="Authorization code" variant="outline" />
				<Alert v-if="enphase.error" theme="red" title="Authorization failed" :description="enphase.error" />
			</div>
			<template #actions>
				<div class="flex justify-end gap-2">
					<Button label="Cancel" @click="enphase.open = false" />
					<Button
						label="Connect"
						variant="solid"
						theme="green"
						:disabled="!enphase.code.trim()"
						:loading="busy('enphase_authorize', enphase.account || {})"
						@click="finishEnphase"
					/>
				</div>
			</template>
		</Dialog>
	</div>
</template>
