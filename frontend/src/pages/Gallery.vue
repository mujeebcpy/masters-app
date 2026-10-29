<script setup>
import { computed, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { Skeleton, TabButtons, useCall } from "frappe-ui"
import { asset, site } from "@/data/site"
import { websiteMethod } from "@/api"
import PageHero from "@/components/PageHero.vue"
import Lightbox from "@/components/Lightbox.vue"
import EmptyState from "@/components/EmptyState.vue"

const props = defineProps({ initialTab: { type: String, default: "Photo" } })
const router = useRouter()

const gallery = useCall({ url: websiteMethod("get_gallery"), cacheKey: "gallery" })
const tab = ref(props.initialTab)
const album = ref(null)
const lightboxIndex = ref(null)

watch(
	() => props.initialTab,
	(value) => (tab.value = value)
)
watch(tab, (value) => {
	album.value = null
	router.replace(value === "Video" ? "/video-gallery" : "/photo-gallery")
})

const tabs = [
	{ value: "Photo", label: "Photos", icon: "lucide-image" },
	{ value: "Video", label: "Videos", icon: "lucide-video" },
]

const ofType = computed(() => (gallery.data || []).filter((i) => i.media_type === tab.value))
const albums = computed(() => [...new Set(ofType.value.map((i) => i.album).filter(Boolean))])
const items = computed(() => ofType.value.filter((i) => !album.value || i.album === album.value))
</script>

<template>
	<PageHero
		title="Gallery"
		eyebrow="Glimpses from Masters"
		subtitle="Moments from Masters Expo, association meetings, trainings and events."
		:image="asset('images/gallery/expo-2025-08.jpg')"
	/>

	<section class="container-page py-14 sm:py-16">
		<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
			<TabButtons v-model="tab" :options="tabs" />
			<div v-if="albums.length > 1" class="flex flex-wrap gap-2">
				<button
					v-for="a in [null, ...albums]"
					:key="a ?? 'all'"
					type="button"
					class="rounded-full border px-3.5 py-1.5 text-sm-medium transition"
					:class="
						album === a
							? 'border-brand-500 bg-brand-500 text-white'
							: 'border-outline-gray-2 text-ink-gray-7 hover:border-brand-300'
					"
					@click="album = a"
				>
					{{ a ?? "All" }}
				</button>
			</div>
		</div>

		<div v-if="!gallery.data" class="mt-8 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
			<Skeleton v-for="i in 8" :key="i" class="aspect-square rounded-6" />
		</div>

		<div v-else-if="items.length && tab === 'Photo'" class="mt-8 columns-2 gap-3 md:columns-3 lg:columns-4">
			<button
				v-for="(item, i) in items"
				:key="item.name"
				type="button"
				class="group relative mb-3 block w-full overflow-hidden rounded-6 bg-surface-gray-2"
				:aria-label="`Open ${item.title}`"
				@click="lightboxIndex = i"
			>
				<img
					:src="item.image"
					:alt="item.title"
					loading="lazy"
					class="w-full transition duration-500 group-hover:scale-105"
				/>
				<span
					class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-forest/80 to-transparent p-3 pt-10 text-left text-sm-medium text-white opacity-0 transition group-hover:opacity-100"
				>
					{{ item.title }}
				</span>
			</button>
		</div>

		<div v-else-if="items.length" class="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
			<button
				v-for="(item, i) in items"
				:key="item.name"
				type="button"
				class="group card overflow-hidden text-left transition hover:shadow-lg"
				@click="lightboxIndex = i"
			>
				<div class="relative aspect-video bg-forest">
					<img
						v-if="item.youtube_id"
						:src="`https://i.ytimg.com/vi/${item.youtube_id}/hqdefault.jpg`"
						:alt="item.title"
						loading="lazy"
						class="size-full object-cover opacity-90 transition group-hover:opacity-100"
					/>
					<span class="absolute inset-0 grid place-items-center">
						<span class="grid size-14 place-items-center rounded-full bg-white/90 text-brand-700 shadow-lg transition group-hover:scale-110">
							<span class="lucide-play ml-0.5 size-6" aria-hidden="true" />
						</span>
					</span>
				</div>
				<div class="p-4">
					<p class="text-lg-semibold text-ink-gray-9">{{ item.title }}</p>
					<p v-if="item.description" class="mt-1 line-clamp-2 text-sm text-ink-gray-5">{{ item.description }}</p>
				</div>
			</button>
		</div>

		<EmptyState
			v-else
			class="mt-8"
			:icon="tab === 'Video' ? 'lucide-video' : 'lucide-image'"
			:title="tab === 'Video' ? 'Videos coming soon' : 'No photos yet'"
			:description="tab === 'Video' ? 'Meanwhile, watch Masters Expo highlights on our YouTube channel.' : ''"
		>
			<a
				v-if="tab === 'Video'"
				:href="site.socials.find((s) => s.key === 'youtube').href"
				target="_blank"
				rel="noopener"
				class="mt-2 inline-flex items-center gap-1 text-base-medium text-brand-700 hover:underline"
			>
				Visit our YouTube channel <span class="lucide-arrow-up-right size-4" aria-hidden="true" />
			</a>
		</EmptyState>
	</section>

	<Lightbox v-model:index="lightboxIndex" :items="items" />
</template>
