import { inject } from "vue"

export const memberSessionKey = Symbol("member-session")

export function useMemberSession() {
	const session = inject(memberSessionKey)
	if (!session) throw new Error("Member session provider is missing")
	return session
}

export function loginUrl(returnTo = "/member/profile") {
	const path = typeof returnTo === "string" && returnTo.startsWith("/") && !returnTo.startsWith("//") && !returnTo.includes("\\")
		? returnTo
		: "/member/profile"
	return `/login?redirect-to=${encodeURIComponent(path)}`
}
