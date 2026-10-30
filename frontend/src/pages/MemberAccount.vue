<script setup>
import { computed, reactive, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { Alert, Button, FormControl, useCall } from "frappe-ui"
import { errorText, memberMethod, method } from "@/api"
import { loginUrl, useMemberSession } from "@/member/session"

const route = useRoute()
const router = useRouter()
const { session } = useMemberSession()
const email = reactive({ new_email: "", current_password: "" })
const password = reactive({ current: "", next: "", confirmation: "" })
const emailMessage = ref("")
const emailError = ref("")
const passwordError = ref("")
const confirmationResult = ref(null)
const confirmationError = ref("")
const token = computed(() => typeof route.query.email_token === "string" ? route.query.email_token : "")
const emailRequest = useCall({ url: memberMethod("request_email_change"), method: "POST", immediate: false })
const confirm = useCall({ url: memberMethod("confirm_email_change"), method: "POST", immediate: false })
const passwordRequest = useCall({ url: method("frappe.core.doctype.user.user.update_password"), method: "POST", immediate: false })
const busy = computed(() => emailRequest.loading || confirm.loading || passwordRequest.loading)

async function requestEmail() {
	emailMessage.value = ""
	emailError.value = ""
	if (!email.new_email.trim() || !email.current_password) {
		emailError.value = "Enter your new email and current password."
		return
	}
	try {
		const response = await emailRequest.submit({ new_email: email.new_email.trim(), current_password: email.current_password })
		emailMessage.value = response.message
	} catch (error) {
		emailError.value = errorText(error)
	} finally {
		email.current_password = ""
		emailRequest.reset()
	}
}

async function confirmEmail() {
	confirmationError.value = ""
	try {
		confirmationResult.value = await confirm.submit({ token: token.value })
		// Remove the one-use token from the address bar after confirmation.
		await router.replace({ path: "/member/account" })
	} catch (error) {
		confirmationError.value = errorText(error)
	} finally {
		confirm.reset()
	}
}

async function changePassword() {
	passwordError.value = ""
	if (!password.current || !password.next) {
		passwordError.value = "Enter your current password and a new password."
		return
	}
	if (password.next !== password.confirmation) {
		passwordError.value = "The new passwords do not match."
		return
	}
	try {
		await passwordRequest.submit({ old_password: password.current, new_password: password.next, logout_all_sessions: 1 })
		// Frappe renews authentication during a password change; refresh boot/CSRF state.
		window.location.assign("/member/account?password_updated=1")
	} catch (error) {
		passwordError.value = errorText(error)
	} finally {
		password.current = ""
		password.next = ""
		password.confirmation = ""
		passwordRequest.reset()
	}
}

function signInAgain() {
	window.location.assign(loginUrl())
}

function forgotPassword() {
	window.location.assign("/login#forgot")
}
</script>

<template>
	<div v-if="confirmationResult" class="card space-y-5 p-6 sm:p-8">
		<Alert theme="green" title="Email updated" :description="confirmationResult.message" />
		<p class="text-p-base text-ink-gray-7">Your login email is now {{ confirmationResult.email }}.</p>
		<Button label="Log in with your new email" variant="solid" theme="green" @click="signInAgain" />
	</div>
	<div v-else class="space-y-6">
		<div v-if="token" class="card space-y-5 p-6 sm:p-8">
			<h2 class="text-lg-semibold text-ink-gray-9">Confirm your new email</h2>
			<p class="text-p-base text-ink-gray-7">Confirm to change your member email and login address. You'll then sign in again using your new address.</p>
			<Alert v-if="confirmationError" theme="red" title="Couldn't verify this email" :description="confirmationError" />
			<Button label="Confirm email change" variant="solid" theme="green" :loading="confirm.loading" :disabled="busy" @click="confirmEmail" />
		</div>
		<Alert v-if="route.query.password_updated === '1'" theme="green" title="Password updated" description="Your password has been changed and other sessions have been signed out." />
		<form class="card space-y-5 p-6 sm:p-8" @submit.prevent="requestEmail">
			<div>
				<h2 class="text-lg-semibold text-ink-gray-9">Change email</h2>
				<p class="mt-2 text-p-base text-ink-gray-6">Your login and member profile use the same email. Your current address stays active until you verify the new one.</p>
			</div>
			<FormControl :model-value="session.data?.user" label="Current email" type="email" variant="outline" disabled />
			<div class="grid gap-5 sm:grid-cols-2">
				<FormControl v-model="email.new_email" label="New email" type="email" autocomplete="email" variant="outline" required :disabled="busy" />
				<FormControl v-model="email.current_password" label="Current password" type="password" autocomplete="current-password" variant="outline" required :disabled="busy" />
			</div>
			<Alert v-if="emailMessage" theme="green" title="Check your new email" :description="emailMessage" />
			<Alert v-if="emailError" theme="red" title="Couldn't request the change" :description="emailError" />
			<Button type="submit" label="Send verification link" :loading="emailRequest.loading" :disabled="busy" />
		</form>
		<form class="card space-y-5 p-6 sm:p-8" @submit.prevent="changePassword">
			<div>
				<h2 class="text-lg-semibold text-ink-gray-9">Change password</h2>
				<p class="mt-2 text-p-base text-ink-gray-6">Choose a strong password. Other signed-in sessions will be logged out.</p>
			</div>
			<FormControl v-model="password.current" label="Current password" type="password" autocomplete="current-password" variant="outline" required :disabled="busy" />
			<div class="grid gap-5 sm:grid-cols-2">
				<FormControl v-model="password.next" label="New password" type="password" autocomplete="new-password" variant="outline" required :disabled="busy" />
				<FormControl v-model="password.confirmation" label="Confirm new password" type="password" autocomplete="new-password" variant="outline" required :disabled="busy" />
			</div>
			<Alert v-if="passwordError" theme="red" title="Couldn't change the password" :description="passwordError" />
			<Button type="submit" label="Update password" variant="solid" theme="green" :loading="passwordRequest.loading" :disabled="busy" />
			<Button label="Forgot your password?" variant="ghost" @click="forgotPassword" />
		</form>
	</div>
</template>
