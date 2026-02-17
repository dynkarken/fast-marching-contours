<script lang="ts">
	import { gsap } from 'gsap';
	import { onMount, onDestroy } from 'svelte';

	let { svgContent, preset }: { svgContent: string; preset: string } = $props();

	let lensActive = $state(false);
	let showLens = $state(false);
	let lensLeft = $state(0);
	let lensTop = $state(0);
	let innerLeft = $state(0);
	let innerTop = $state(0);
	let containerWidth = $state(0);

	let containerEl: HTMLDivElement;
	let viewerEl: HTMLDivElement;
	let revealTl: gsap.core.Timeline | null = null;

	const LENS_DIAMETER = 200;
	const LENS_RADIUS = LENS_DIAMETER / 2;
	const SCALE = 2;

	onMount(() => {
		if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
			gsap.set(viewerEl, { opacity: 1, y: 0, scale: 1 });
			return;
		}

		const svgContainer = viewerEl.querySelector('.svg-container')!;
		const actions = viewerEl.querySelector('.actions')!;

		revealTl = gsap.timeline({
			defaults: { ease: 'power2.out' },
			onComplete: () => {
				gsap.set([svgContainer, actions], { clearProps: 'all' });
			},
		});
		revealTl
			.from(svgContainer, {
				opacity: 0,
				y: 30,
				scale: 0.97,
				duration: 0.6,
			})
			.from(
				actions,
				{
					opacity: 0,
					y: 12,
					duration: 0.4,
				},
				'-=0.2'
			);
	});

	onDestroy(() => {
		revealTl?.kill();
	});

	function onMouseMove(e: MouseEvent) {
		if (!lensActive) return;
		showLens = true;

		const rect = containerEl.getBoundingClientRect();
		const mouseX = e.clientX - rect.left;
		const mouseY = e.clientY - rect.top;
		containerWidth = rect.width;

		lensLeft = e.clientX - LENS_RADIUS;
		lensTop = e.clientY - LENS_RADIUS;

		innerLeft = -mouseX * SCALE + LENS_RADIUS;
		innerTop = -mouseY * SCALE + LENS_RADIUS;
	}

	function onMouseLeave() {
		showLens = false;
	}

	function download() {
		const blob = new Blob([svgContent], { type: 'image/svg+xml' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `contour_${preset}.svg`;
		a.click();
		URL.revokeObjectURL(url);
	}
</script>

<div class="viewer" bind:this={viewerEl}>
	<div
		class="svg-container"
		bind:this={containerEl}
		onmousemove={onMouseMove}
		onmouseleave={onMouseLeave}
		role="img"
	>
		{@html svgContent}
	</div>

	{#if lensActive && showLens}
		<div
			class="lens"
			style="left: {lensLeft}px; top: {lensTop}px; width: {LENS_DIAMETER}px; height: {LENS_DIAMETER}px;"
		>
			<div
				class="lens-inner"
				style="width: {containerWidth * SCALE}px; transform: translate({innerLeft}px, {innerTop}px);"
			>
				{@html svgContent}
			</div>
		</div>
	{/if}

	<div class="actions">
		<button class="btn" class:active={lensActive} onclick={() => (lensActive = !lensActive)}>
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<circle cx="11" cy="11" r="8"/>
				<line x1="21" y1="21" x2="16.65" y2="16.65"/>
				<line x1="11" y1="8" x2="11" y2="14"/>
				<line x1="8" y1="11" x2="14" y2="11"/>
			</svg>
			Magnifier
		</button>
		<button class="btn" onclick={download}>
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
				<polyline points="7 10 12 15 17 10"/>
				<line x1="12" y1="15" x2="12" y2="3"/>
			</svg>
			Download SVG
		</button>
	</div>
</div>

<style>
	.viewer {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
	}

	.svg-container {
		width: 100%;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		overflow: hidden;
		background: #fff;
		cursor: crosshair;
	}

	.svg-container :global(svg) {
		width: 100%;
		height: auto;
		display: block;
	}

	.lens {
		position: fixed;
		border-radius: 50%;
		overflow: hidden;
		border: 2px solid var(--text-primary);
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
		pointer-events: none;
		z-index: 100;
	}

	.lens-inner {
		will-change: transform;
	}

	.lens-inner :global(svg) {
		width: 100%;
		height: auto;
		display: block;
	}

	.actions {
		display: flex;
		gap: 0.5rem;
	}

	.btn {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.5rem 1rem;
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		font-family: var(--font-sans);
		font-size: 0.8rem;
		cursor: pointer;
		transition: all 0.15s;
	}

	.btn:hover {
		border-color: var(--border-hover);
		color: var(--text-primary);
	}

	.btn.active {
		background: var(--text-primary);
		color: var(--bg-primary);
		border-color: var(--text-primary);
	}
</style>
