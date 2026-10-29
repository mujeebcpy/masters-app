import preset, { content } from "frappe-ui/tailwind"

/** @type {import('tailwindcss').Config} */
export default {
	presets: [preset],
	content: [...content, "./index.html", "./src/**/*.{vue,js,ts}"],
	theme: {
		extend: {
			colors: {
				// Sampled from the Masters logo: lime #8FCC49 → green #57B562 → teal #26B68C
				brand: {
					50: "#F2FAEE",
					100: "#E2F4D9",
					200: "#C5E8B3",
					300: "#9FD683",
					400: "#76C159",
					500: "#57B562",
					600: "#3C9447",
					700: "#2F7539",
					800: "#285D31",
					900: "#1F4A28",
					950: "#0D2A17",
				},
				lime: "#8FCC49",
				teal: { brand: "#26B68C" },
				forest: "#0B2619",
			},
			// frappe-ui's type scale tops out at 56px and its 3xl–7xl steps are 20–32px,
			// so marketing headings use this separate display scale.
			fontSize: {
				"display-xs": ["1.5rem", { lineHeight: "1.25", letterSpacing: "-0.01em" }],
				"display-sm": ["1.875rem", { lineHeight: "1.2", letterSpacing: "-0.015em" }],
				"display-md": ["2.5rem", { lineHeight: "1.15", letterSpacing: "-0.02em" }],
				"display-lg": ["3rem", { lineHeight: "1.1", letterSpacing: "-0.02em" }],
				"display-xl": ["3.75rem", { lineHeight: "1.05", letterSpacing: "-0.025em" }],
				"display-2xl": ["4.5rem", { lineHeight: "1.02", letterSpacing: "-0.03em" }],
				"display-3xl": ["6rem", { lineHeight: "1", letterSpacing: "-0.03em" }],
			},
			fontFamily: {
				display: ["Gabarito", "InterVar", "sans-serif"],
			},
		},
	},
}
