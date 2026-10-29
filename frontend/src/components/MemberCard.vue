<script setup>
import { computed } from "vue"
import { Avatar } from "frappe-ui"

const props = defineProps({
	member: { type: Object, required: true },
	compact: { type: Boolean, default: false },
})
defineEmits(["select"])

const initials = computed(() =>
	props.member.name
		.split(/\s+/)
		.filter((w) => /^[a-z]/i.test(w))
		.slice(0, 2)
		.map((w) => w[0].toUpperCase())
		.join("")
)
</script>

<template>
	<button
		type="button"
		class="group card flex w-full flex-col overflow-hidden text-left transition duration-200 hover:-translate-y-1 hover:border-brand-200 hover:shadow-xl focus-visible:-translate-y-1"
		@click="$emit('select', member)"
	>
		<div v-if="!compact" class="relative aspect-[4/5] w-full overflow-hidden bg-gradient-to-br from-brand-50 to-brand-100">
			<img
				v-if="member.photo"
				:src="member.photo"
				:alt="member.name"
				loading="lazy"
				class="size-full object-cover object-top transition duration-500 group-hover:scale-105"
			/>
			<div v-else class="grid size-full place-items-center">
				<span
					class="grid size-28 place-items-center rounded-full bg-surface-base/80 font-display text-display-md font-bold text-brand-600 shadow-sm"
				>
					{{ initials }}
				</span>
			</div>
			<span
				v-if="member.position"
				class="absolute bottom-3 left-3 right-3 truncate rounded-full bg-forest/85 px-3 py-1 text-center text-xs-semibold text-lime backdrop-blur"
			>
				{{ member.position }}
			</span>
		</div>
		<div class="flex flex-1 items-center gap-3 p-4">
			<Avatar v-if="compact" :label="member.name" :image="member.photo" size="xl" theme="green" />
			<div class="min-w-0 flex-1">
				<p class="truncate text-lg-semibold text-ink-gray-9">{{ member.name }}</p>
				<p v-if="compact && member.position" class="mt-1 truncate text-sm-medium text-brand-700">
					{{ member.position }}
				</p>
				<p class="mt-1 truncate text-sm text-ink-gray-5">
					{{ [member.designation, member.company].filter(Boolean).join(" · ") || member.district }}
				</p>
			</div>
		</div>
	</button>
</template>
