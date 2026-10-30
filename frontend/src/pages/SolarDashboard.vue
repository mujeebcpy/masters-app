<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { Alert, Badge, Button, FormControl, Skeleton, TextInput, toast, useCall } from "frappe-ui"
import { errorText, solarMethod } from "@/api"
import { ONLINE, formatDateTime, formatEnergy, formatPower, queuedSummary, severityTheme } from "@/solar/format"

const PAGE = 100
const filters = ref({ provider: null, account: null, member: null })
const search = ref("")
const start = ref(0)
const overview = useCall({
	url: solarMethod("get_overview"),
	params: () => ({ ...filters.value, search: search.value || null, start: start.value }),
	refetch: true,
})
const refresh = useCall({ url: solarMethod("refresh_production"), method: "POST", immediate: false })
const alertCheck = useCall({ url: solarMethod("check_alerts"), method: "POST", immediate: false })

const data = computed(() => overview.data)
const isAll = computed(() => data.value?.scope === "all")
const canManage = computed(() => (data.value?.manageable_accounts || []).length > 0)
const accountOptions = computed(() => [
	{ label: "All accounts", value: null },
	...(data.value?.accounts || []).map((a) => ({
		label: isAll.value ? `${a.account_label} · ${a.member_name}` : a.account_label,
		value: a.name,
	})),
])
const memberOptions = computed(() => [
	{ label: "All members", value: null },
	...(data.value?.members || []).map((m) => ({ label: m.label, value: m.name })),
])
const providerOptions = [
	{ label: "All providers", value: null },
	{ label: "Deye", value: "Deye" },
	{ label: "Enphase", value: "Enphase" },
]
const cards = computed(() => {
	const s = data.value?.summary || {}
	const n = s.station_count || 0
	const coverage = (field) => (n ? `${s[field + "_coverage"] ?? 0} of ${n} stations` : "No stations")
	return [
		{ label: "Installed capacity", value: formatPower(s.capacity_kw), hint: coverage("capacity_kw"), icon: "lucide-zap" },
		{ label: "Current power", value: formatPower(s.production_power_kw), hint: coverage("production_power_kw"), icon: "lucide-activity" },
		{ label: "Today", value: formatEnergy(s.daily_production_kwh), hint: coverage("daily_production_kwh"), icon: "lucide-sun" },
		{ label: "This month", value: formatEnergy(s.monthly_production_kwh), hint: coverage("monthly_production_kwh"), icon: "lucide-calendar" },
		{ label: "Lifetime", value: formatEnergy(s.total_production_kwh), hint: coverage("total_production_kwh"), icon: "lucide-battery-charging" },
	]
})
const accountProblems = computed(() =>
	(data.value?.accounts || []).filter((a) => a.connection_status === "Error" || a.sync_status === "Failed" || a.alert_status === "Failed")
)

watch(
	() => [filters.value.provider, filters.value.account, filters.value.member, search.value],
	() => (start.value = 0),
	{ deep: true }
)
// Selecting a member resets an account that may belong to someone else.
watch(
	() => filters.value.member,
	() => (filters.value.account = null)
)

// Poll while production jobs are queued or running, then stop.
let timer = null
watch(
	() => data.value?.busy,
	(busy) => {
		clearInterval(timer)
		timer = busy ? setInterval(() => overview.reload(), 8000) : null
	}
)
onBeforeUnmount(() => clearInterval(timer))

async function run(call, label) {
	try {
		const result = await call.submit({ account: filters.value.account })
		toast.success(`${label}: ${queuedSummary(result)}`)
		overview.reload()
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		call.reset()
	}
}
</script>

<template>
	<div v-if="!data && !overview.error" class="space-y-4" role="status" aria-label="Loading solar data">
		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
			<Skeleton v-for="i in 5" :key="i" class="h-28 rounded-6" />
		</div>
		<Skeleton class="h-72 w-full rounded-6" />
	</div>
	<div v-else-if="overview.error && !data" class="space-y-4">
		<Alert theme="red" title="Couldn't load solar data" :description="errorText(overview.error)" />
		<Button label="Try again" :loading="overview.loading" @click="overview.reload()" />
	</div>
	<div v-else class="space-y-6">
		<div v-if="!data.accounts.length && !filters.provider && !filters.member" class="card space-y-4 p-6 sm:p-8">
			<h2 class="text-lg-semibold text-ink-gray-9">No solar accounts yet</h2>
			<p class="text-p-base text-ink-gray-6">
				{{ isAll ? "No member has connected a solar monitoring account yet." : "Connect your Deye or Enphase account to see your stations, production and alerts here." }}
			</p>
			<Button v-if="!isAll" :route="{ path: '/solar/accounts' }" label="Add API account" variant="solid" theme="green" icon-left="lucide-plus" class="self-start" />
		</div>

		<template v-else>
			<div class="flex flex-wrap items-end gap-3">
				<FormControl v-if="isAll" v-model="filters.member" type="select" class="w-full sm:w-52" :options="memberOptions" />
				<FormControl v-model="filters.provider" type="select" class="w-full sm:w-40" :options="providerOptions" />
				<FormControl v-model="filters.account" type="select" class="w-full sm:w-56" :options="accountOptions" />
				<div v-if="canManage" class="flex gap-2 sm:ml-auto">
					<Button label="Update production" icon-left="lucide-refresh-cw" :loading="refresh.loading" @click="run(refresh, 'Production update')" />
					<Button label="Check alerts" icon-left="lucide-bell" :loading="alertCheck.loading" @click="run(alertCheck, 'Alert check')" />
				</div>
			</div>

			<Alert
				v-for="account in accountProblems"
				:key="account.name"
				theme="amber"
				:title="`${account.account_label}${isAll ? ' · ' + account.member_name : ''}`"
				:description="account.authentication_error || account.sync_error || account.alert_error || 'This account needs attention.'"
			/>

			<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
				<div v-for="card in cards" :key="card.label" class="card p-5">
					<div class="flex items-center gap-2 text-sm-medium text-ink-gray-5">
						<span :class="card.icon" class="size-4" aria-hidden="true" />
						{{ card.label }}
					</div>
					<p class="mt-3 text-2xl-semibold text-ink-gray-9">{{ card.value }}</p>
					<p class="mt-1 text-sm text-ink-gray-5">{{ card.hint }}</p>
				</div>
			</div>
			<p class="text-sm text-ink-gray-5">
				{{ data.station_count }} stations · {{ data.device_count }} devices
				<template v-if="data.summary.stale_count"> · {{ data.summary.stale_count }} with stale readings</template>
			</p>

			<div v-if="data.alerts.length" class="card p-5 sm:p-6">
				<div class="flex items-center justify-between gap-3">
					<h2 class="text-lg-semibold text-ink-gray-9">Open alerts</h2>
					<div class="flex gap-1.5">
						<Badge v-for="(count, severity) in data.alert_counts" :key="severity" :theme="severityTheme[severity]" :label="`${count} ${severity}`" />
					</div>
				</div>
				<ul class="mt-4 divide-y divide-outline-gray-1">
					<li v-for="alert in data.alerts" :key="alert.name" class="flex flex-wrap items-center gap-x-3 gap-y-1 py-3">
						<Badge :theme="severityTheme[alert.severity]" :label="alert.severity" />
						<span class="text-base-medium text-ink-gray-8">{{ alert.alert_name }}</span>
						<router-link :to="`/solar/station/${encodeURIComponent(alert.station)}`" class="text-base text-ink-gray-6 hover:underline">
							{{ alert.station_name }}
						</router-link>
						<span class="ml-auto text-sm text-ink-gray-5">{{ formatDateTime(alert.alert_start) }}</span>
					</li>
				</ul>
			</div>

			<div class="card overflow-hidden">
				<div class="flex flex-wrap items-center justify-between gap-3 p-5 sm:px-6">
					<h2 class="text-lg-semibold text-ink-gray-9">Stations</h2>
					<TextInput v-model="search" class="w-full sm:w-64" placeholder="Search stations" :debounce="250">
						<template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
					</TextInput>
				</div>
				<div class="overflow-x-auto">
					<table class="w-full min-w-[44rem] text-left text-base">
						<thead class="border-y border-outline-gray-1 bg-surface-gray-1 text-sm-medium text-ink-gray-5">
							<tr>
								<th class="px-5 py-2.5 sm:px-6">Station</th>
								<th class="px-3 py-2.5">Status</th>
								<th class="px-3 py-2.5 text-right">Capacity</th>
								<th class="px-3 py-2.5 text-right">Power</th>
								<th class="px-3 py-2.5 text-right">Today</th>
								<th class="px-3 py-2.5 text-right">Month</th>
								<th class="px-5 py-2.5 text-right sm:px-6">Updated</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-outline-gray-1">
							<tr v-for="station in data.stations" :key="station.name" class="hover:bg-surface-gray-1">
								<td class="px-5 py-3 sm:px-6">
									<router-link :to="`/solar/station/${encodeURIComponent(station.name)}`" class="text-base-medium text-ink-gray-9 hover:underline">
										{{ station.station_name || station.name }}
									</router-link>
									<p v-if="station.location" class="mt-0.5 max-w-xs truncate text-sm text-ink-gray-5">{{ station.location }}</p>
								</td>
								<td class="px-3 py-3">
									<Badge
										:theme="ONLINE.includes(station.connection_status) ? 'green' : 'gray'"
										:label="station.connection_status || 'Unknown'"
									/>
									<Badge v-if="station.production_status === 'Failed'" theme="red" label="Update failed" class="ml-1" />
									<Badge v-else-if="['Queued', 'Running'].includes(station.production_status)" theme="blue" label="Updating" class="ml-1" />
								</td>
								<td class="px-3 py-3 text-right tabular-nums">{{ formatPower(station.capacity_kw) }}</td>
								<td class="px-3 py-3 text-right tabular-nums">{{ formatPower(station.production_power_kw) }}</td>
								<td class="px-3 py-3 text-right tabular-nums">{{ formatEnergy(station.daily_production_kwh) }}</td>
								<td class="px-3 py-3 text-right tabular-nums">{{ formatEnergy(station.monthly_production_kwh) }}</td>
								<td class="px-5 py-3 text-right text-sm sm:px-6" :class="station.stale ? 'text-ink-amber-6' : 'text-ink-gray-5'">
									{{ formatDateTime(station.last_production_fetch) }}
								</td>
							</tr>
							<tr v-if="!data.stations.length">
								<td colspan="7" class="px-6 py-10 text-center text-ink-gray-5">
									{{ search ? "No stations match your search." : "No stations yet. Fetch stations from your API account." }}
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				<div v-if="data.filtered_count > PAGE" class="flex items-center justify-between border-t border-outline-gray-1 px-5 py-3 text-sm text-ink-gray-6 sm:px-6">
					<span>{{ start + 1 }}–{{ Math.min(start + PAGE, data.filtered_count) }} of {{ data.filtered_count }}</span>
					<div class="flex gap-2">
						<Button label="Previous" :disabled="start === 0" @click="start = Math.max(0, start - PAGE)" />
						<Button label="Next" :disabled="start + PAGE >= data.filtered_count" @click="start += PAGE" />
					</div>
				</div>
			</div>
		</template>
	</div>
</template>
