<script setup>
import { computed, onMounted, watch } from "vue"
import { useRoute } from "vue-router"
import { Alert, Button, Skeleton } from "frappe-ui"
import { errorText } from "@/api"
import { loginUrl, useMemberSession } from "@/member/session"

const route = useRoute()
const { session } = useMemberSession()
const ready = computed(() => session.isFinished && !session.loading)
const access = computed(() => session.data?.solar_access)
let redirecting = false

watch(
	() => [ready.value, session.data?.is_logged_in, route.fullPath],
	() => {
		if (ready.value && session.data && !session.data.is_logged_in && !redirecting) {
			redirecting = true
			window.location.assign(loginUrl(route.fullPath))
		}
	},
	{ immediate: true }
)

onMounted(() => {
	if (!session.loading) session.reload()
})
</script>

<template>
	<section class="container-page max-w-6xl py-10 text-ink-gray-8 sm:py-14">
		<div class="mb-7 flex flex-wrap items-start justify-between gap-5">
			<div>
				<p class="text-sm-medium text-ink-gray-5">{{ access === "all" ? "All members · read only" : "Member area" }}</p>
				<h1 class="mt-2 text-4xl-bold text-ink-gray-9">{{ route.meta.title }}</h1>
			</div>
			<nav v-if="access" class="flex gap-2" aria-label="Solar monitor">
				<Button :route="{ path: '/solar' }" label="Dashboard" :variant="route.name === 'SolarDashboard' ? 'solid' : 'subtle'" />
				<Button
					v-if="session.data?.has_member_access"
					:route="{ path: '/solar/accounts' }"
					label="API accounts"
					:variant="route.name === 'SolarAccounts' ? 'solid' : 'subtle'"
				/>
			</nav>
		</div>
		<div v-if="!session.data && !session.error" class="space-y-4" role="status" aria-label="Checking solar monitor access">
			<Skeleton class="h-28 w-full rounded-6" />
			<Skeleton class="h-64 w-full rounded-6" />
		</div>
		<div v-else-if="session.error" class="space-y-4">
			<Alert theme="red" title="Couldn't check your account" :description="errorText(session.error)" />
			<Button label="Try again" :loading="session.loading" @click="session.reload()" />
		</div>
		<div v-else-if="!access" class="card space-y-4 p-6 sm:p-8">
			<Alert
				theme="amber"
				title="Solar monitor unavailable"
				:description="session.data?.reason || 'The solar monitor is available to approved members.'"
			/>
			<Button :route="{ path: '/contact' }" label="Contact Masters" />
		</div>
		<router-view v-else />
	</section>
</template>
