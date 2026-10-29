<script setup>
import { asset } from "@/data/site"

defineProps({
	title: { type: String, required: true },
	subtitle: { type: String, default: "" },
	eyebrow: { type: String, default: "" },
	image: { type: String, default: () => asset("images/photos/members-gathering.jpg") },
})
</script>

<template>
	<section class="relative isolate overflow-hidden bg-forest">
		<img :src="image" alt="" class="absolute inset-0 -z-10 size-full object-cover opacity-30" />
		<div class="absolute inset-0 -z-10 bg-gradient-to-r from-forest via-forest/90 to-forest/40" aria-hidden="true" />
		<div class="container-page py-16 sm:py-20">
			<nav class="flex items-center gap-1.5 text-sm text-white/60" aria-label="Breadcrumb">
				<router-link to="/" class="hover:text-lime">Home</router-link>
				<span class="lucide-chevron-right size-3.5" aria-hidden="true" />
				<span class="text-white/90">{{ title }}</span>
			</nav>
			<p v-if="eyebrow" class="mt-6 text-sm-semibold uppercase tracking-[0.14em] text-lime">{{ eyebrow }}</p>
			<h1 class="mt-3 max-w-3xl text-display-sm font-bold text-white sm:text-display-lg">{{ title }}</h1>
			<p v-if="subtitle" class="mt-4 max-w-2xl text-p-lg text-white/75">{{ subtitle }}</p>
			<slot />
		</div>
		<div class="h-1 bg-gradient-to-r from-lime via-brand-500 to-teal-brand" aria-hidden="true" />
	</section>
</template>
