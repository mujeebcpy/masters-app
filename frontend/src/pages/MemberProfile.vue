<script setup>
import { computed, reactive, ref } from "vue"
import { Alert, Avatar, Button, Checkbox, FormControl, Skeleton, dialog, useCall } from "frappe-ui"
import { errorText, memberMethod, websiteMethod } from "@/api"
import { useMemberSession } from "@/member/session"

const { session } = useMemberSession()
const snapshot = ref(null)
const draft = reactive({})
const errors = ref({})
const notice = ref("")
const photoError = ref("")
const serverError = ref("")
const readingPhoto = ref(false)
const photoInput = ref(null)
const stats = [
	{ field: "total_mnre_projects_done_till_date", label: "MNRE projects completed" },
	{ field: "total_capacity_done_till_this_date", label: "Total installed capacity" },
	{ field: "total_number_of_hybrid", label: "Hybrid projects completed" },
	{ field: "total_storage_capacity_of_hybrid", label: "Total hybrid storage capacity" },
]
const fields = [
	"name1", "designation", "mobile_no_whatsapp", "district", "google_maps_link",
	"show_on_website", "show_contact_on_website", ...stats.map((stat) => stat.field),
]

function acceptProfile(data, resetDraft = true) {
	if (!data) return
	snapshot.value = data
	if (resetDraft) {
		for (const field of fields) {
			draft[field] = field.startsWith("show_") ? Boolean(data[field]) : (data[field] ?? "")
		}
	}
}

const profile = useCall({ url: memberMethod("get_my_profile"), onSuccess: (data) => acceptProfile(data) })
const options = useCall({ url: websiteMethod("get_registration_options") })
const update = useCall({ url: memberMethod("update_my_profile"), method: "POST", immediate: false })
const upload = useCall({ url: memberMethod("upload_my_photo"), method: "POST", immediate: false })
const remove = useCall({ url: memberMethod("remove_my_photo"), method: "POST", immediate: false })
const busy = computed(() => update.loading || upload.loading || remove.loading || readingPhoto.value)
const dirty = computed(() => snapshot.value && fields.some((field) => {
	if (field.startsWith("show_")) return Boolean(draft[field]) !== Boolean(snapshot.value[field])
	return String(draft[field] ?? "") !== String(snapshot.value[field] ?? "")
}))

async function save() {
	const validation = {}
	if (!draft.name1?.trim()) validation.name1 = "Enter your name."
	if (!draft.mobile_no_whatsapp?.trim()) validation.mobile_no_whatsapp = "Enter your phone number."
	if (!draft.district) validation.district = "Choose your district."
	for (const stat of stats) {
		if (draft[stat.field] !== "" && !/^\d+$/.test(String(draft[stat.field]))) {
			validation[stat.field] = "Enter a nonnegative whole number."
		}
	}
	errors.value = validation
	if (Object.keys(validation).length) return
	notice.value = ""
	serverError.value = ""
	try {
		const data = Object.fromEntries(fields.map((field) => [field, draft[field]]))
		acceptProfile(await update.submit({ data, modified: snapshot.value.modified }))
		notice.value = "Your profile has been saved."
		session.reload()
	} catch (error) {
		serverError.value = errorText(error)
		// Keep the draft so a failed save never discards the member's work.
	}
}

function reload() {
	const refresh = async () => {
		notice.value = ""
		errors.value = {}
		serverError.value = ""
		photoError.value = ""
		await profile.reload()
	}
	if (dirty.value) {
		dialog.confirm({ title: "Reload profile?", message: "This will replace your unsaved changes with the latest saved profile.", confirmLabel: "Reload", onConfirm: refresh })
	} else {
		refresh()
	}
}

function readPhoto(file) {
	return new Promise((resolve, reject) => {
		const reader = new FileReader()
		reader.onload = () => resolve(reader.result)
		reader.onerror = () => reject(new Error("Couldn't read this photo. Please choose it again."))
		reader.readAsDataURL(file)
	})
}

async function choosePhoto(event) {
	const file = event.target.files?.[0]
	event.target.value = ""
	if (!file) return
	photoError.value = ""
	serverError.value = ""
	notice.value = ""
	if (!["image/jpeg", "image/png"].includes(file.type) || file.size > 5 * 1024 * 1024) {
		photoError.value = "Choose a JPG or PNG photo smaller than 5 MB."
		return
	}
	readingPhoto.value = true
	try {
		const photo = await readPhoto(file)
		// Preserve unsaved text edits while advancing the saved modification timestamp.
		acceptProfile(await upload.submit({ photo, photo_name: file.name, modified: snapshot.value.modified }), false)
		notice.value = "Your profile photo has been updated."
		session.reload()
	} catch (error) {
		photoError.value = errorText(error)
	} finally {
		readingPhoto.value = false
		upload.reset()
	}
}

function removePhoto() {
	photoError.value = ""
	serverError.value = ""
	dialog.confirm({
		title: "Remove profile photo?", message: "Your member photo and account avatar will be cleared.", confirmLabel: "Remove photo",
		onConfirm: async () => {
			try {
				acceptProfile(await remove.submit({ modified: snapshot.value.modified }), false)
				notice.value = "Your profile photo has been removed."
				session.reload()
			} catch (error) {
				serverError.value = errorText(error)
				throw error
			}
		},
	})
}
</script>

<template>
	<div v-if="profile.loading && !snapshot" class="space-y-4" role="status" aria-label="Loading profile">
		<Skeleton class="h-32 w-full rounded-6" />
		<Skeleton class="h-64 w-full rounded-6" />
	</div>
	<div v-else-if="!snapshot" class="space-y-4">
		<Alert theme="red" title="Couldn't load your profile" :description="errorText(profile.error)" />
		<Button label="Try again" :loading="profile.loading" @click="profile.reload()" />
	</div>
	<form v-else class="space-y-6" @submit.prevent="save">
		<Alert v-if="notice" theme="green" title="Saved" :description="notice" dismissible @dismiss="notice = ''" />
		<div v-if="serverError || photoError || profile.error" class="space-y-3">
			<Alert theme="red" title="Couldn't complete the update" :description="photoError || errorText(serverError || profile.error)" />
			<Button label="Reload latest profile" icon="lucide-refresh-cw" :loading="profile.loading" :disabled="busy" @click="reload" />
		</div>
		<div class="card p-6 sm:p-8">
			<div class="flex flex-wrap items-center gap-5">
				<Avatar :label="draft.name1" :image="snapshot.photo" size="3xl" />
				<div class="min-w-0 flex-1">
					<h2 class="text-lg-semibold text-ink-gray-9">Profile photo</h2>
					<p class="mt-1 text-p-sm text-ink-gray-6">Your portrait is a public image and may appear in the member directory. JPG or PNG, up to 5 MB.</p>
					<div class="mt-3 flex flex-wrap gap-2">
						<Button label="Choose photo" icon="lucide-image-plus" :loading="upload.loading || readingPhoto" :disabled="busy" @click="photoInput?.click()" />
						<Button v-if="snapshot.photo" label="Remove photo" variant="ghost" :loading="remove.loading" :disabled="busy" @click="removePhoto" />
					</div>
					<!-- The native picker feeds the authorized member upload endpoint. -->
					<input ref="photoInput" type="file" accept="image/jpeg,image/png" class="hidden" aria-label="Choose profile photo" @change="choosePhoto" />
				</div>
			</div>
		</div>
		<div class="card space-y-6 p-6 sm:p-8">
			<div>
				<h2 class="text-lg-semibold text-ink-gray-9">Your details</h2>
				<p class="mt-1 text-p-sm text-ink-gray-6">Changes to public fields appear in the member directory when your profile is listed.</p>
			</div>
			<div class="grid gap-5 sm:grid-cols-2">
				<FormControl v-model="draft.name1" label="Name" variant="outline" size="md" required :disabled="busy" :error="errors.name1" />
				<FormControl v-model="draft.designation" label="Designation" variant="outline" size="md" :disabled="busy" />
				<FormControl v-model="draft.mobile_no_whatsapp" label="Mobile / WhatsApp" type="tel" variant="outline" size="md" required :disabled="busy" :error="errors.mobile_no_whatsapp" />
				<FormControl v-model="draft.district" label="District" type="select" :options="options.data?.districts || []" variant="outline" size="md" required :disabled="busy" :error="errors.district" />
				<FormControl :model-value="snapshot.email" label="Email" type="email" variant="outline" size="md" disabled description="Change your login email in Account settings." />
				<FormControl :model-value="snapshot.membership_status" label="Membership" variant="outline" size="md" disabled />
			</div>
			<FormControl v-model="draft.google_maps_link" label="Google Maps link" type="url" variant="outline" size="md" :disabled="busy" description="Open your business in Google Maps, choose Share, then copy the link." />
			<Alert v-if="options.error" theme="red" title="Couldn't load district options" :description="errorText(options.error)" :primary-action="{ label: 'Retry', onClick: () => options.reload() }" />
		</div>
		<div class="card space-y-5 p-6 sm:p-8">
			<div>
				<h2 class="text-lg-semibold text-ink-gray-9">Project statistics</h2>
				<p class="mt-1 text-p-sm text-ink-gray-6">Enter whole numbers using the same capacity units as your membership record.</p>
			</div>
			<div class="grid gap-5 sm:grid-cols-2">
				<FormControl v-for="stat in stats" :key="stat.field" v-model="draft[stat.field]" :label="stat.label" type="number" min="0" step="1" variant="outline" size="md" :disabled="busy" :error="errors[stat.field]" />
			</div>
		</div>
		<div class="card space-y-5 p-6 sm:p-8">
			<h2 class="text-lg-semibold text-ink-gray-9">Directory visibility</h2>
			<Checkbox v-model="draft.show_on_website" label="Show my profile in the public member directory" :disabled="busy" />
			<Checkbox v-model="draft.show_contact_on_website" label="Show my email and phone on my public profile" :disabled="busy" />
			<p class="text-p-sm text-ink-gray-6">Hiding your directory listing does not make an uploaded portrait private.</p>
		</div>
		<div class="flex flex-wrap items-center gap-3">
			<Button type="submit" label="Save profile" variant="solid" theme="green" size="md" :loading="update.loading" :disabled="busy || profile.loading" />
			<Button label="Reload profile" variant="ghost" :loading="profile.loading" :disabled="busy" @click="reload" />
		</div>
	</form>
</template>
