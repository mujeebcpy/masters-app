<script setup>
import { provide } from "vue"
import { useCall } from "frappe-ui"
import { memberMethod, method } from "@/api"
import { memberSessionKey } from "@/member/session"

// Keep authentication state in memory, never in persistent resource caches.
const session = useCall({ url: memberMethod("get_session") })
const logoutRequest = useCall({ url: method("logout"), method: "POST", immediate: false })

async function logout() {
	try {
		await logoutRequest.submit()
		window.location.assign("/")
	} catch {
		// The header displays the request error and permits another attempt.
	}
}

provide(memberSessionKey, { session, logoutRequest, logout })
</script>

<template>
	<slot />
</template>
