<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { gsap } from 'gsap';
	import ImageUpload from '$lib/components/ImageUpload.svelte';
	import PresetPicker from '$lib/components/PresetPicker.svelte';
	import SvgViewer from '$lib/components/SvgViewer.svelte';

	let selectedFile = $state<File | null>(null);
	let selectedPreset = $state('A');
	let svgContent = $state<string | null>(null);
	let isProcessing = $state(false);
	let errorMessage = $state<string | null>(null);

	let headerEl: HTMLElement;
	let contentEl: HTMLElement;
	let entranceTl: gsap.core.Timeline | null = null;

	onMount(() => {
		const items = Array.from(contentEl.children);

		if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
			gsap.set([headerEl, ...items], { opacity: 1, y: 0 });
			return;
		}

		entranceTl = gsap.timeline({
			defaults: { ease: 'power3.out' },
			onComplete: () => {
				gsap.set([headerEl, ...items], { clearProps: 'all' });
			},
		});
		entranceTl
			.from(headerEl, { opacity: 0, y: -20, duration: 0.7 })
			.from(items, {
				opacity: 0,
				y: 24,
				stagger: 0.08,
				duration: 0.5,
			}, '-=0.3');
	});

	onDestroy(() => {
		entranceTl?.kill();
	});

	async function generate() {
		if (!selectedFile) return;

		isProcessing = true;
		errorMessage = null;
		svgContent = null;

		const formData = new FormData();
		formData.append('image', selectedFile);
		formData.append('preset', selectedPreset);

		try {
			const res = await fetch('/api/process', {
				method: 'POST',
				body: formData,
			});
			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.detail || 'Processing failed');
			}
			svgContent = await res.text();
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Something went wrong';
		} finally {
			isProcessing = false;
		}
	}
</script>

<div class="page">
	<header bind:this={headerEl}>
		<h1>Fast Marching <span class="thin">Contours</span></h1>
		<p class="subtitle">Turn photos into contour line art</p>
	</header>

	<div class="content" bind:this={contentEl}>
		<section class="card">
			<span class="label">Image</span>
			<ImageUpload bind:file={selectedFile} />
		</section>

		<section class="card">
			<span class="label">Preset</span>
			<PresetPicker bind:selected={selectedPreset} />
		</section>

		<button class="generate" onclick={generate} disabled={!selectedFile || isProcessing}>
			{#if isProcessing}
				<span class="spinner-inline"></span>
				Processing...
			{:else}
				Generate
			{/if}
		</button>

		{#if errorMessage}
			<p class="error">{errorMessage}</p>
		{/if}

		{#if svgContent}
			<section>
				<SvgViewer {svgContent} preset={selectedPreset} />
			</section>
		{/if}
	</div>
</div>

<style>
	.page {
		max-width: 760px;
		margin: 0 auto;
		padding: 3rem 1.5rem 4rem;
	}

	header {
		margin-bottom: 2.5rem;
	}

	h1 {
		font-size: 2rem;
		font-weight: 700;
		letter-spacing: -0.03em;
		color: var(--text-primary);
	}

	h1 .thin {
		font-weight: 300;
		color: var(--text-secondary);
	}

	.subtitle {
		font-size: 0.9rem;
		color: var(--text-muted);
		margin-top: 0.25rem;
		letter-spacing: 0.02em;
		text-transform: uppercase;
		font-weight: 500;
	}

	.content {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.card {
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: 1.25rem;
	}

	.label {
		display: block;
		font-size: 0.75rem;
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-muted);
		margin-bottom: 0.75rem;
	}

	.generate {
		width: 100%;
		padding: 0.85rem;
		background: var(--text-primary);
		color: var(--bg-primary);
		border: none;
		border-radius: var(--radius-md);
		font-family: var(--font-sans);
		font-size: 0.9rem;
		font-weight: 600;
		letter-spacing: 0.01em;
		cursor: pointer;
		transition: opacity 0.15s, transform 0.15s;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
	}

	.generate:hover:not(:disabled) {
		opacity: 0.85;
		transform: translateY(-1px);
	}

	.generate:active:not(:disabled) {
		transform: translateY(0);
	}

	.generate:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}

	.spinner-inline {
		width: 1rem;
		height: 1rem;
		border: 2px solid transparent;
		border-top-color: var(--bg-primary);
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}

	.error {
		color: var(--error);
		font-size: 0.85rem;
		padding: 0.75rem 1rem;
		background: rgba(238, 85, 85, 0.08);
		border: 1px solid rgba(238, 85, 85, 0.2);
		border-radius: var(--radius-md);
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
