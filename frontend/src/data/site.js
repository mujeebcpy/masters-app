// Static content carried over from the previous mastersassociation.org site.
// Dynamic content (members, team, gallery, events, documents) comes from the backend.

export const asset = (path) => `/assets/masters_association/${path}`

export const site = {
	name: "Masters Association",
	fullName: "Ministry Approved Solar Traders",
	tagline: "Powering the world's clean energy future",
	phone: "+91 81298 38288",
	phoneHref: "tel:+918129838288",
	whatsapp: "https://wa.me/918129838288",
	email: "info@solarmasters.org",
	membershipEmail: "solarmasters@gmail.com",
	address: "Dot Space, Total Tower, Behind Changampuzha Park, Edappally, Kochi, Kerala 682024",
	mapsLink: "https://maps.app.goo.gl/LEEnanMHswSmcRBd6",
	mapsEmbed:
		"https://www.google.com/maps?q=Changampuzha+Park,+Edappally,+Kochi,+Kerala+682024&output=embed",
	expoLink: "https://expokerala.com/",
	brandBook: asset("docs/masters-brand-book.pdf"),
	membershipFee: 1000,
	logo: {
		dark: asset("images/logo/logo-dark.png"),
		white: asset("images/logo/logo-white.png"),
		mark: asset("images/logo/mark.png"),
	},
	socials: [
		{ label: "Facebook", key: "facebook", href: "https://www.facebook.com/Mastersgreenenergyexpo2026/" },
		{ label: "YouTube", key: "youtube", href: "https://www.youtube.com/@Mastersexpo2026" },
		{ label: "Instagram", key: "instagram", href: "https://www.instagram.com/mastersexpo_2026/" },
		{ label: "LinkedIn", key: "linkedin", href: "https://www.linkedin.com/company/110237453/" },
	],
}

export const navigation = [
	{ label: "Home", route: "/" },
	{ label: "About", route: "/about" },
	{ label: "Members", route: "/members" },
	{
		label: "Gallery",
		route: "/gallery",
		children: [
			{ label: "Photo gallery", route: "/photo-gallery", icon: "lucide-image" },
			{ label: "Video gallery", route: "/video-gallery", icon: "lucide-video" },
		],
	},
	{ label: "Events", route: "/events" },
	{ label: "Documents", route: "/documents" },
	{ label: "Grievance", route: "/grievance" },
	{ label: "Contact", route: "/contact" },
]

export const highlights = [
	"A growing member network",
	"MNRE subsidy program",
	"Quality-control association",
	"Supporting new members",
	"Vendorship training",
	"Largest solar association in Kerala",
]

export const reasons = [
	{
		title: "Experience",
		icon: "lucide-award",
		text: "With more than 3 years of experience and in-depth knowledge of solar installation and services, we help new members grow.",
	},
	{
		title: "Expertise",
		icon: "lucide-lightbulb",
		text: "Masters keeps track of the latest changes in the solar industry and shares them with every association member.",
	},
	{
		title: "Track record",
		icon: "lucide-trending-up",
		text: "Our listed members have completed over 10 MW of installations under the MNRE subsidy program, with the support of fellow members.",
	},
	{
		title: "Safety",
		icon: "lucide-hard-hat",
		text: "We run periodic training on safe installation on elevated roofs, with proper walkways and handrails.",
	},
]

export const testimonials = [
	{
		name: "Jayakrishnan V",
		quote: "The biggest value of my membership and participation in Masters is the opportunity to build relationships with my colleagues in the industry. The solar industry is a close-knit community, and Masters gives us the venue to share ideas and celebrate accomplishments.",
	},
	{
		name: "Suryakumar L",
		quote: "In both big and small ways, my membership in Masters has been an integral part of my professional career, giving me numerous opportunities to network and enhance my credibility as a professional. I choose to be a member of Masters as it is the only organization 100 per cent dedicated to advancing our industry.",
	},
	{
		name: "Sooraj R",
		quote: "My main reason for joining Masters is to show dedication to my profession. Beyond engaging with industry professionals, there is a real community feeling that comes from giving back to the solar industry.",
	},
	{
		name: "Mujeeb Rehman",
		quote: "I value membership because of the professional network for keeping up with solar industry people and the work they do. I value the idea that there is a greater good of the whole, as opposed to 300 isolated and disconnected vendors.",
	},
]

export const requiredDocuments = {
	identification: ["PAN card", "Aadhaar card", "Driving licence", "Passport", "Voter ID"],
	registration: ["Valid address proof of the company / organization", "MNRE registration number", "GST certificate"],
}
