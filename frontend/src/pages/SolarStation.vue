<script setup>
import { computed, onBeforeUnmount, watch } from "vue"
import { Alert, Badge, Button, Skeleton, toast, useCall } from "frappe-ui"
import { errorText, solarMethod } from "@/api"
import { ONLINE, formatDateTime, formatEnergy, formatPower, severityTheme } from "@/solar/format"

const props = defineProps({ name: { type: String, required: true } })
const detail = useCall({ url: solarMethod("get_station"), params: () => ({ station: props.name }), refetch: true })
const refresh = useCall({ url: solarMethod("refresh_station"), method: "POST", immediate: false })

const station = computed(() => detail.data?.station)
const busy = computed(() => ["Queued", "Running"].includes(station.value?.production_status))
const readings = computed(() => {
	const s = station.value || {}
	return [
		{ label: "Installed capacity", value: formatPower(s.capacity_kw) },
		{ label: "Current power", value: formatPower(s.production_power_kw) },
		{ label: "Today", value: formatEnergy(s.daily_production_kwh) },
		{ label: "This month", value: formatEnergy(s.monthly_production_kwh) },
		{ label: "Lifetime", value: formatEnergy(s.total_production_kwh) },
	]
})
const details = computed(() => {
	const s = station.value || {}
	return [
		["Account", `${detail.data?.account.label} (${detail.data?.account.provider})`],
		["Location", s.location || "—"],
		["Time zone", s.timezone || "—"],
		["Last updated", formatDateTime(s.last_production_fetch)],
	]
})

let timer = null
watch(busy, (value) => {
	clearInterval(timer)
	timer = value ? setInterval(() => detail.reload(), 6000) : null
})
onBeforeUnmount(() => clearInterval(timer))

async function update() {
	try {
		const result = await refresh.submit({ station: props.name })
		if (result.status === "Cached") toast.info(`Updated recently. Try again in ${result.retry_after} seconds.`)
		else toast.success("Production update queued.")
		detail.reload()
	} catch (error) {
		toast.error(errorText(error))
	} finally {
		refresh.reset()
	}
}
</script>

<template>
	<div v-if="!detail.data && !detail.error" class="space-y-4" role="status" aria-label="Loading station">
		<Skeleton class="h-24 w-full rounded-6" />
		<Skeleton class="h-64 w-full rounded-6" />
	</div>
	<div v-else-if="detail.error" class="space-y-4">
		<Alert theme="red" title="Couldn't load this station" :description="errorText(detail.error)" />
		<Button :route="{ path: '/solar' }" label="Back to dashboard" icon-left="lucide-arrow-left" />
	</div>
	<div v-else class="space-y-6">
		<div class="flex flex-wrap items-center gap-3">
			<Button :route="{ path: '/solar' }" variant="ghost" icon-left="lucide-arrow-left" label="Dashboard" />
			<h2 class="text-2xl-semibold text-ink-gray-9">{{ station.station_name || station.name }}</h2>
			<Badge :theme="ONLINE.includes(station.connection_status) ? 'green' : 'gray'" :label="station.connection_status || 'Unknown'" />
			<Badge v-if="station.stale" theme="amber" label="Stale readings" />
			<Button
				v-if="detail.data.can_manage"
				class="sm:ml-auto"
				label="Update production"
				icon-left="lucide-refresh-cw"
				:loading="refresh.loading || busy"
				@click="update"
			/>
		</div>
		<Alert v-if="station.production_error" theme="amber" title="Last update failed" :description="station.production_error" />

		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
			<div v-for="item in readings" :key="item.label" class="card p-5">
				<p class="text-sm-medium text-ink-gray-5">{{ item.label }}</p>
				<p class="mt-2 text-2xl-semibold text-ink-gray-9">{{ item.value }}</p>
			</div>
		</div>

		<div class="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
			<div class="card p-5 sm:p-6">
				<h3 class="text-lg-semibold text-ink-gray-9">Details</h3>
				<dl class="mt-4 space-y-3">
					<div v-for="[label, value] in details" :key="label" class="flex justify-between gap-4 text-base">
						<dt class="text-ink-gray-5">{{ label }}</dt>
						<dd class="text-right text-ink-gray-8">{{ value }}</dd>
					</div>
				</dl>
			</div>
			<div class="card p-5 sm:p-6">
				<h3 class="text-lg-semibold text-ink-gray-9">Devices</h3>
				<ul v-if="detail.data.devices.length" class="mt-3 divide-y divide-outline-gray-1">
					<li v-for="device in detail.data.devices" :key="device.name" class="flex items-center justify-between gap-3 py-2.5">
						<span class="text-base-medium text-ink-gray-8">{{ device.device_type || "Device" }}</span>
						<span class="font-mono text-sm text-ink-gray-5">{{ device.external_id }}</span>
					</li>
				</ul>
				<p v-else class="mt-3 text-base text-ink-gray-5">No devices found for this station.</p>
			</div>
		</div>

		<div class="card p-5 sm:p-6">
			<h3 class="text-lg-semibold text-ink-gray-9">Open alerts</h3>
			<ul v-if="detail.data.alerts.length" class="mt-3 divide-y divide-outline-gray-1">
				<li v-for="alert in detail.data.alerts" :key="alert.name" class="flex flex-wrap items-center gap-x-3 gap-y-1 py-3">
					<Badge :theme="severityTheme[alert.severity]" :label="alert.severity" />
					<span class="text-base-medium text-ink-gray-8">{{ alert.alert_name }}</span>
					<span v-if="alert.device_sn" class="font-mono text-sm text-ink-gray-5">{{ alert.device_sn }}</span>
					<span class="ml-auto text-sm text-ink-gray-5">{{ formatDateTime(alert.alert_start) }}</span>
				</li>
			</ul>
			<p v-else class="mt-3 text-base text-ink-gray-5">No open alerts.</p>
		</div>
	</div>
</template>
