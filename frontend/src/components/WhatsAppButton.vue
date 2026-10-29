<script setup>
import { site } from "@/data/site"
import SocialIcon from "./SocialIcon.vue"
</script>

<template>
	<a
		:href="site.whatsapp"
		target="_blank"
		rel="noopener"
		aria-label="Chat with us on WhatsApp"
		class="fixed bottom-5 right-5 z-30 grid size-14 place-items-center rounded-full bg-[#25D366] text-white shadow-xl transition hover:scale-105"
	>
		<SocialIcon name="whatsapp" class="size-7" />
	</a>
</template>
