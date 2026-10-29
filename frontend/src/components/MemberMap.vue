<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue"
import L from "leaflet"
import "leaflet/dist/leaflet.css"

const props = defineProps({
	locations: { type: Array, default: () => [] },
})

// Kerala, for when there are no pins to fit the map to
const KERALA_BOUNDS = [
	[8.18, 74.85],
	[12.8, 77.42],
]

const el = ref(null)
let map = null
let markers = null

const pin = L.divIcon({
	className: "member-pin",
	html: '<span class="member-pin__dot"></span>',
	iconSize: [28, 28],
	iconAnchor: [14, 28],
	popupAnchor: [0, -26],
})

function escape(value) {
	const div = document.createElement("div")
	div.textContent = value || ""
	return div.innerHTML
}

function popup(location) {
	const lines = [
		`<p class="text-base-semibold text-ink-gray-9">${escape(location.name)}</p>`,
		location.company && `<p class="mt-0.5 text-sm text-ink-gray-6">${escape(location.company)}</p>`,
		location.district && `<p class="mt-0.5 text-sm text-ink-gray-5">${escape(location.district)}</p>`,
		location.maps_link &&
			`<a class="mt-2 inline-block text-sm-semibold text-brand-700" href="${escape(location.maps_link)}" target="_blank" rel="noopener">Open in Google Maps →</a>`,
	]
	return lines.filter(Boolean).join("")
}

function render() {
	markers.clearLayers()
	for (const location of props.locations) {
		L.marker([location.lat, location.lng], { icon: pin, title: location.name })
			.bindPopup(popup(location))
			.addTo(markers)
	}
	const bounds = props.locations.length ? markers.getBounds() : L.latLngBounds(KERALA_BOUNDS)
	map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 })
}

onMounted(() => {
	map = L.map(el.value, { scrollWheelZoom: false })
	L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
		maxZoom: 19,
		attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
	}).addTo(map)
	markers = L.featureGroup().addTo(map)
	render()
})

watch(() => props.locations, () => map && render())

onBeforeUnmount(() => map?.remove())
</script>

<template>
	<div ref="el" class="relative z-0 h-[26rem] w-full overflow-hidden rounded-7 border border-outline-gray-1 sm:h-[32rem]" />
</template>

<style>
.member-pin__dot {
	position: relative;
	display: block;
	width: 28px;
	height: 28px;
	border-radius: 50% 50% 50% 0;
	transform: rotate(-45deg);
	background: linear-gradient(135deg, #8fcc49, #26b68c);
	border: 3px solid #fff;
	box-shadow: 0 2px 6px rgb(0 0 0 / 0.35);
}
.member-pin__dot::after {
	content: "";
	position: absolute;
	inset: 6px;
	border-radius: 50%;
	background: #0b2619;
}
.leaflet-popup-content {
	margin: 12px 14px;
}
.leaflet-popup-content p {
	margin: 0;
}
</style>
