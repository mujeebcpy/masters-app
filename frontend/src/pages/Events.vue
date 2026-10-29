<script setup>
import { Button, Skeleton, useCall } from "frappe-ui"
import { asset, site } from "@/data/site"
import { formatDate, websiteMethod } from "@/api"
import PageHero from "@/components/PageHero.vue"
import EmptyState from "@/components/EmptyState.vue"

const events = useCall({ url: websiteMethod("get_events"), cacheKey: "events" })

function dateRange(event) {
	if (!event.end_date || event.end_date === event.start_date) return formatDate(event.start_date)
	return `${formatDate(event.start_date, { day: "numeric", month: "short" })} – ${formatDate(event.end_date)}`
}
</script>

<template>
	<PageHero
		title="Events"
		eyebrow="What's on"
		subtitle="Expos, trainings and member meets organised by Masters Association."
		:image="asset('images/gallery/expo-2025-04.jpg')"
	/>

	<section class="container-page py-14 sm:py-16">
		<div v-if="!events.data" class="space-y-5">
			<Skeleton v-for="i in 3" :key="i" class="h-56 rounded-7" />
		</div>

		<template v-else>
			<h2 class="text-display-xs font-bold text-ink-gray-9">Upcoming events</h2>
			<div v-if="events.data.upcoming.length" class="mt-6 space-y-6">
				<article
					v-for="event in events.data.upcoming"
					:id="event.name"
					:key="event.name"
					class="card grid scroll-mt-28 overflow-hidden md:grid-cols-[18rem_1fr]"
				>
					<div class="relative bg-gradient-to-br from-brand-500 to-teal-brand">
						<img
							v-if="event.cover_image"
							:src="event.cover_image"
							:alt="event.title"
							class="size-full max-h-72 object-cover md:max-h-none"
						/>
						<div v-else class="grid h-44 place-items-center text-white md:h-full">
							<span class="lucide-calendar-days size-12 opacity-80" aria-hidden="true" />
						</div>
					</div>
					<div class="p-6 sm:p-8">
						<div class="flex flex-wrap gap-x-5 gap-y-2 text-sm-medium text-brand-700">
							<span class="flex items-center gap-1.5">
								<span class="lucide-calendar size-4" aria-hidden="true" />{{ dateRange(event) }}
							</span>
							<span v-if="event.venue" class="flex items-center gap-1.5">
								<span class="lucide-map-pin size-4" aria-hidden="true" />{{ event.venue }}
							</span>
						</div>
						<h3 class="mt-3 text-display-sm font-bold text-ink-gray-9">{{ event.title }}</h3>
						<p v-if="event.summary" class="mt-3 text-p-lg text-ink-gray-6">{{ event.summary }}</p>
						<div
							v-if="event.description"
							class="prose prose-sm mt-4 max-w-none text-ink-gray-7"
							v-html="event.description"
						/>
						<Button
							v-if="event.registration_url"
							class="mt-6"
							variant="solid"
							theme="green"
							size="lg"
							:href="event.registration_url"
							label="Event details & registration"
							icon-right="lucide-arrow-up-right"
						/>
					</div>
				</article>
			</div>
			<EmptyState
				v-else
				class="mt-6"
				icon="lucide-calendar-days"
				title="No upcoming events announced"
				description="Follow Masters Expo for the latest on Kerala's largest solar expo and member meets."
			>
				<Button class="mt-2" variant="outline" :href="site.expoLink" label="Visit Masters Expo" icon-right="lucide-arrow-up-right" />
			</EmptyState>

			<template v-if="events.data.past.length">
				<h2 class="mt-16 text-display-xs font-bold text-ink-gray-9">Past events</h2>
				<div class="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
					<article v-for="event in events.data.past" :id="event.name" :key="event.name" class="card overflow-hidden">
						<img
							v-if="event.cover_image"
							:src="event.cover_image"
							:alt="event.title"
							loading="lazy"
							class="aspect-video w-full object-cover"
						/>
						<div class="p-5">
							<p class="text-sm-medium text-ink-gray-5">{{ dateRange(event) }}</p>
							<h3 class="mt-1 text-xl-semibold text-ink-gray-9">{{ event.title }}</h3>
							<p v-if="event.venue" class="mt-1 text-sm text-ink-gray-5">{{ event.venue }}</p>
							<p v-if="event.summary" class="mt-3 line-clamp-3 text-p-sm text-ink-gray-6">{{ event.summary }}</p>
						</div>
					</article>
				</div>
			</template>
		</template>
	</section>
</template>
