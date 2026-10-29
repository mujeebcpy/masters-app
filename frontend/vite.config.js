import path from "path"
import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import frappeui from "frappe-ui/vite"

export default defineConfig({
	plugins: [
		frappeui({
			frontendRoute: "/",
			frappeProxy: {
				// the website lives at the site root, so only backend paths are proxied
				source: "^/(app|login|api|assets|files|private|members-registration)",
			},
			buildConfig: {
				indexHtmlPath: "../masters_association/www/masters.html",
			},
		}),
		vue(),
	],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
})
