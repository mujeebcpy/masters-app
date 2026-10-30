// Missing readings stay unavailable ("—"); they are never shown as zero.
const numberFormat = (digits) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: digits })

export function formatPower(kw) {
	if (kw == null) return "—"
	return Math.abs(kw) >= 1000 ? `${numberFormat(2).format(kw / 1000)} MW` : `${numberFormat(2).format(kw)} kW`
}

export function formatEnergy(kwh) {
	if (kwh == null) return "—"
	return Math.abs(kwh) >= 1000 ? `${numberFormat(2).format(kwh / 1000)} MWh` : `${numberFormat(1).format(kwh)} kWh`
}

export function formatDateTime(value) {
	if (!value) return "—"
	return new Date(String(value).replace(" ", "T")).toLocaleString("en-IN", {
		day: "numeric",
		month: "short",
		hour: "numeric",
		minute: "2-digit",
	})
}

export const ONLINE = ["NORMAL", "System Normal"]

export const severityTheme = { Critical: "red", Warning: "amber", Notice: "gray" }

export function statusTheme(status) {
	return { Connected: "green", Completed: "green", Error: "red", Failed: "red", Queued: "blue", Running: "blue" }[status] || "gray"
}

// Summarize a queueing response such as { Queued: 3, Running: 1, Cached: 0 }.
export function queuedSummary(result) {
	const parts = Object.entries(result || {})
		.filter(([, count]) => count)
		.map(([state, count]) => `${count} ${state.toLowerCase()}`)
	return parts.length ? parts.join(", ") : "Nothing to update"
}
