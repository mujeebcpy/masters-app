<script setup>
import { Button } from "frappe-ui"
</script>

<template>
	<section class="container-page flex flex-col items-center py-28 text-center">
		<p class="font-display text-display-3xl font-extrabold text-gradient">404</p>
		<h1 class="mt-4 text-display-sm font-bold text-ink-gray-9">Page not found</h1>
		<p class="mt-3 max-w-md text-p-lg text-ink-gray-6">The page you're looking for doesn't exist or has moved.</p>
		<Button class="mt-8" variant="solid" theme="green" size="lg" :route="{ path: '/' }" label="Back to home" />
	</section>
</template>
