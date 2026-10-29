<script setup>
import { FrappeUIProvider } from "frappe-ui"
import SiteHeader from "@/components/SiteHeader.vue"
import SiteFooter from "@/components/SiteFooter.vue"
import WhatsAppButton from "@/components/WhatsAppButton.vue"
</script>

<template>
	<FrappeUIProvider>
		<div class="flex min-h-screen flex-col">
			<SiteHeader />
			<main class="flex-1">
				<router-view />
			</main>
			<SiteFooter />
			<WhatsAppButton />
		</div>
	</FrappeUIProvider>
</template>
