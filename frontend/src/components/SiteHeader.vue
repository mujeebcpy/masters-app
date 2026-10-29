<script setup>
import { ref, watch } from "vue"
import { useRoute } from "vue-router"
import { Button, Dropdown } from "frappe-ui"
import { navigation, site } from "@/data/site"

const route = useRoute()
const mobileOpen = ref(false)

watch(
	() => route.fullPath,
	() => (mobileOpen.value = false)
)

function isActive(item) {
	if (item.route === "/") return route.path === "/"
	return [item.route, ...(item.children || []).map((c) => c.route)].includes(route.path)
}

function menuOptions(item) {
	return [{ label: "All photos & videos", route: item.route, icon: "lucide-images" }, ...item.children]
}
</script>

<template>
	<header class="sticky top-0 z-40 border-b border-outline-gray-1 bg-surface-base/90 backdrop-blur-md">
		<div class="container-page flex h-16 items-center justify-between gap-4 lg:h-[4.5rem]">
			<router-link to="/" class="shrink-0" aria-label="Masters Association home">
				<img :src="site.logo.dark" alt="Masters - Ministry Approved Solar Traders" class="h-9 w-auto lg:h-10" />
			</router-link>

			<nav class="hidden items-center gap-0.5 lg:flex" aria-label="Main">
				<template v-for="item in navigation" :key="item.route">
					<Dropdown v-if="item.children" :options="menuOptions(item)" align="center">
						<button
							class="inline-flex items-center gap-1 rounded-4 px-3 py-2 text-base-medium transition-colors hover:bg-surface-gray-2"
							:class="isActive(item) ? 'text-brand-700' : 'text-ink-gray-7'"
						>
							{{ item.label }}
							<span class="lucide-chevron-down size-3.5" aria-hidden="true" />
						</button>
					</Dropdown>
					<router-link
						v-else
						:to="item.route"
						class="rounded-4 px-3 py-2 text-base-medium transition-colors hover:bg-surface-gray-2"
						:class="isActive(item) ? 'text-brand-700' : 'text-ink-gray-7'"
					>
						{{ item.label }}
					</router-link>
				</template>
			</nav>

			<div class="flex items-center gap-2">
				<Button
					class="hidden sm:inline-flex"
					variant="solid"
					theme="green"
					size="md"
					:route="{ path: '/become-members' }"
					label="Become a member"
					icon-right="lucide-arrow-right"
				/>
				<Button
					class="lg:hidden"
					size="md"
					variant="ghost"
					:icon="mobileOpen ? 'lucide-x' : 'lucide-menu'"
					:aria-label="mobileOpen ? 'Close menu' : 'Open menu'"
					:aria-expanded="mobileOpen"
					@click="mobileOpen = !mobileOpen"
				/>
			</div>
		</div>

		<Transition
			enter-from-class="opacity-0 -translate-y-2"
			leave-to-class="opacity-0 -translate-y-2"
			enter-active-class="transition duration-200"
			leave-active-class="transition duration-150"
		>
			<nav
				v-if="mobileOpen"
				class="max-h-[calc(100vh-4rem)] overflow-y-auto border-t border-outline-gray-1 bg-surface-base lg:hidden"
				aria-label="Mobile"
			>
				<div class="container-page space-y-0.5 py-3">
					<template v-for="item in navigation" :key="item.route">
						<router-link
							:to="item.route"
							class="block rounded-5 px-3 py-2.5 text-lg-medium"
							:class="isActive(item) ? 'bg-brand-50 text-brand-700' : 'text-ink-gray-8'"
						>
							{{ item.label }}
						</router-link>
						<router-link
							v-for="child in item.children"
							:key="child.route"
							:to="child.route"
							class="flex items-center gap-2 rounded-5 py-2 pl-7 pr-3 text-base text-ink-gray-6"
						>
							<span :class="child.icon" class="size-4" aria-hidden="true" />
							{{ child.label }}
						</router-link>
					</template>
					<div class="pt-3">
						<Button
							class="w-full"
							variant="solid"
							theme="green"
							size="lg"
							:route="{ path: '/become-members' }"
							label="Become a member"
						/>
					</div>
				</div>
			</nav>
		</Transition>
	</header>
</template>
