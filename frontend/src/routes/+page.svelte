<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { gsap } from 'gsap';
	import ImageUpload from '$lib/components/ImageUpload.svelte';
	import PresetPicker from '$lib/components/PresetPicker.svelte';
	import SvgViewer from '$lib/components/SvgViewer.svelte';
	import Navbar from '$lib/components/Navbar.svelte';

	let selectedFile  = $state<File | null>(null);
	let selectedPreset= $state('A');
	let svgContent    = $state<string | null>(null);
	let isProcessing  = $state(false);
	let errorMessage  = $state<string | null>(null);

	// ASCII spinner
	const spinFrames = ['|', '/', '—', '\\'];
	let spinFrame = $state(0);
	let spinInterval: ReturnType<typeof setInterval> | null = null;

	$effect(() => {
		if (isProcessing) {
			spinInterval = setInterval(() => { spinFrame = (spinFrame + 1) % spinFrames.length; }, 120);
		} else {
			if (spinInterval) { clearInterval(spinInterval); spinInterval = null; }
		}
	});

	let heroEl: HTMLElement;
	let controlsEl: HTMLElement;
	let viewerWrapEl: HTMLDivElement | null = null;
	let mm: gsap.MatchMedia | null = null;

	$effect(() => {
		const processing = isProcessing;
		if (!viewerWrapEl) return;
		if (processing) {
			gsap.to(viewerWrapEl, { opacity: 0.25, duration: 0.2, ease: 'power1.out' });
		} else {
			gsap.fromTo(viewerWrapEl, { opacity: 0 }, { opacity: 1, duration: 0.45, ease: 'power2.out' });
		}
	});

	function generateContourAscii(cols: number, rows: number): string {
		const cx = (cols - 1) / 2;
		const cy = (rows - 1) / 2;
		const chars = ' ·.:-=+*#@';
		const lines: string[] = [];
		for (let y = 0; y < rows; y++) {
			let line = '';
			for (let x = 0; x < cols; x++) {
				const dx = (x - cx) / (cx * 0.88);
				const dy = (y - cy) / (cy * 0.88) * 1.85;
				const d  = Math.sqrt(dx * dx + dy * dy);
				if (d > 1.04) { line += ' '; continue; }
				const ringPhase = (d * 11) % 1;
				if (ringPhase < 0.14) {
					line += chars[Math.max(1, Math.floor((1 - d) * (chars.length - 1)))];
				} else {
					line += ' ';
				}
			}
			lines.push(line);
		}
		return lines.join('\n');
	}

	const asciiArt = generateContourAscii(68, 24);

	onMount(() => {
		const heroItems = Array.from(heroEl.children);
		const sections  = Array.from(controlsEl.querySelectorAll('.ctrl-section'));

		mm = gsap.matchMedia();
		mm.add({
			noMotion:  '(prefers-reduced-motion: reduce)',
			isDesktop: '(min-width: 820px)',
		}, (ctx) => {
			const { noMotion, isDesktop } = ctx.conditions!;
			if (noMotion) {
				gsap.set([...heroItems, ...sections], { opacity: 1 });
				return;
			}
			const tl = gsap.timeline({
				defaults: { ease: 'power3.out' },
				onComplete: () => gsap.set([...heroItems, ...sections], { clearProps: 'all' }),
			});
			tl.from(heroItems, { opacity: 0, y: isDesktop ? -10 : -5, stagger: 0.08, duration: 0.45, delay: 0.25 })
			  .from(sections,  { opacity: 0, y: isDesktop ? 12 : 6,  stagger: 0.06, duration: 0.35 }, '-=0.2');
			return () => tl.kill();
		});
	});

	onDestroy(() => {
		mm?.kill();
		if (spinInterval) clearInterval(spinInterval);
	});

	async function generate() {
		if (!selectedFile) return;
		isProcessing  = true;
		errorMessage  = null;

		const formData = new FormData();
		formData.append('image', selectedFile);
		formData.append('preset', selectedPreset);

		try {
			const res = await fetch('/api/process', { method: 'POST', body: formData });
			if (!res.ok) {
				let detail = 'processing failed';
				try { const err = await res.json(); detail = err.detail || detail; } catch {}
				throw new Error(detail);
			}
			svgContent = await res.text();
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'something went wrong';
		} finally {
			isProcessing = false;
		}
	}
</script>

<!-- Fixed desktop background with teal blobs -->
<div class="desktop-bg" aria-hidden="true">
	<div class="blob blob-1"></div>
	<div class="blob blob-2"></div>
	<div class="blob blob-3"></div>
</div>

<Navbar />

<!-- Desktop canvas — sits below taskbar -->
<div class="desktop">
	<!-- Floating app window -->
	<div class="window">
		<!-- Window chrome: dots + title -->
		<div class="window-chrome">
			<div class="window-dots">
				<span class="dot"></span>
				<span class="dot"></span>
			</div>
			<span class="window-title">fast-marching-contours — image processor</span>
			<div class="window-dots" style="visibility:hidden" aria-hidden="true">
				<span class="dot"></span>
				<span class="dot"></span>
			</div>
		</div>

		<!-- Window body: two-panel layout -->
		<div class="window-body">
			<!-- Left panel: header + controls -->
			<div class="left-panel">
				<header class="hero" bind:this={heroEl}>
					<p class="hero-prompt">$ image-processor v1.0</p>
					<h1>fast&#8209;marching<br>contours</h1>
					<p class="hero-sub">photographic line art via wavefront propagation</p>
				</header>

				<div class="controls" bind:this={controlsEl}>
					<div class="ctrl-section">
						<p class="ctrl-label">&gt; image</p>
						<ImageUpload bind:file={selectedFile} />
					</div>

					<div class="ctrl-section">
						<p class="ctrl-label">&gt; preset</p>
						<PresetPicker bind:selected={selectedPreset} />
					</div>

					<div class="ctrl-section">
						<p class="ctrl-label">&gt; run</p>
						<button
							class="generate"
							class:processing={isProcessing}
							onclick={generate}
							disabled={!selectedFile || isProcessing}
						>
							{#if isProcessing}
								<span class="spin-char" aria-hidden="true">{spinFrames[spinFrame]}</span>
								processing...
							{:else}
								$ generate-contours
							{/if}
						</button>
						{#if errorMessage}
							<p class="error">! {errorMessage}</p>
						{/if}
					</div>
				</div>
			</div>

			<!-- Result column -->
			<div class="result-col">
				<div class="result">
					{#if svgContent}
						<div class="result-viewer" bind:this={viewerWrapEl}>
							<SvgViewer {svgContent} preset={selectedPreset} />
						</div>
					{:else if !isProcessing}
						<div class="result-empty">
							<pre class="ascii-art" aria-hidden="true">{asciiArt}</pre>
							<p class="empty-hint">no output yet — drop an image and run</p>
						</div>
					{/if}

					{#if isProcessing}
						<div class="result-spinner" class:overlay={!!svgContent} aria-label="Processing">
							<p class="spinner-text" role="status">
								{spinFrames[spinFrame]} processing image
							</p>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	/* ── Desktop background ── */

	.desktop-bg {
		position: fixed;
		inset: 0;
		z-index: -1;
		background: var(--bg);
		overflow: hidden;
	}

	.blob {
		position: absolute;
		background: var(--accent);
		opacity: 0.55;
	}

	/* Upper-left sweeping ribbon */
	.blob-1 {
		width: 75%;
		height: 60%;
		top: -18%;
		left: -8%;
		border-radius: 35% 65% 70% 30% / 38% 32% 68% 62%;
		transform: rotate(-10deg);
	}

	/* Lower-right ribbon */
	.blob-2 {
		width: 65%;
		height: 55%;
		bottom: -14%;
		right: -6%;
		border-radius: 60% 40% 38% 62% / 55% 60% 40% 45%;
		transform: rotate(14deg);
	}

	/* Small accent blob mid-left */
	.blob-3 {
		width: 28%;
		height: 30%;
		bottom: 8%;
		left: 2%;
		border-radius: 50% 50% 40% 60% / 50% 40% 60% 50%;
		transform: rotate(-5deg);
		opacity: 0.3;
	}

	/* ── Desktop canvas ── */

	.desktop {
		min-height: 100dvh;
		padding: calc(2rem + 1rem) 1.25rem 1.25rem; /* taskbar(2rem) + gap(1rem) */
		display: flex;
		align-items: flex-start;
		justify-content: center;
	}

	/* ── Window ── */

	.window {
		width: 100%;
		max-width: 1280px;
		background: var(--bg-window);
		border: 2.5px solid var(--border);
		border-radius: var(--radius-window);
		overflow: hidden;
		box-shadow: 6px 6px 0 rgba(28, 25, 22, 0.18);
		display: flex;
		flex-direction: column;
	}

	/* Window chrome bar */
	.window-chrome {
		background: var(--bg-inset);
		border-bottom: 2px solid var(--border);
		height: 2rem;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 0.75rem;
		flex-shrink: 0;
	}

	.window-dots {
		display: flex;
		gap: 0.35rem;
		flex-shrink: 0;
	}

	.dot {
		width: 11px;
		height: 11px;
		border-radius: 50%;
		border: 1.5px solid var(--border);
		background: transparent;
		display: block;
	}

	.window-title {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		letter-spacing: 0.05em;
		color: var(--text-dim);
		text-align: center;
		flex: 1;
	}

	/* ── Window body ── */

	.window-body {
		display: flex;
		flex-direction: column;
		flex: 1;
	}

	/* ── Left panel ── */

	.left-panel {
		display: flex;
		flex-direction: column;
		border-bottom: 2px solid var(--border);
	}

	/* ── Hero header ── */

	.hero {
		padding: 1.4rem 1.4rem 1.1rem;
		border-bottom: 2px solid var(--border);
	}

	.hero-prompt {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		letter-spacing: 0.08em;
		color: var(--accent-dark);
		margin-bottom: 0.5rem;
	}

	h1 {
		font-family: var(--font-mono);
		font-weight: 500;
		font-size: clamp(1.25rem, 5vw, 1.75rem);
		line-height: 1.05;
		letter-spacing: -0.02em;
		color: var(--text);
	}

	.hero-sub {
		margin-top: 0.65rem;
		font-family: var(--font-mono);
		font-size: 0.55rem;
		letter-spacing: 0.08em;
		color: var(--text-faint);
	}

	/* ── Controls ── */

	.controls {
		display: flex;
		flex-direction: column;
	}

	.ctrl-section {
		padding: 1rem 1.4rem;
		border-bottom: 1px solid var(--border-light);
	}

	.ctrl-label {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		letter-spacing: 0.08em;
		color: var(--accent-dark);
		margin-bottom: 0.6rem;
	}

	/* ── Generate button ── */

	.generate {
		position: relative;
		overflow: hidden;
		width: 100%;
		padding: 0.7rem 1rem;
		background: var(--text);
		color: var(--bg);
		border: 2px solid var(--border);
		border-radius: var(--radius-sm);
		font-family: var(--font-mono);
		font-weight: 500;
		font-size: 0.68rem;
		letter-spacing: 0.04em;
		cursor: pointer;
		text-align: left;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		transition: opacity 0.12s;
	}

	.generate:hover:not(:disabled) { opacity: 0.82; }
	.generate:disabled { opacity: 0.28; cursor: not-allowed; }

	.generate.processing::after {
		content: '';
		position: absolute;
		inset: 0;
		background: linear-gradient(90deg, transparent 0%, rgba(127,206,206,0.22) 45%, rgba(127,206,206,0.22) 55%, transparent 100%);
		animation: sweep 1.4s ease-in-out infinite;
		pointer-events: none;
	}

	@keyframes sweep {
		from { transform: translateX(-120%); }
		to   { transform: translateX(120%); }
	}

	.spin-char {
		display: inline-block;
		width: 0.8em;
		text-align: center;
	}

	.error {
		margin-top: 0.6rem;
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--error);
		letter-spacing: 0.04em;
	}

	/* ── Result column ── */

	.result-col {
		flex: 1;
		display: flex;
		flex-direction: column;
		padding: 1.25rem;
		min-height: 300px;
	}

	.result {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-height: 0;
		position: relative;
	}

	.result-viewer {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
	}

	.result-viewer :global(.viewer) {
		flex: 1;
		min-height: 0;
	}

	/* ── Empty state ── */

	.result-empty {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1.25rem;
		border: 2px dashed var(--border-light);
		border-radius: var(--radius-md);
	}

	.ascii-art {
		font-family: var(--font-mono);
		font-size: clamp(0.48rem, 1.1vw, 0.68rem);
		line-height: 1.35;
		color: var(--text-ghost);
		white-space: pre;
		overflow: hidden;
		pointer-events: none;
		user-select: none;
	}

	.empty-hint {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		letter-spacing: 0.06em;
		color: var(--text-ghost);
	}

	/* ── Spinner ── */

	.result-spinner {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 2px dashed var(--border-light);
		border-radius: var(--radius-md);
	}

	.result-spinner.overlay {
		position: absolute;
		inset: 0;
		flex: none;
		border: none;
	}

	.spinner-text {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		letter-spacing: 0.08em;
		color: var(--text-dim);
	}

	/* ── Desktop: true app layout ── */

	@media (min-width: 820px) {
		.desktop {
			height: 100dvh;
			overflow: hidden;
			align-items: center;
		}

		.window {
			height: calc(100% - 2rem); /* subtract extra gap */
		}

		.window-body {
			flex-direction: row;
			min-height: 0;
			flex: 1;
			overflow: hidden;
		}

		.left-panel {
			width: 288px;
			flex-shrink: 0;
			border-bottom: none;
			border-right: 2px solid var(--border);
			overflow-y: auto;
		}

		.result-col {
			flex: 1;
			min-width: 0;
			overflow: hidden;
		}

		.result {
			height: 100%;
		}
	}
</style>
