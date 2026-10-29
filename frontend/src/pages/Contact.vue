<script setup>
import { reactive, ref } from "vue"
import { Alert, Button, FormControl, useCall } from "frappe-ui"
import { asset, site } from "@/data/site"
import { errorText, websiteMethod } from "@/api"
import PageHero from "@/components/PageHero.vue"
import SocialIcon from "@/components/SocialIcon.vue"

const form = reactive({ full_name: "", mobile: "", email: "", place: "", message: "" })
const errors = ref({})
const sent = ref(false)

const submission = useCall({ url: websiteMethod("submit_enquiry"), method: "POST", immediate: false })

async function submit() {
	const e = {}
	if (!form.full_name.trim()) e.full_name = "Please enter your name."
	if (!/^\+?[\d\s-]{10,15}$/.test(form.mobile.trim())) e.mobile = "Please enter a valid mobile number."
	if (form.email && !/^\S+@\S+\.\S+$/.test(form.email)) e.email = "Please enter a valid email address."
	if (!form.message.trim()) e.message = "Please enter a message."
	errors.value = e
	if (Object.keys(e).length) return

	try {
		await submission.submit({ enquiry_type: "Contact", ...form })
	} catch {
		return
	}
	sent.value = true
}

const channels = [
	{ icon: "lucide-map-pin", label: "Visit us", value: site.address, href: site.mapsLink, external: true },
	{ icon: "lucide-mail", label: "Write to us", value: site.email, href: `mailto:${site.email}` },
	{ icon: "lucide-phone", label: "Call us", value: site.phone, href: site.phoneHref },
]
</script>

<template>
	<PageHero
		title="Contact"
		eyebrow="Get in touch"
		subtitle="Stay connected with us for updates, opportunities and participation."
		:image="asset('images/photos/members-meeting.jpg')"
	/>

	<section class="container-page py-14 sm:py-16">
		<div class="grid gap-4 md:grid-cols-3">
			<a
				v-for="c in channels"
				:key="c.label"
				:href="c.href"
				:target="c.external ? '_blank' : undefined"
				rel="noopener"
				class="card group flex gap-4 p-6 transition hover:border-brand-200 hover:shadow-lg"
			>
				<span
					class="grid size-12 shrink-0 place-items-center rounded-5 bg-brand-50 text-brand-600 transition group-hover:bg-brand-500 group-hover:text-white"
				>
					<span :class="c.icon" class="size-5" aria-hidden="true" />
				</span>
				<span>
					<span class="block text-sm text-ink-gray-5">{{ c.label }}</span>
					<span class="mt-1 block text-p-base font-medium text-ink-gray-8">{{ c.value }}</span>
				</span>
			</a>
		</div>

		<div class="mt-10 grid gap-10 lg:grid-cols-2">
			<div>
				<div v-if="sent" class="card p-8 text-center sm:p-12">
					<div class="mx-auto grid size-16 place-items-center rounded-full bg-brand-100 text-brand-600">
						<span class="lucide-circle-check size-8" aria-hidden="true" />
					</div>
					<h2 class="mt-6 text-display-sm font-bold text-ink-gray-9">Message sent</h2>
					<p class="mt-3 text-p-lg text-ink-gray-6">Thanks, {{ form.full_name }}. We'll be in touch soon.</p>
				</div>
				<form v-else class="card space-y-5 p-6 sm:p-8" novalidate @submit.prevent="submit">
					<div>
						<h2 class="text-display-xs font-bold text-ink-gray-9">Send us a message</h2>
						<p class="mt-1 text-p-base text-ink-gray-5">Interested in joining Masters, or have a question? Write to us.</p>
					</div>
					<div class="grid gap-5 sm:grid-cols-2">
						<FormControl v-model="form.full_name" label="Name" size="lg" variant="outline" required :error="errors.full_name" />
						<FormControl v-model="form.mobile" type="tel" label="Mobile" size="lg" variant="outline" required :error="errors.mobile" />
						<FormControl v-model="form.email" type="email" label="Email" size="lg" variant="outline" :error="errors.email" />
						<FormControl v-model="form.place" label="Place" size="lg" variant="outline" />
					</div>
					<FormControl
						v-model="form.message"
						type="textarea"
						label="Message"
						:rows="5"
						variant="outline"
						required
						:error="errors.message"
					/>
					<Alert v-if="submission.error" theme="red" title="Couldn't send" :description="errorText(submission.error)" />
					<Button
						type="submit"
						variant="solid"
						theme="green"
						size="lg"
						class="w-full sm:w-auto"
						label="Send message"
						icon-right="lucide-send"
						:loading="submission.loading"
					/>
				</form>
			</div>
			<div class="flex flex-col gap-5">
				<iframe
					:src="site.mapsEmbed"
					title="Masters Association office location"
					class="min-h-80 w-full flex-1 rounded-7 border border-outline-gray-1"
					loading="lazy"
					referrerpolicy="no-referrer-when-downgrade"
				/>
				<div class="card flex flex-wrap items-center justify-between gap-4 p-5">
					<p class="text-lg-semibold text-ink-gray-9">Follow us</p>
					<div class="flex gap-2">
						<a
							v-for="social in site.socials"
							:key="social.key"
							:href="social.href"
							target="_blank"
							rel="noopener"
							:aria-label="social.label"
							class="grid size-10 place-items-center rounded-full bg-brand-50 text-brand-700 transition hover:bg-brand-500 hover:text-white"
						>
							<SocialIcon :name="social.key" class="size-4" />
						</a>
					</div>
				</div>
			</div>
		</div>
	</section>
</template>
