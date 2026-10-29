<script setup>
import { computed, reactive, ref } from "vue"
import { Alert, Button, ErrorMessage, FormControl, FormLabel, Spinner, useCall } from "frappe-ui"
import { asset, requiredDocuments, site } from "@/data/site"
import { errorText, method, websiteMethod } from "@/api"
import PageHero from "@/components/PageHero.vue"

// The form is submitted through the existing "members-registration" Web Form (via
// register_member), so its field rules, mandatory checks and Association Member hooks all apply.
const WEB_FORM = "members-registration"
const GSTIN_PATTERN = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/

const membershipLabels = {
	"Normal Member": "Ordinary member",
	"Lifetime Member": "Lifetime member",
	"Not A Member": "Not a member yet",
}

const options = useCall({ url: websiteMethod("get_registration_options"), cacheKey: "registration-options" })
const membershipOptions = computed(() =>
	(options.data?.membership_statuses || []).map((value) => ({ value, label: membershipLabels[value] || value }))
)
const districtOptions = computed(() => options.data?.districts || [])

const form = reactive({
	name1: "",
	membership_status: "Normal Member",
	email: "",
	mobile: "",
	designation: "",
	gst: "",
	district: null,
	google_maps_link: "",
})
const photo = ref(null) // { name, dataUrl }
const errors = ref({})
const submitted = ref(null)

const gstDetails = useCall({
	url: method("masters_association.api.fetch_gst_details"),
	method: "POST",
	immediate: false,
})

function onGstinInput(value) {
	const gstin = (value || "").trim().toUpperCase()
	form.gst = gstin
	gstDetails.reset()
	// a failed lookup is shown inline from gstDetails.error; the member can still submit
	if (GSTIN_PATTERN.test(gstin)) gstDetails.submit({ gstin }).catch(() => {})
}

async function onPhotoChange(event) {
	const file = event.target.files?.[0]
	if (!file) return
	if (!file.type.startsWith("image/")) {
		errors.value = { ...errors.value, photo: "Please choose an image file." }
		return
	}
	errors.value = { ...errors.value, photo: null }
	// resized to JPEG, so name it accordingly
	const name = file.name.replace(/\.[^.]+$/, "").replace(/[^\w-]+/g, "-") + ".jpg"
	photo.value = { name, dataUrl: await resizeImage(file, 800) }
}

// Keep uploads small: members' photos are shown at most ~400px wide on the site.
function resizeImage(file, maxSize) {
	return new Promise((resolve, reject) => {
		const img = new Image()
		img.onload = () => {
			const scale = Math.min(1, maxSize / Math.max(img.width, img.height))
			const canvas = document.createElement("canvas")
			canvas.width = Math.round(img.width * scale)
			canvas.height = Math.round(img.height * scale)
			canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height)
			URL.revokeObjectURL(img.src)
			resolve(canvas.toDataURL("image/jpeg", 0.85))
		}
		img.onerror = reject
		img.src = URL.createObjectURL(file)
	})
}

function fullMobile() {
	const value = form.mobile.trim()
	if (value.startsWith("+")) return value
	return `+91-${value.replace(/\D/g, "")}`
}

function validate() {
	const e = {}
	if (!form.name1.trim()) e.name1 = "Please enter the contact person's name."
	if (!form.membership_status) e.membership_status = "Please choose a membership type."
	if (form.email && !/^\S+@\S+\.\S+$/.test(form.email)) e.email = "Please enter a valid email address."
	if (!/^\+?[\d\s-]{10,15}$/.test(form.mobile.trim())) e.mobile = "Please enter a valid 10-digit mobile number."
	if (!GSTIN_PATTERN.test(form.gst))
		e.gst = "Enter a 15-character GSTIN: two state-code digits, your 10-character PAN, an entity code, Z and a check character."
	if (!form.district) e.district = "Please choose your district."
	errors.value = e
	return !Object.keys(e).length
}

const submission = useCall({
	url: websiteMethod("register_member"),
	method: "POST",
	immediate: false,
})

async function submit() {
	if (!validate()) return
	const gst = gstDetails.data || {}
	const data = {
		doctype: "Association Member",
		web_form_name: WEB_FORM,
		name1: form.name1.trim(),
		membership_status: form.membership_status,
		email: form.email.trim(),
		mobile_no_whatsapp: fullMobile(),
		designation: form.designation.trim(),
		gst: form.gst,
		gst_company_name: gst.gst_company_name || "",
		gst_address: gst.gst_address || "",
		gst_pincode: gst.gst_pincode || "",
		gst_state: gst.gst_state || "",
		gst_status: gst.gst_status || "",
		district: form.district,
		google_maps_link: form.google_maps_link.trim(),
	}
	try {
		await submission.submit({
			data: JSON.stringify(data),
			photo: photo.value?.dataUrl,
			photo_name: photo.value?.name,
		})
	} catch {
		return // shown in the Alert above the submit button
	}
	submitted.value = submission.data
	window.scrollTo({ top: 0, behavior: "smooth" })
}
</script>

<template>
	<PageHero
		title="Become a member"
		eyebrow="Membership"
		subtitle="Join Kerala's largest association of MNRE-registered solar vendors. Registration is open for MNRE members only."
		:image="asset('images/photos/members-meeting.jpg')"
	/>

	<section class="container-page grid gap-10 py-16 sm:py-20 lg:grid-cols-[0.85fr_1.15fr] lg:gap-14">
		<!-- What you need -->
		<aside class="space-y-6 lg:sticky lg:top-28 lg:self-start">
			<div>
				<p class="eyebrow">Before you start</p>
				<h2 class="mt-3 text-display-sm font-bold text-ink-gray-9">Required documents</h2>
				<p class="mt-3 text-p-base text-ink-gray-6">
					Keep these ready. Our team may ask for copies while reviewing your application. You can also
					email them to
					<a :href="`mailto:${site.membershipEmail}`" class="text-ink-blue-link hover:underline">
						{{ site.membershipEmail }}
					</a>.
				</p>
			</div>

			<div class="card divide-y divide-outline-gray-1">
				<div class="p-5">
					<div class="flex items-center gap-2">
						<span class="lucide-id-card size-5 text-brand-600" aria-hidden="true" />
						<h3 class="text-lg-semibold text-ink-gray-9">Identification</h3>
					</div>
					<p class="mt-1 text-sm text-ink-gray-5">Any one of the following</p>
					<ul class="mt-3 flex flex-wrap gap-2">
						<li
							v-for="doc in requiredDocuments.identification"
							:key="doc"
							class="rounded-full bg-surface-gray-2 px-3 py-1 text-sm-medium text-ink-gray-7"
						>
							{{ doc }}
						</li>
					</ul>
				</div>
				<div class="p-5">
					<div class="flex items-center gap-2">
						<span class="lucide-file-badge size-5 text-brand-600" aria-hidden="true" />
						<h3 class="text-lg-semibold text-ink-gray-9">Registration</h3>
					</div>
					<ul class="mt-3 space-y-2">
						<li v-for="doc in requiredDocuments.registration" :key="doc" class="flex gap-2 text-base text-ink-gray-7">
							<span class="lucide-circle-check mt-0.5 size-4 shrink-0 text-brand-500" aria-hidden="true" />
							{{ doc }}
						</li>
					</ul>
				</div>
			</div>

			<div class="flex gap-5 overflow-hidden rounded-7 bg-forest p-5 text-white">
				<img
					:src="asset('images/photos/payment-qr.jpg')"
					alt="UPI QR code for membership payment"
					class="w-28 shrink-0 rounded-4 bg-white"
				/>
				<div>
					<p class="text-sm-semibold uppercase tracking-wider text-lime">Membership fee</p>
					<p class="mt-1 font-display text-display-sm font-bold">₹{{ site.membershipFee.toLocaleString("en-IN") }}</p>
					<p class="mt-2 text-p-sm text-white/70">
						Scan with any UPI app to pay. Keep the transaction reference; our team will verify the payment
						against your application.
					</p>
				</div>
			</div>
		</aside>

		<!-- Form -->
		<div>
			<div v-if="submitted" class="card p-8 text-center sm:p-12">
				<div class="mx-auto grid size-16 place-items-center rounded-full bg-brand-100 text-brand-600">
					<span class="lucide-circle-check size-8" aria-hidden="true" />
				</div>
				<h2 class="mt-6 text-display-sm font-bold text-ink-gray-9">Application received</h2>
				<p class="mx-auto mt-3 max-w-md text-p-lg text-ink-gray-6">
					Thank you, {{ form.name1 }}. Our membership team will review your details and contact you on
					WhatsApp at {{ fullMobile() }}.
				</p>
				<p v-if="submitted.name" class="mt-4 text-sm text-ink-gray-5">Reference: {{ submitted.name }}</p>
				<Button class="mt-8" size="lg" variant="outline" :route="{ path: '/' }" label="Back to home" />
			</div>

			<form v-else class="card p-6 sm:p-8" novalidate @submit.prevent="submit">
				<h2 class="text-display-xs font-bold text-ink-gray-9">Membership registration</h2>
				<p class="mt-1 text-p-base text-ink-gray-5">Fields marked * are required.</p>

				<fieldset class="mt-8 space-y-5">
					<legend class="mb-4 text-sm-semibold uppercase tracking-wider text-brand-700">Contact details</legend>
					<FormControl
						v-model="form.name1"
						label="Contact person name"
						size="lg"
						variant="outline"
						required
						:error="errors.name1"
						autocomplete="name"
					/>
					<div class="grid gap-5 sm:grid-cols-2">
						<FormControl
							v-model="form.membership_status"
							type="select"
							label="Membership type"
							size="lg"
							variant="outline"
							required
							:options="membershipOptions"
							:error="errors.membership_status"
						/>
						<FormControl
							v-model="form.designation"
							label="Designation"
							size="lg"
							variant="outline"
							placeholder="e.g. Managing Director"
						/>
					</div>
					<div class="grid gap-5 sm:grid-cols-2">
						<FormControl
							v-model="form.mobile"
							type="tel"
							label="WhatsApp mobile number"
							description="We'll add this number to the Masters family WhatsApp group."
							size="lg"
							variant="outline"
							required
							placeholder="98765 43210"
							:error="errors.mobile"
							autocomplete="tel-national"
						>
							<template #prefix><span class="text-base text-ink-gray-5">+91</span></template>
						</FormControl>
						<FormControl
							v-model="form.email"
							type="email"
							label="Email"
							size="lg"
							variant="outline"
							:error="errors.email"
							autocomplete="email"
						/>
					</div>
					<div>
						<FormLabel label="Photo" />
						<label
							class="mt-1.5 flex cursor-pointer items-center gap-4 rounded-5 border border-dashed border-outline-gray-3 p-4 transition hover:border-brand-400 hover:bg-brand-50/50"
						>
							<img v-if="photo" :src="photo.dataUrl" alt="" class="size-14 rounded-full object-cover" />
							<span v-else class="grid size-14 place-items-center rounded-full bg-surface-gray-2 text-ink-gray-5">
								<span class="lucide-user-round size-6" aria-hidden="true" />
							</span>
							<span class="flex-1">
								<span class="block text-base-medium text-ink-gray-8">
									{{ photo ? photo.name : "Upload a photo" }}
								</span>
								<span class="block text-sm text-ink-gray-5">
									Shown on the members page once approved. JPG or PNG.
								</span>
							</span>
							<span class="lucide-upload size-5 text-ink-gray-5" aria-hidden="true" />
							<input type="file" accept="image/*" class="sr-only" @change="onPhotoChange" />
						</label>
						<ErrorMessage v-if="errors.photo" class="mt-1.5" :message="errors.photo" />
					</div>
				</fieldset>

				<fieldset class="mt-10 space-y-5">
					<legend class="mb-4 text-sm-semibold uppercase tracking-wider text-brand-700">Business details</legend>
					<FormControl
						:model-value="form.gst"
						label="GSTIN"
						size="lg"
						variant="outline"
						required
						placeholder="32ABCDE1234F1Z5"
						description="Your registered business details are fetched automatically."
						:error="errors.gst"
						maxlength="15"
						@update:model-value="onGstinInput"
					/>
					<div
						v-if="gstDetails.loading || gstDetails.data || gstDetails.error"
						class="rounded-5 border p-4"
						:class="gstDetails.error ? 'border-outline-amber-3 bg-surface-amber-1' : 'border-brand-200 bg-brand-50/60'"
					>
						<div v-if="gstDetails.loading" class="flex items-center gap-2 text-base text-ink-gray-6">
							<Spinner class="size-4" /> Looking up GSTIN…
						</div>
						<p v-else-if="gstDetails.error" class="text-p-sm text-ink-amber-7">
							{{ errorText(gstDetails.error) }}
						</p>
						<dl v-else class="grid gap-3 text-sm sm:grid-cols-2">
							<div class="sm:col-span-2">
								<dt class="text-ink-gray-5">Registered name</dt>
								<dd class="mt-0.5 text-base-semibold text-ink-gray-9">{{ gstDetails.data.gst_company_name }}</dd>
							</div>
							<div class="sm:col-span-2">
								<dt class="text-ink-gray-5">Address</dt>
								<dd class="mt-0.5 text-ink-gray-8">
									{{ [gstDetails.data.gst_address, gstDetails.data.gst_state, gstDetails.data.gst_pincode].filter(Boolean).join(", ") }}
								</dd>
							</div>
							<div>
								<dt class="text-ink-gray-5">Status</dt>
								<dd class="mt-0.5 text-ink-gray-8">{{ gstDetails.data.gst_status }}</dd>
							</div>
						</dl>
					</div>
					<div class="grid gap-5 sm:grid-cols-2">
						<FormControl
							v-model="form.district"
							type="select"
							label="District"
							size="lg"
							variant="outline"
							required
							placeholder="Select district"
							:options="districtOptions"
							:error="errors.district"
						/>
						<FormControl
							v-model="form.google_maps_link"
							type="url"
							label="Google Maps link"
							size="lg"
							variant="outline"
							placeholder="https://maps.app.goo.gl/…"
						/>
					</div>
				</fieldset>

				<Alert
					v-if="submission.error"
					class="mt-8"
					theme="red"
					title="We couldn't submit your application"
					:description="errorText(submission.error)"
				/>

				<div class="mt-8 flex flex-col-reverse items-stretch gap-4 border-t border-outline-gray-1 pt-6 sm:flex-row sm:items-center sm:justify-between">
					<p class="text-p-sm text-ink-gray-5">
						By submitting, you confirm that you are an MNRE-registered vendor.
					</p>
					<Button
						type="submit"
						variant="solid"
						theme="green"
						size="lg"
						label="Submit application"
						icon-right="lucide-send"
						:loading="submission.loading"
					/>
				</div>
			</form>
		</div>
	</section>
</template>
