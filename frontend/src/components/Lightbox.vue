<script setup>
import { computed } from "vue"
import { Button, Dialog } from "frappe-ui"

const props = defineProps({ items: { type: Array, required: true } })
const index = defineModel("index", { type: Number, default: null })

const open = computed({
	get: () => index.value !== null,
	set: (value) => !value && (index.value = null),
})
const item = computed(() => (index.value === null ? null : props.items[index.value]))

function step(delta) {
	index.value = (index.value + delta + props.items.length) % props.items.length
}

function onKeydown(event) {
	if (event.key === "ArrowRight") step(1)
	if (event.key === "ArrowLeft") step(-1)
}
</script>

<template>
	<Dialog v-model:open="open" size="5xl" bare>
		<div v-if="item" class="relative bg-black" tabindex="-1" @keydown="onKeydown">
			<div v-if="item.media_type === 'Video'" class="aspect-video w-full">
				<iframe
					:src="`https://www.youtube-nocookie.com/embed/${item.youtube_id}?autoplay=1`"
					:title="item.title"
					class="size-full"
					allow="autoplay; encrypted-media; picture-in-picture"
					allowfullscreen
				/>
			</div>
			<img v-else :src="item.image" :alt="item.title" class="mx-auto max-h-[80vh] w-auto object-contain" />

			<template v-if="items.length > 1">
				<Button
					class="absolute left-3 top-1/2 -translate-y-1/2"
					icon="lucide-chevron-left"
					size="lg"
					aria-label="Previous"
					@click="step(-1)"
				/>
				<Button
					class="absolute right-3 top-1/2 -translate-y-1/2"
					icon="lucide-chevron-right"
					size="lg"
					aria-label="Next"
					@click="step(1)"
				/>
			</template>
			<div class="flex items-center justify-between gap-4 bg-forest px-5 py-3 text-white">
				<div class="min-w-0">
					<p class="truncate text-base-medium">{{ item.title }}</p>
					<p v-if="item.description" class="truncate text-sm text-white/60">{{ item.description }}</p>
				</div>
				<span class="shrink-0 text-sm text-white/60">{{ index + 1 }} / {{ items.length }}</span>
			</div>
		</div>
	</Dialog>
</template>
