import { createRouter, createWebHistory } from "vue-router"

const routes = [
	{ path: "/", name: "Home", component: () => import("./pages/Home.vue") },
	{ path: "/about", name: "About", component: () => import("./pages/About.vue"), meta: { title: "About us" } },
	{
		path: "/become-members",
		name: "BecomeMember",
		component: () => import("./pages/BecomeMember.vue"),
		meta: { title: "Become a member" },
	},
	{ path: "/members", name: "Members", component: () => import("./pages/Members.vue"), meta: { title: "Members" } },
	{
		path: "/gallery",
		name: "Gallery",
		component: () => import("./pages/Gallery.vue"),
		meta: { title: "Gallery" },
	},
	{
		path: "/photo-gallery",
		name: "PhotoGallery",
		component: () => import("./pages/Gallery.vue"),
		props: { initialTab: "Photo" },
		meta: { title: "Photo gallery" },
	},
	{
		path: "/video-gallery",
		name: "VideoGallery",
		component: () => import("./pages/Gallery.vue"),
		props: { initialTab: "Video" },
		meta: { title: "Video gallery" },
	},
	{ path: "/events", name: "Events", component: () => import("./pages/Events.vue"), meta: { title: "Events" } },
	{
		path: "/documents",
		name: "Documents",
		component: () => import("./pages/Documents.vue"),
		meta: { title: "Documents" },
	},
	{
		path: "/grievance",
		name: "Grievance",
		component: () => import("./pages/Grievance.vue"),
		meta: { title: "Grievance" },
	},
	{ path: "/contact", name: "Contact", component: () => import("./pages/Contact.vue"), meta: { title: "Contact" } },
	{
		path: "/:pathMatch(.*)*",
		name: "NotFound",
		component: () => import("./pages/NotFound.vue"),
		meta: { title: "Page not found" },
	},
]

export const router = createRouter({
	history: createWebHistory(),
	routes,
	scrollBehavior(to, from, savedPosition) {
		if (savedPosition) return savedPosition
		if (to.hash) return { el: to.hash, top: 96 }
		return { top: 0 }
	},
})

router.afterEach((to) => {
	document.title = to.meta.title ? `${to.meta.title} | Masters Association` : "Masters Association"
})
