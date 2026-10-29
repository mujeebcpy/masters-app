<script setup>
import { asset, testimonials } from "@/data/site"
import PageHero from "@/components/PageHero.vue"
import SectionHeading from "@/components/SectionHeading.vue"
import { Avatar } from "frappe-ui"

const challenges = [
	{
		title: "Perception of luxury",
		text: "Solar installations were seen as a non-essential expense, limiting interest in the residential sector.",
	},
	{
		title: "Economic strain",
		text: "With households and businesses tightening budgets, investing in renewable energy took a back seat.",
	},
	{
		title: "Interrupted growth",
		text: "Supply chain disruptions and project delays further hampered progress in an already challenging period.",
	},
]

const story = [
	{
		year: "2022",
		title: "The turning point: a push for renewable energy",
		paragraphs: [
			"To reduce carbon emissions (Net Zero 2070) and align with the global push for sustainability (UN Sustainable Development Goals 2030), the Indian government turned its focus to renewable energy. The solar sector, with its immense potential, became a key pillar of this strategy. Alongside environmental goals, the government aimed to strengthen the Indian solar market by promoting the “Make in India” ideology, boosting domestic manufacturing and innovation.",
		],
	},
	{
		year: "DBT",
		title: "The subsidy scheme: a catalyst for growth",
		paragraphs: [
			"To encourage solar adoption in the residential sector, the government introduced an innovative DBT (Direct Benefit Transfer) subsidy scheme. It made solar installations more affordable for households by directing financial incentives to the end user.",
			"The scheme was a game-changer, but it came with its own challenges: centralised administration, complex registration processes, limited information channels and technological hurdles made it difficult for integrators to navigate and for consumers to benefit as intended.",
		],
	},
	{
		year: "Oct 2022",
		title: "The spark that lit the flame",
		paragraphs: [
			"In the first week of October 2022, someone made the effort to bring MNRE vendors under one roof through WhatsApp, inviting over 35 strangers to form a group. They were among the first to register under MNRE as approved vendors.",
			"At first the group's purpose was unclear, and many were sceptical about what it could achieve. Then came the pivotal moment: Mr. Jayakrishnan, creator of the Kerala MNRE vendors WhatsApp group, invited all members to a physical meeting on 10 October 2022.",
		],
	},
	{
		year: "10 Oct 2022",
		title: "From informal beginnings to formal recognition",
		paragraphs: [
			"Everyone in the room was a stranger, but as the introductions began it became clear that we all shared the same struggles and aspirations. Working in isolation was not the answer; collaboration was.",
			"For the first time we had a platform to share experiences, clarify doubts about the subsidy scheme and its registration process, and support one another. The idea of an association took root: a group dedicated to sharing insights, resolving issues and fostering growth for all members.",
			"The 35 members agreed to form a committee of eleven: Mr. Jayakrishnan as President, Mr. Reni as Vice President, Mr. Biju as Secretary, a Treasurer, and charter members in other key roles. More executive members joined soon after. Within two weeks the registration of the association was complete, and “MASTERS” was born.",
		],
	},
]
</script>

<template>
	<PageHero
		title="About us"
		eyebrow="Our story"
		subtitle="The journey of Kerala's solar vendors association: from a WhatsApp group of 35 strangers to a community of more than 600 members."
		:image="asset('images/photos/members-gathering.jpg')"
	/>

	<!-- Intro -->
	<section class="container-page grid gap-12 py-20 sm:py-24 lg:grid-cols-2 lg:gap-16">
		<div>
			<SectionHeading eyebrow="How we became Masters" title="Born out of a difficult year" />
			<p class="mt-6 text-p-lg text-ink-gray-7">
				In 2022, industries across the globe were fighting to regain their footing after the pandemic. For the
				Indian solar industry the struggle was particularly pronounced. The industry was seeing only modest
				gains and showing signs of stagnation, until the central government stepped in with bold measures to
				revolutionise the renewable energy sector.
			</p>
			<figure class="mt-8 rounded-6 border-l-4 border-brand-500 bg-brand-50 p-6">
				<span class="lucide-quote size-6 text-brand-500" aria-hidden="true" />
				<blockquote class="mt-2 font-display text-display-xs font-semibold text-ink-gray-9">
					From a few 32 or 36 members, it grew to more than 600.
				</blockquote>
			</figure>
		</div>
		<div class="space-y-4">
			<div v-for="(item, i) in challenges" :key="item.title" class="card flex gap-4 p-5">
				<span class="font-display text-display-sm font-bold text-brand-200">0{{ i + 1 }}</span>
				<div>
					<h3 class="text-lg-semibold text-ink-gray-9">{{ item.title }}</h3>
					<p class="mt-1 text-p-base text-ink-gray-6">{{ item.text }}</p>
				</div>
			</div>
		</div>
	</section>

	<!-- Timeline -->
	<section class="bg-surface-gray-1">
		<div class="container-page grid gap-12 py-20 sm:py-24 lg:grid-cols-[1fr_1.4fr]">
			<div class="lg:sticky lg:top-28 lg:self-start">
				<SectionHeading eyebrow="Milestones" title="How Masters came together" />
				<img
					:src="asset('images/photos/executive-committee.jpg')"
					alt="Masters executive committee"
					class="mt-8 w-full rounded-7 object-cover shadow-lg"
					loading="lazy"
				/>
			</div>
			<ol class="relative space-y-10 border-l-2 border-brand-200 pl-8">
				<li v-for="step in story" :key="step.title" class="relative">
					<span
						class="absolute -left-[2.6rem] top-1 grid size-5 place-items-center rounded-full bg-brand-500 ring-4 ring-brand-100"
						aria-hidden="true"
					/>
					<p class="text-sm-semibold uppercase tracking-wider text-brand-600">{{ step.year }}</p>
					<h3 class="mt-1 text-display-xs font-bold text-ink-gray-9">{{ step.title }}</h3>
					<p v-for="(p, i) in step.paragraphs" :key="i" class="mt-3 text-p-base text-ink-gray-7">{{ p }}</p>
				</li>
			</ol>
		</div>
	</section>

	<!-- Mission & vision -->
	<section class="container-page py-20 sm:py-24">
		<div class="grid gap-6 lg:grid-cols-[1fr_1fr_0.9fr]">
			<div class="card p-8">
				<div class="grid size-12 place-items-center rounded-5 bg-brand-500 text-white">
					<span class="lucide-target size-6" aria-hidden="true" />
				</div>
				<h2 class="mt-6 text-display-sm font-bold text-ink-gray-9">Mission</h2>
				<p class="mt-3 text-p-base text-ink-gray-7">
					To support MNRE-registered vendors across Kerala by promoting quality installations, reliable
					after-sales service and professional growth, setting high industry standards and fostering
					collaboration among all members.
				</p>
			</div>
			<div class="rounded-7 bg-forest p-8 text-white">
				<div class="grid size-12 place-items-center rounded-5 bg-lime text-forest">
					<span class="lucide-eye size-6" aria-hidden="true" />
				</div>
				<h2 class="mt-6 text-display-sm font-bold">Vision</h2>
				<p class="mt-3 text-p-base text-white/75">
					A Kerala where every MNRE-registered vendor delivers high-quality installations and exceptional
					after-sales service, backed by shared industry standards, collaboration and continuous professional
					growth.
				</p>
			</div>
			<img
				:src="asset('images/photos/training-session.jpg')"
				alt="Masters training session"
				class="h-full min-h-64 w-full rounded-7 object-cover"
				loading="lazy"
			/>
		</div>
	</section>

	<!-- Testimonials -->
	<section class="bg-brand-50/60">
		<div class="container-page py-20 sm:py-24">
			<SectionHeading center eyebrow="Testimonials" title="Hear from our members" />
			<div class="mt-12 grid gap-5 md:grid-cols-2">
				<figure v-for="t in testimonials" :key="t.name" class="card flex flex-col p-7">
					<span class="lucide-quote size-7 text-brand-400" aria-hidden="true" />
					<blockquote class="mt-4 flex-1 text-p-lg text-ink-gray-7">{{ t.quote }}</blockquote>
					<figcaption class="mt-6 flex items-center gap-3">
						<Avatar :label="t.name" size="lg" theme="green" />
						<span class="text-base-semibold text-ink-gray-9">{{ t.name }}</span>
					</figcaption>
				</figure>
			</div>
		</div>
	</section>
</template>
