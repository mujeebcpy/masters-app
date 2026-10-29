<script setup>
import { reactive, ref } from "vue"
import { Alert, Button, FormControl, TabButtons, useCall } from "frappe-ui"
import { asset, site } from "@/data/site"
import { errorText, websiteMethod } from "@/api"
import PageHero from "@/components/PageHero.vue"

const raisedByOptions = [
	{ value: "Consumer", label: "Consumer" },
	{ value: "Vendor", label: "Vendor" },
	{ value: "Member", label: "Member" },
]

const form = reactive({
	complainant_type: "Consumer",
	on_behalf_of: "",
	full_name: "",
	mobile: "",
	email: "",
	place: "",
	subject: "",
	message: "",
})
const errors = ref({})
const reference = ref(null)

const submission = useCall({ url: websiteMethod("submit_enquiry"), method: "POST", immediate: false })

async function submit() {
	const e = {}
	if (!form.full_name.trim()) e.full_name = "Please enter your name."
	if (!/^\+?[\d\s-]{10,15}$/.test(form.mobile.trim())) e.mobile = "Please enter a valid mobile number."
	if (form.email && !/^\S+@\S+\.\S+$/.test(form.email)) e.email = "Please enter a valid email address."
	if (!form.message.trim()) e.message = "Please describe your grievance."
	errors.value = e
	if (Object.keys(e).length) return

	try {
		await submission.submit({ enquiry_type: "Grievance", ...form })
	} catch {
		return
	}
	reference.value = submission.data.name
}
</script>

<template>
	<PageHero
		title="Grievance"
		eyebrow="We're here to help"
		subtitle="Raise a concern about a solar installation, a vendor or the association. Our grievance committee reviews every submission."
		:image="asset('images/photos/solar-field.jpg')"
	/>

	<section class="container-page grid gap-10 py-14 sm:py-16 lg:grid-cols-[1.3fr_0.7fr]">
		<div v-if="reference" class="card p-8 text-center sm:p-12">
			<div class="mx-auto grid size-16 place-items-center rounded-full bg-brand-100 text-brand-600">
				<span class="lucide-circle-check size-8" aria-hidden="true" />
			</div>
			<h2 class="mt-6 text-display-sm font-bold text-ink-gray-9">Grievance submitted</h2>
			<p class="mx-auto mt-3 max-w-md text-p-lg text-ink-gray-6">
				Thank you. Our team will contact you on {{ form.mobile }} once it has been reviewed.
			</p>
			<p class="mt-4 text-sm text-ink-gray-5">Reference: {{ reference }}</p>
		</div>

		<form v-else class="card space-y-5 p-6 sm:p-8" novalidate @submit.prevent="submit">
			<div>
				<h2 class="text-display-xs font-bold text-ink-gray-9">Submit your grievance</h2>
				<p class="mt-1 text-p-base text-ink-gray-5">Fields marked * are required.</p>
			</div>
			<div class="space-y-1.5">
				<p class="text-sm text-ink-gray-6">I am a</p>
				<TabButtons v-model="form.complainant_type" :options="raisedByOptions" />
			</div>
			<FormControl
				v-model="form.on_behalf_of"
				label="On behalf of"
				description="If you are raising this for someone else, enter their name."
				size="lg"
				variant="outline"
			/>
			<div class="grid gap-5 sm:grid-cols-2">
				<FormControl v-model="form.full_name" label="Your name" size="lg" variant="outline" required :error="errors.full_name" />
				<FormControl v-model="form.mobile" type="tel" label="Mobile" size="lg" variant="outline" required :error="errors.mobile" />
				<FormControl v-model="form.email" type="email" label="Email" size="lg" variant="outline" :error="errors.email" />
				<FormControl v-model="form.place" label="Place" size="lg" variant="outline" />
			</div>
			<FormControl v-model="form.subject" label="Subject" size="lg" variant="outline" />
			<FormControl
				v-model="form.message"
				type="textarea"
				label="Details"
				:rows="6"
				variant="outline"
				required
				:error="errors.message"
				placeholder="Describe the issue, the vendor involved and any dates or references."
			/>
			<Alert v-if="submission.error" theme="red" title="Couldn't submit" :description="errorText(submission.error)" />
			<div class="flex justify-end">
				<Button
					type="submit"
					variant="solid"
					theme="green"
					size="lg"
					label="Submit grievance"
					icon-right="lucide-send"
					:loading="submission.loading"
				/>
			</div>
		</form>

		<aside class="space-y-5">
			<div class="rounded-7 bg-forest p-6 text-white">
				<span class="lucide-shield-check size-8 text-lime" aria-hidden="true" />
				<h3 class="mt-4 text-xl-semibold">How we handle grievances</h3>
				<ol class="mt-4 space-y-3 text-p-sm text-white/75">
					<li class="flex gap-3"><span class="font-display text-lime">1</span>We log your grievance and share a reference number.</li>
					<li class="flex gap-3"><span class="font-display text-lime">2</span>The committee reviews it with the vendor or member involved.</li>
					<li class="flex gap-3"><span class="font-display text-lime">3</span>We get back to you with the outcome.</li>
				</ol>
			</div>
			<div class="card p-6">
				<h3 class="text-lg-semibold text-ink-gray-9">Prefer to talk?</h3>
				<a :href="site.phoneHref" class="mt-3 flex items-center gap-2 text-base text-ink-gray-7 hover:text-brand-700">
					<span class="lucide-phone size-4 text-brand-600" aria-hidden="true" />{{ site.phone }}
				</a>
				<a :href="`mailto:${site.email}`" class="mt-2 flex items-center gap-2 text-base text-ink-gray-7 hover:text-brand-700">
					<span class="lucide-mail size-4 text-brand-600" aria-hidden="true" />{{ site.email }}
				</a>
			</div>
		</aside>
	</section>
</template>
