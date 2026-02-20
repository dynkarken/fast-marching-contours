<script lang="ts">

	let { svgContent, preset }: { svgContent: string; preset: string } = $props();

	let lensActive = $state(false);
	let showLens = $state(false);
	let blobUrl = $state<string | null>(null);       // SVG blob — lens + download
	let rasterBlobUrl = $state<string | null>(null); // PNG blob — main display

	// Inline style for the SVG <img> inside the lens, updated every mousemove.
	let lensImgStyle = $state('');

	let imgEl: HTMLImageElement;
	let lensEl: HTMLDivElement;

	const LENS_DIAMETER = 200;
	const LENS_RADIUS = LENS_DIAMETER / 2;
	// How many times to zoom relative to the displayed image.
	const LENS_ZOOM = 3;

	$effect(() => {
		// SVG blob — used by the lens <img> and the download button.
		const blob = new Blob([svgContent], { type: 'image/svg+xml' });
		const svgUrl = URL.createObjectURL(blob);
		blobUrl = svgUrl;
		rasterBlobUrl = null;

		// Matplotlib emits pt units. Convert to CSS px (96 dpi / 72 pt/in),
		// then multiply by RASTER_SCALE so the PNG is always rendered at a
		// higher pixel density than the display area. Downscaling is crisp;
		// upscaling is what causes the mushy grey appearance.
		const RASTER_SCALE = 2;
		const ptW = svgContent.match(/\bwidth="([\d.]+)pt"/);
		const ptH = svgContent.match(/\bheight="([\d.]+)pt"/);
		const canvasW = Math.round((ptW ? parseFloat(ptW[1]) * (96 / 72) : 1200) * RASTER_SCALE);
		const canvasH = Math.round((ptH ? parseFloat(ptH[1]) * (96 / 72) : canvasW / RASTER_SCALE) * RASTER_SCALE);

		// Rasterise the SVG to a canvas, then export as PNG blob for the main view.
		const img = new Image();
		img.onload = () => {
			const canvas = document.createElement('canvas');
			canvas.width = canvasW;
			canvas.height = canvasH;
			canvas.getContext('2d')!.drawImage(img, 0, 0, canvasW, canvasH);
			canvas.toBlob((pngBlob) => {
				if (!pngBlob) return;
				const prev = rasterBlobUrl;
				rasterBlobUrl = URL.createObjectURL(pngBlob);
				if (prev) URL.revokeObjectURL(prev);
			}, 'image/png');
		};
		img.src = svgUrl;

		return () => {
			URL.revokeObjectURL(svgUrl);
			if (rasterBlobUrl) { URL.revokeObjectURL(rasterBlobUrl); rasterBlobUrl = null; }
		};
	});


	function onMouseMove(e: MouseEvent) {
		if (!lensActive) return;
		if (!showLens) showLens = true;

		// Move the lens circle via GPU transform — zero layout reflow.
		lensEl.style.transform =
			`translate(${e.clientX - LENS_RADIUS}px, ${e.clientY - LENS_RADIUS}px)`;

		if (!imgEl || !blobUrl) return;

		// Position the SVG <img> inside the lens so that the cursor point is
		// centred in the lens at LENS_ZOOM× scale.
		const imgRect = imgEl.getBoundingClientRect();
		const mouseX = e.clientX - imgRect.left;
		const mouseY = e.clientY - imgRect.top;
		const zW = imgRect.width  * LENS_ZOOM;
		const zH = imgRect.height * LENS_ZOOM;
		// Translate so the cursor point lands at (LENS_RADIUS, LENS_RADIUS):
		const tx = LENS_RADIUS - mouseX * LENS_ZOOM;
		const ty = LENS_RADIUS - mouseY * LENS_ZOOM;
		lensImgStyle = `position:absolute;top:0;left:0;width:${zW}px;height:${zH}px;transform:translate(${tx}px,${ty}px);display:block;`;
	}

	function onMouseLeave() {
		showLens = false;
	}

	function download() {
		const a = document.createElement('a');
		a.href = blobUrl!;
		a.download = `contour_${preset}.svg`;
		a.click();
	}
</script>

<div class="viewer">
	<div class="viewer-meta">
		<span class="meta-left">
			<em class="meta-label">(output)</em>
			<span class="meta-preset">preset {preset}</span>
		</span>
		<span class="meta-right">svg · contour art</span>
	</div>

	<!-- Main view: raster PNG. Shows a spinner while canvas.toBlob() is in flight. -->
	<div
		class="svg-stage"
		onmousemove={onMouseMove}
		onmouseleave={onMouseLeave}
		role="img"
		aria-label="Generated contour art"
	>
		{#if rasterBlobUrl}
			<img src={rasterBlobUrl} alt="Contour art (raster), preset {preset}" class="svg-raster" bind:this={imgEl} />
		{:else if blobUrl}
			<div class="loading" aria-label="Rasterising preview">
				<div class="spinner" role="status"></div>
				<span class="loading-label">rasterising</span>
			</div>
		{/if}
	</div>

	<!-- Lens: circle-clipped div containing a full-size SVG <img> shifted via
	     CSS transform — crisp vector rendering at LENS_ZOOM× with no canvas
	     rasterisation. -->
	{#if lensActive}
		<div class="lens" class:visible={showLens} bind:this={lensEl}>
			{#if blobUrl}
				<img src={blobUrl} style={lensImgStyle} alt="" aria-hidden="true" />
			{/if}
		</div>
	{/if}

	<div class="actions">
		<button class="action-btn" class:active={lensActive} onclick={() => (lensActive = !lensActive)}>
			<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
				<circle cx="11" cy="11" r="8"/>
				<line x1="21" y1="21" x2="16.65" y2="16.65"/>
				<line x1="11" y1="8" x2="11" y2="14"/>
				<line x1="8" y1="11" x2="14" y2="11"/>
			</svg>
			magnifier
		</button>
		<button class="action-btn" onclick={download}>
			<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
				<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
				<polyline points="7 10 12 15 17 10"/>
				<line x1="12" y1="15" x2="12" y2="3"/>
			</svg>
			export svg
		</button>
	</div>
</div>

<style>
	.viewer {
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		overflow: hidden; /* clips inner content to rounded corners */
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	.viewer-meta {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.5rem 0.85rem;
		border-bottom: 1px solid var(--border-light);
	}

	.meta-left {
		display: flex;
		align-items: baseline;
		gap: 0.75rem;
	}

	.meta-label {
		font-family: var(--font-serif);
		font-style: italic;
		font-size: 0.92rem;
		color: var(--text-dim);
	}

	.meta-preset {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-faint);
	}

	.meta-right {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-ghost);
	}

	.svg-stage {
		flex: 1;
		min-height: 0;
		height: 0; /* makes percentage heights resolvable for children */
		background: #ffffff;
		cursor: crosshair;
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
	}

	.svg-raster {
		max-width: 100%;
		max-height: 100%;
		width: auto;
		height: auto;
		object-fit: contain;
		display: block;
	}

	/* Loading state while canvas.toBlob() rasterises the SVG */
	.loading {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.85rem;
	}

	.spinner {
		width: 22px;
		height: 22px;
		border: 1.5px solid var(--border-light);
		border-top-color: var(--text);
		border-radius: 50%;
		animation: spin 0.75s linear infinite;
	}

	.loading-label {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-faint);
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Lens: circle-clipped div, positioned via GPU transform.
	   No box-shadow — clean edge only. */
	.lens {
		position: fixed;
		left: 0;
		top: 0;
		width: 200px;
		height: 200px;
		transform: translate(-9999px, -9999px);
		will-change: transform;
		border-radius: 50%;
		overflow: hidden;
		border: 1px solid var(--border);
		pointer-events: none;
		z-index: 100;
		background: #fff;
		opacity: 0;
		transition: opacity 0.12s;
	}

	.lens.visible {
		opacity: 1;
	}

	.actions {
		display: flex;
		border-top: 1px solid var(--border-light);
	}

	.action-btn {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.4rem;
		padding: 0.55rem 0.75rem;
		background: transparent;
		color: var(--text-faint);
		border: none;
		border-right: 1px solid var(--border-light);
		font-family: var(--font-mono);
		font-size: 0.62rem;
		text-transform: lowercase;
		letter-spacing: 0.06em;
		cursor: pointer;
		transition: color 0.12s, background 0.12s;
	}

	.action-btn:last-child { border-right: none; }
	.action-btn:hover { color: var(--text); background: var(--bg-off); }
	.action-btn.active {
		color: var(--text);
		background: var(--bg-off);
		border-bottom: 2px solid var(--border);
	}
</style>
