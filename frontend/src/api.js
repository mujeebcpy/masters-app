export const method = (path) => `/api/v2/method/${path}`
export const websiteMethod = (name) => method(`masters_association.website.${name}`)
export const memberMethod = (name) => method(`masters_association.member_portal.${name}`)

export function formatDate(value, options = { day: "numeric", month: "short", year: "numeric" }) {
	if (!value) return ""
	return new Date(value).toLocaleDateString("en-IN", options)
}

// Frappe errors arrive as "ValidationError: <message, possibly with HTML>"
export function errorText(error) {
	if (!error) return ""
	const message = (error.message || String(error)).replace(/^[A-Za-z]+Error:\s*/, "")
	const div = document.createElement("div")
	div.innerHTML = message.replace(/<br\s*\/?>/gi, "\n")
	return div.textContent.trim().replace(/\n{2,}/g, "\n")
}
