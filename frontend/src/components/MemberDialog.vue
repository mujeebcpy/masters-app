<script setup>
import { computed } from "vue"
import { Avatar, Badge, Dialog } from "frappe-ui"

const props = defineProps({ member: { type: Object, default: null } })
const emit = defineEmits(["close"])

const open = computed({
	get: () => Boolean(props.member),
	set: (value) => !value && emit("close"),
})

const membershipLabel = { "Lifetime Member": "Lifetime member", "Normal Member": "Ordinary member" }

const details = computed(() => {
	const m = props.member
	if (!m) return []
	return [
		{ icon: "lucide-briefcase", label: "Designation", value: m.designation },
		{ icon: "lucide-building-2", label: "Company", value: m.company },
		{ icon: "lucide-map-pin", label: "District", value: m.district },
		{ icon: "lucide-mail", label: "Email", value: m.email, href: m.email && `mailto:${m.email}` },
		{ icon: "lucide-phone", label: "Phone", value: m.phone, href: m.phone && `tel:${m.phone.replace(/[^+\d]/g, "")}` },
	].filter((d) => d.value)
})
</script>

<template>
	<Dialog v-model:open="open" size="md" bare>
		<div v-if="member" class="overflow-hidden rounded-7">
			<div class="relative h-24 bg-gradient-to-r from-lime via-brand-500 to-teal-brand" />
			<div class="-mt-12 px-6 pb-6">
				<Avatar
					:label="member.name"
					:image="member.photo"
					size="3xl"
					theme="green"
					class="!size-24 ring-4 ring-white"
				/>
				<h3 class="mt-3 text-display-xs font-bold text-ink-gray-9">{{ member.name }}</h3>
				<div class="mt-2 flex flex-wrap gap-1.5">
					<Badge v-if="member.position" theme="green" variant="solid" :label="member.position" />
					<Badge
						v-if="membershipLabel[member.membership_status]"
						theme="green"
						variant="subtle"
						:label="membershipLabel[member.membership_status]"
					/>
					<Badge v-if="member.is_mnre_empaneled" theme="blue" variant="subtle">
						<template #prefix><span class="lucide-badge-check size-3" aria-hidden="true" /></template>
						MNRE empanelled
					</Badge>
				</div>
				<dl class="mt-5 divide-y divide-outline-gray-1 border-y border-outline-gray-1">
					<div v-for="d in details" :key="d.label" class="flex items-start gap-3 py-3">
						<span :class="d.icon" class="mt-0.5 size-4 shrink-0 text-brand-600" aria-hidden="true" />
						<dt class="w-24 shrink-0 text-sm text-ink-gray-5">{{ d.label }}</dt>
						<dd class="min-w-0 flex-1 break-words text-base text-ink-gray-8">
							<a v-if="d.href" :href="d.href" class="text-ink-blue-link hover:underline">{{ d.value }}</a>
							<template v-else>{{ d.value }}</template>
						</dd>
					</div>
				</dl>
			</div>
		</div>
	</Dialog>
</template>
