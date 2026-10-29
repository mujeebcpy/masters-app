<script setup>
import { site } from "@/data/site"
import SocialIcon from "./SocialIcon.vue"

const quickLinks = [
	{ label: "About us", route: "/about" },
	{ label: "Become a member", route: "/become-members" },
	{ label: "Members", route: "/members" },
	{ label: "Gallery", route: "/gallery" },
	{ label: "Events", route: "/events" },
	{ label: "Documents", route: "/documents" },
	{ label: "Grievance", route: "/grievance" },
	{ label: "Contact", route: "/contact" },
]
const year = new Date().getFullYear()
</script>

<template>
	<footer class="relative overflow-hidden bg-forest text-white">
		<div
			class="pointer-events-none absolute -right-40 -top-40 size-[28rem] rounded-full bg-gradient-to-br from-lime/20 to-teal-brand/10 blur-3xl"
			aria-hidden="true"
		/>
		<div class="container-page relative grid gap-10 py-14 sm:grid-cols-2 lg:grid-cols-12 lg:gap-8">
			<div class="lg:col-span-4">
				<img :src="site.logo.white" :alt="site.name" class="h-10 w-auto" />
				<p class="mt-5 max-w-xs text-p-base text-white/70">
					{{ site.tagline }}. Kerala's largest association of MNRE-registered solar vendors.
				</p>
				<div class="mt-6 flex gap-2">
					<a
						v-for="social in site.socials"
						:key="social.key"
						:href="social.href"
						target="_blank"
						rel="noopener"
						:aria-label="social.label"
						class="grid size-10 place-items-center rounded-full bg-white/10 text-white/80 transition hover:bg-lime hover:text-forest"
					>
						<SocialIcon :name="social.key" class="size-4" />
					</a>
				</div>
			</div>

			<div class="lg:col-span-3">
				<h3 class="text-lg-semibold">Quick links</h3>
				<ul class="mt-4 grid grid-cols-2 gap-x-4 gap-y-2.5 lg:grid-cols-1">
					<li v-for="link in quickLinks" :key="link.route">
						<router-link :to="link.route" class="text-base text-white/70 transition hover:text-lime">
							{{ link.label }}
						</router-link>
					</li>
				</ul>
			</div>

			<div class="lg:col-span-3">
				<h3 class="text-lg-semibold">Get in touch</h3>
				<ul class="mt-4 space-y-4 text-base text-white/70">
					<li class="flex gap-3">
						<span class="lucide-map-pin mt-0.5 size-4 shrink-0 text-lime" aria-hidden="true" />
						<a :href="site.mapsLink" target="_blank" rel="noopener" class="text-p-base hover:text-lime">
							{{ site.address }}
						</a>
					</li>
					<li class="flex gap-3">
						<span class="lucide-mail mt-0.5 size-4 shrink-0 text-lime" aria-hidden="true" />
						<a :href="`mailto:${site.email}`" class="hover:text-lime">{{ site.email }}</a>
					</li>
					<li class="flex gap-3">
						<span class="lucide-phone mt-0.5 size-4 shrink-0 text-lime" aria-hidden="true" />
						<a :href="site.phoneHref" class="hover:text-lime">{{ site.phone }}</a>
					</li>
				</ul>
			</div>

			<div class="lg:col-span-2">
				<h3 class="text-lg-semibold">Masters Expo</h3>
				<p class="mt-4 text-p-base text-white/70">Kerala's largest solar expo, organised by Masters.</p>
				<a
					:href="site.expoLink"
					target="_blank"
					rel="noopener"
					class="mt-3 inline-flex items-center gap-1 text-base-medium text-lime hover:underline"
				>
					expokerala.com
					<span class="lucide-arrow-up-right size-4" aria-hidden="true" />
				</a>
				<a
					:href="site.brandBook"
					target="_blank"
					class="mt-3 flex items-center gap-1 text-base-medium text-white/70 hover:text-lime"
				>
					<span class="lucide-file-text size-4" aria-hidden="true" />
					Brand book
				</a>
			</div>
		</div>
		<div class="border-t border-white/10">
			<div
				class="container-page flex flex-col gap-2 py-5 text-sm text-white/50 sm:flex-row sm:items-center sm:justify-between"
			>
				<p>© {{ year }} Masters Association ({{ site.fullName }}). All rights reserved.</p>
				<a href="/login" class="hover:text-white">Member &amp; admin login</a>
			</div>
		</div>
	</footer>
</template>
