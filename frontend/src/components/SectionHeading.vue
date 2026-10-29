<script setup>
defineProps({
	eyebrow: { type: String, default: "" },
	title: { type: String, required: true },
	description: { type: String, default: "" },
	center: { type: Boolean, default: false },
})
</script>

<template>
	<div :class="center ? 'mx-auto max-w-2xl text-center' : 'max-w-2xl'">
		<p v-if="eyebrow" class="eyebrow" :class="center && 'justify-center'">{{ eyebrow }}</p>
		<h2 class="mt-3 text-display-sm font-bold text-ink-gray-9 sm:text-display-md">
			<slot name="title">{{ title }}</slot>
		</h2>
		<p v-if="description" class="mt-4 text-p-lg text-ink-gray-6">{{ description }}</p>
	</div>
</template>
