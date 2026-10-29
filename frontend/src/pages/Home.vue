<script setup>
import { ref } from "vue"
import { Button, Skeleton, useCall } from "frappe-ui"
import { asset, highlights, reasons, stats } from "@/data/site"
import { formatDate, websiteMethod } from "@/api"
import SectionHeading from "@/components/SectionHeading.vue"
import MemberCard from "@/components/MemberCard.vue"
import MemberDialog from "@/components/MemberDialog.vue"
import Lightbox from "@/components/Lightbox.vue"

const home = useCall({ url: websiteMethod("get_home_data"), cacheKey: "home-data" })
const selectedMember = ref(null)
const lightboxIndex = ref(null)
</script>

<template>
	<!-- Hero -->
	<section class="relative isolate overflow-hidden bg-forest">
		<img
			:src="asset('images/photos/members-gathering.jpg')"
			alt=""
			class="absolute inset-0 -z-10 size-full object-cover opacity-35"
		/>
		<div class="absolute inset-0 -z-10 bg-gradient-to-r from-forest via-forest/85 to-forest/30" aria-hidden="true" />
		<div
			class="absolute -left-32 top-1/3 -z-10 size-96 rounded-full bg-lime/20 blur-3xl"
			aria-hidden="true"
		/>
		<div class="container-page pb-28 pt-20 sm:pb-36 sm:pt-28">
			<span
				class="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-sm-medium text-white/90 backdrop-blur"
			>
				<span class="lucide-sun size-4 text-lime" aria-hidden="true" />
				Ministry Approved Solar Traders · Kerala
			</span>
			<h1 class="mt-6 max-w-3xl text-display-md font-extrabold text-white sm:text-display-xl lg:text-display-2xl">
				A trusted network of
				<span class="text-gradient">MNRE-registered</span>
				solar vendors
			</h1>
			<p class="mt-6 max-w-2xl text-p-xl text-white/75">
				Masters Association connects MNRE-registered solar vendors across Kerala, ensuring quality
				installations and professional service standards. Since its formation, the association has
				championed collaboration, reliability and industry growth.
			</p>
			<div class="mt-9 flex flex-wrap gap-3">
				<Button
					variant="solid"
					theme="green"
					size="lg"
					:route="{ path: '/become-members' }"
					label="Join Masters"
					icon-right="lucide-arrow-right"
				/>
				<Button
					size="lg"
					class="!bg-white/10 !text-white backdrop-blur hover:!bg-white/20"
					:route="{ path: '/members' }"
					label="Meet our members"
				/>
			</div>
		</div>
	</section>

	<!-- Stats -->
	<section class="container-page relative z-10 -mt-16">
		<dl class="grid grid-cols-2 overflow-hidden rounded-7 border border-outline-gray-1 bg-surface-base shadow-xl lg:grid-cols-4">
			<div
				v-for="(stat, i) in stats"
				:key="stat.label"
				class="border-outline-gray-1 p-6 sm:p-8"
				:class="[i % 2 === 0 && 'border-r', i < 2 && 'border-b lg:border-b-0', i === 1 && 'lg:border-r']"
			>
				<dt class="text-sm-medium text-ink-gray-5">{{ stat.label }}</dt>
				<dd class="mt-2 font-display text-display-sm font-bold text-ink-gray-9 sm:text-display-md">
					{{ stat.value }}<span class="text-brand-500">{{ stat.suffix }}</span>
				</dd>
			</div>
		</dl>
	</section>

	<!-- Who we are -->
	<section class="container-page grid items-center gap-12 py-20 sm:py-28 lg:grid-cols-2 lg:gap-16">
		<div class="relative">
			<img
				:src="asset('images/photos/members-meeting.jpg')"
				alt="Masters members at an association meeting"
				class="aspect-[4/3.4] w-full rounded-7 object-cover shadow-xl"
				loading="lazy"
			/>
			<div
				class="absolute -bottom-6 -right-2 max-w-[16rem] rounded-6 bg-forest p-5 text-white shadow-2xl sm:-right-6"
			>
				<p class="font-display text-display-md font-bold text-lime">2022</p>
				<p class="mt-1 text-p-sm text-white/75">Founded in October 2022 by MNRE-registered vendors</p>
			</div>
		</div>
		<div>
			<SectionHeading eyebrow="Who we are" title="Kerala's largest solar vendors association" />
			<p class="mt-6 text-p-lg text-ink-gray-7">
				Masters Association was formed in October 2022 by a group of vendors registered with the MNRE
				subsidy program. Vendors from every district of Kerala have since joined as members, making Masters
				the largest association of its kind in the state.
			</p>
			<p class="mt-4 text-p-lg text-ink-gray-7">
				Our focus is simple: help new vendors deliver quality installations and dependable after-sales
				service, through shared expertise and good practice.
			</p>
			<Button
				class="mt-8"
				size="lg"
				variant="outline"
				:route="{ path: '/about' }"
				label="More about us"
				icon-right="lucide-arrow-right"
			/>
		</div>
	</section>

	<!-- Professional excellence -->
	<section class="bg-brand-50/60">
		<div class="container-page grid items-center gap-12 py-20 sm:py-28 lg:grid-cols-[1.1fr_0.9fr]">
			<div>
				<SectionHeading
					eyebrow="Masters"
					title="Committed to professional excellence"
					description="We support MNRE-registered vendors across Kerala to deliver quality installations and reliable after-sales service, setting industry standards and fostering collaboration."
				/>
				<ul class="mt-8 grid gap-3 sm:grid-cols-2">
					<li
						v-for="item in highlights"
						:key="item"
						class="flex items-center gap-3 rounded-5 border border-brand-100 bg-surface-base px-4 py-3.5"
					>
						<span class="grid size-7 shrink-0 place-items-center rounded-full bg-brand-500 text-white">
							<span class="lucide-check size-4" aria-hidden="true" />
						</span>
						<span class="text-base-medium text-ink-gray-8">{{ item }}</span>
					</li>
				</ul>
				<Button
					class="mt-8"
					variant="solid"
					theme="green"
					size="lg"
					:route="{ path: '/contact' }"
					label="Contact us"
				/>
			</div>
			<div class="relative mx-auto w-full max-w-md">
				<div
					class="absolute inset-x-6 bottom-0 top-16 rounded-[2.5rem] bg-gradient-to-br from-lime to-teal-brand"
					aria-hidden="true"
				/>
				<img
					:src="asset('images/photos/solar-technician.png')"
					alt="Solar technician holding a solar panel"
					class="relative w-full"
					loading="lazy"
				/>
			</div>
		</div>
	</section>

	<!-- Why Masters -->
	<section class="container-page py-20 sm:py-28">
		<div class="flex flex-col justify-between gap-6 md:flex-row md:items-end">
			<SectionHeading
				eyebrow="Why Masters"
				title="A name members trust"
				description="Our commitment to quality and the way we share knowledge with every member sets us apart."
			/>
			<Button size="lg" variant="outline" :route="{ path: '/contact' }" label="Connect with us" class="shrink-0" />
		</div>
		<div class="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
			<div
				v-for="reason in reasons"
				:key="reason.title"
				class="card group p-6 transition hover:border-brand-200 hover:shadow-lg"
			>
				<div
					class="grid size-12 place-items-center rounded-5 bg-brand-50 text-brand-600 transition group-hover:bg-brand-500 group-hover:text-white"
				>
					<span :class="reason.icon" class="size-6" aria-hidden="true" />
				</div>
				<h3 class="mt-5 text-xl-semibold text-ink-gray-9">{{ reason.title }}</h3>
				<p class="mt-2 text-p-base text-ink-gray-6">{{ reason.text }}</p>
			</div>
		</div>
	</section>

	<!-- Team -->
	<section v-if="home.loading || home.data?.team?.length" class="bg-surface-gray-1">
		<div class="container-page py-20 sm:py-28">
			<div class="flex flex-col justify-between gap-6 md:flex-row md:items-end">
				<SectionHeading eyebrow="Our team" title="Meet the people leading Masters" />
				<Button
					size="lg"
					variant="outline"
					:route="{ path: '/members' }"
					label="View all members"
					icon-right="lucide-arrow-right"
					class="shrink-0"
				/>
			</div>
			<div
				class="mt-12 grid gap-5 sm:grid-cols-2"
				:class="home.data?.team?.length === 3 ? 'lg:grid-cols-3 lg:px-24' : 'lg:grid-cols-4'"
			>
				<template v-if="!home.data">
					<Skeleton v-for="i in 4" :key="i" class="aspect-[4/5.6] rounded-7" />
				</template>
				<MemberCard
					v-for="member in home.data?.team"
					v-else
					:key="member.id + member.position"
					:member="member"
					@select="selectedMember = $event"
				/>
			</div>
		</div>
	</section>

	<!-- Upcoming events -->
	<section v-if="home.data?.upcoming_events?.length" class="container-page pt-20 sm:pt-28">
		<SectionHeading eyebrow="Events" title="Coming up" />
		<div class="mt-10 grid gap-5 md:grid-cols-3">
			<router-link
				v-for="event in home.data.upcoming_events"
				:key="event.name"
				:to="{ path: '/events', hash: `#${event.name}` }"
				class="card flex gap-4 p-5 transition hover:border-brand-200 hover:shadow-lg"
			>
				<div class="grid size-16 shrink-0 place-items-center rounded-5 bg-brand-500 text-center text-white">
					<div>
						<p class="font-display text-display-xs font-bold leading-none">
							{{ formatDate(event.start_date, { day: "2-digit" }) }}
						</p>
						<p class="text-xs-semibold uppercase">{{ formatDate(event.start_date, { month: "short" }) }}</p>
					</div>
				</div>
				<div class="min-w-0">
					<p class="text-lg-semibold text-ink-gray-9">{{ event.title }}</p>
					<p v-if="event.venue" class="mt-1 truncate text-sm text-ink-gray-5">{{ event.venue }}</p>
				</div>
			</router-link>
		</div>
	</section>

	<!-- Glimpses -->
	<section v-if="home.loading || home.data?.glimpses?.length" class="container-page py-20 sm:py-28">
		<SectionHeading
			center
			eyebrow="Gallery"
			title="Glimpses from Masters"
			description="Moments, innovations and experiences from Masters Expo and our association events."
		/>
		<div class="mt-12 grid auto-rows-[10rem] grid-cols-2 gap-3 sm:auto-rows-[13rem] md:grid-cols-4">
			<template v-if="!home.data">
				<Skeleton v-for="i in 8" :key="i" class="rounded-6" />
			</template>
			<button
				v-for="(photo, i) in home.data?.glimpses"
				v-else
				:key="photo.name"
				type="button"
				class="group relative overflow-hidden rounded-6 bg-surface-gray-2"
				:class="[i % 6 === 0 && 'col-span-2 row-span-2']"
				:aria-label="`Open ${photo.title}`"
				@click="lightboxIndex = i"
			>
				<img
					:src="photo.image"
					:alt="photo.title"
					loading="lazy"
					class="size-full object-cover transition duration-500 group-hover:scale-105"
				/>
				<span
					class="absolute inset-0 bg-gradient-to-t from-forest/70 to-transparent opacity-0 transition group-hover:opacity-100"
				/>
			</button>
		</div>
		<div class="mt-10 text-center">
			<Button size="lg" variant="outline" :route="{ path: '/gallery' }" label="View full gallery" />
		</div>
	</section>

	<!-- CTA -->
	<section class="container-page pb-20 sm:pb-28">
		<div
			class="relative isolate overflow-hidden rounded-[2rem] bg-gradient-to-br from-brand-700 via-brand-800 to-forest px-6 py-14 sm:px-14 sm:py-16"
		>
			<img
				:src="asset('images/photos/solar-field.jpg')"
				alt=""
				class="absolute inset-0 -z-10 size-full object-cover opacity-15 mix-blend-luminosity"
			/>
			<div class="grid items-center gap-8 lg:grid-cols-[1fr_auto]">
				<div>
					<h2 class="text-display-sm font-bold text-white sm:text-display-md">Grow with Kerala's solar community</h2>
					<p class="mt-3 max-w-xl text-p-lg text-white/75">
						Registration is open for MNRE-registered vendors. Join over 600 members sharing knowledge,
						training and support.
					</p>
				</div>
				<Button
					variant="solid"
					size="lg"
					class="!bg-lime !text-forest hover:!bg-white"
					:route="{ path: '/become-members' }"
					label="Become a member"
					icon-right="lucide-arrow-right"
				/>
			</div>
		</div>
	</section>

	<MemberDialog :member="selectedMember" @close="selectedMember = null" />
	<Lightbox v-if="home.data?.glimpses" v-model:index="lightboxIndex" :items="home.data.glimpses" />
</template>
