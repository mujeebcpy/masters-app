<script setup>
import { computed, ref } from "vue"
import { FormControl, Skeleton, TabButtons, TextInput, useCall } from "frappe-ui"
import { asset } from "@/data/site"
import { websiteMethod } from "@/api"
import PageHero from "@/components/PageHero.vue"
import MemberCard from "@/components/MemberCard.vue"
import MemberDialog from "@/components/MemberDialog.vue"
import EmptyState from "@/components/EmptyState.vue"
import SectionHeading from "@/components/SectionHeading.vue"
import MemberMap from "@/components/MemberMap.vue"

const committeeTitles = {
	"State Secretariat": "State Secretariat members",
	"State Executive": "State Executive members",
	"District Coordinator": "District coordinators",
}

const members = useCall({ url: websiteMethod("get_members"), cacheKey: "members" })
const tab = ref("committee")
const query = ref("")
const district = ref("")
const selectedMember = ref(null)

const tabs = computed(() => [
	{ value: "committee", label: "Committee" },
	{ value: "lifetime", label: `Lifetime members${count("lifetime")}` },
	{ value: "ordinary", label: `Ordinary members${count("ordinary")}` },
])

function count(key) {
	const n = members.data?.[key]?.length
	return n ? ` (${n})` : ""
}

const districts = computed(() => {
	const all = [...(members.data?.lifetime || []), ...(members.data?.ordinary || [])]
	const names = [...new Set(all.map((m) => m.district).filter(Boolean))].sort()
	return [{ label: "All districts", value: "" }, ...names.map((d) => ({ label: d, value: d }))]
})

function matches(member) {
	const q = query.value.trim().toLowerCase()
	if (district.value && member.district !== district.value) return false
	if (!q) return true
	return [member.name, member.company, member.designation, member.district, member.position]
		.filter(Boolean)
		.some((v) => v.toLowerCase().includes(q))
}

const committees = computed(() =>
	(members.data?.committees || [])
		.map((c) => ({ ...c, members: c.members.filter(matches) }))
		.filter((c) => c.members.length)
)
const directory = computed(() => (members.data?.[tab.value] || []).filter(matches))
</script>

<template>
	<PageHero
		title="Members"
		eyebrow="Our team"
		subtitle="The office bearers who lead Masters, and the vendors across Kerala who make up the association."
		:image="asset('images/photos/executive-committee.jpg')"
	/>

	<section class="container-page py-14 sm:py-16">
		<div
			class="sticky top-16 z-20 -mx-4 flex flex-col gap-3 border-b border-outline-gray-1 bg-surface-base/95 px-4 py-3 backdrop-blur sm:mx-0 sm:rounded-6 sm:border sm:px-3 md:flex-row md:items-center md:justify-between lg:top-[4.75rem]"
		>
			<div class="overflow-x-auto">
				<TabButtons v-model="tab" :options="tabs" />
			</div>
			<div class="flex gap-2">
				<TextInput
					v-model="query"
					type="search"
					placeholder="Search name, company…"
					class="min-w-0 flex-1 md:w-64"
					:debounce="150"
				>
					<template #prefix><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" /></template>
				</TextInput>
				<FormControl
					v-if="tab !== 'committee'"
					v-model="district"
					type="select"
					class="w-44 shrink-0"
					:options="districts"
					placeholder="All districts"
				/>
			</div>
		</div>

		<div v-if="!members.data" class="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
			<Skeleton v-for="i in 8" :key="i" class="aspect-[4/5.6] rounded-7" />
		</div>

		<template v-else-if="tab === 'committee'">
			<div v-for="group in committees" :key="group.committee" class="mt-12 first:mt-10">
				<div class="flex flex-wrap items-baseline justify-between gap-2 border-b border-outline-gray-1 pb-3">
					<h2 class="text-display-xs font-bold text-ink-gray-9">{{ committeeTitles[group.committee] }}</h2>
					<span class="rounded-full bg-brand-50 px-3 py-1 text-sm-semibold text-brand-700">{{ group.term }}</span>
				</div>
				<div
					class="mt-6 grid gap-5"
					:class="
						group.committee === 'District Coordinator'
							? 'sm:grid-cols-2 lg:grid-cols-3'
							: 'sm:grid-cols-2 lg:grid-cols-4'
					"
				>
					<MemberCard
						v-for="member in group.members"
						:key="member.id + member.position"
						:member="member"
						:compact="group.committee === 'District Coordinator'"
						@select="selectedMember = $event"
					/>
				</div>
			</div>
			<EmptyState
				v-if="!committees.length"
				class="mt-10"
				icon="lucide-users"
				:title="query ? 'No committee members match your search' : 'Committee will be announced soon'"
				:description="query ? 'Try a different name or position.' : ''"
			/>
		</template>

		<template v-else>
			<div v-if="directory.length" class="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				<MemberCard
					v-for="member in directory"
					:key="member.id"
					:member="member"
					compact
					@select="selectedMember = $event"
				/>
			</div>
			<EmptyState
				v-else
				class="mt-10"
				icon="lucide-users"
				:title="query || district ? 'No members match your filters' : 'No members listed yet'"
				:description="query || district ? 'Try a different search or district.' : 'Approved members will appear here.'"
			/>
		</template>
	</section>

	<section v-if="members.data?.locations?.length" class="border-t border-outline-gray-1 bg-surface-gray-1 py-14 sm:py-16">
		<div class="container-page">
			<SectionHeading
				eyebrow="Find a member"
				title="Members across Kerala"
				description="Approved Masters members on the map. Select a pin for details and directions."
			/>
			<MemberMap class="mt-8" :locations="members.data.locations" />
		</div>
	</section>

	<MemberDialog :member="selectedMember" @close="selectedMember = null" />
</template>
