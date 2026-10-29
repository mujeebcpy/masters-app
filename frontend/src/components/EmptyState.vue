<script setup>
defineProps({
	icon: { type: String, default: "lucide-inbox" },
	title: { type: String, required: true },
	description: { type: String, default: "" },
})
</script>

<template>
	<div class="card flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
		<div class="rounded-full bg-brand-50 p-4 text-brand-600">
			<span :class="icon" class="block size-7" aria-hidden="true" />
		</div>
		<p class="text-xl-semibold text-ink-gray-8">{{ title }}</p>
		<p v-if="description" class="max-w-md text-p-base text-ink-gray-5">{{ description }}</p>
		<slot />
	</div>
</template>
