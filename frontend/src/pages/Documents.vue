<script setup>
import { computed } from "vue"
import { Button, Skeleton, useCall } from "frappe-ui"
import { asset } from "@/data/site"
import { formatDate, websiteMethod } from "@/api"
import PageHero from "@/components/PageHero.vue"
import EmptyState from "@/components/EmptyState.vue"

const documents = useCall({ url: websiteMethod("get_documents"), cacheKey: "documents" })

const groups = computed(() => {
	const map = new Map()
	for (const doc of documents.data || []) {
		const key = doc.category || "General"
		if (!map.has(key)) map.set(key, [])
		map.get(key).push(doc)
	}
	return [...map.entries()]
})

function extension(url) {
	return (url?.split("?")[0].split(".").pop() || "file").toUpperCase()
}
</script>

<template>
	<PageHero
		title="Documents"
		eyebrow="Resources"
		subtitle="Circulars, forms and brand resources from Masters Association."
		:image="asset('images/photos/training-session.jpg')"
	/>

	<section class="container-page py-14 sm:py-16">
		<div v-if="!documents.data" class="grid gap-4 sm:grid-cols-2">
			<Skeleton v-for="i in 4" :key="i" class="h-28 rounded-7" />
		</div>
		<template v-else-if="groups.length">
			<div v-for="[category, docs] in groups" :key="category" class="mt-10 first:mt-0">
				<h2 class="text-sm-semibold uppercase tracking-wider text-brand-700">{{ category }}</h2>
				<ul class="mt-4 grid gap-4 sm:grid-cols-2">
					<li
						v-for="doc in docs"
						:key="doc.name"
						class="card flex items-center gap-4 p-5 transition hover:border-brand-200 hover:shadow-lg"
					>
						<div
							class="grid size-14 shrink-0 place-items-center rounded-5 bg-brand-50 text-xs-semibold text-brand-700"
						>
							<span class="lucide-file-text size-6" aria-hidden="true" />
						</div>
						<div class="min-w-0 flex-1">
							<p class="truncate text-lg-semibold text-ink-gray-9">{{ doc.title }}</p>
							<p class="mt-1 line-clamp-2 text-sm text-ink-gray-5">
								{{ [extension(doc.file), formatDate(doc.document_date), doc.description].filter(Boolean).join(" · ") }}
							</p>
						</div>
						<Button :href="doc.file" icon="lucide-download" variant="subtle" size="md" :aria-label="`Download ${doc.title}`" />
					</li>
				</ul>
			</div>
		</template>
		<EmptyState v-else icon="lucide-folder-open" title="No documents published yet" />
	</section>
</template>
