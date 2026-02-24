<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { gsap } from 'gsap';
	import ImageUpload from '$lib/components/ImageUpload.svelte';
	import PresetPicker from '$lib/components/PresetPicker.svelte';
	import SvgViewer from '$lib/components/SvgViewer.svelte';
	import Navbar from '$lib/components/Navbar.svelte';

	let selectedFile = $state<File | null>(null);
	let selectedPreset = $state('A');
	let svgContent = $state<string | null>(null);
	let isProcessing = $state(false);
	let errorMessage = $state<string | null>(null);

	let heroEl: HTMLElement;
	let controlsEl: HTMLElement;
	let mm: gsap.MatchMedia | null = null;

	// Wrapper around SvgViewer — GSAP fades this element to manage
	// the dim-on-processing and fade-in-on-completion transitions.
	let viewerWrapEl: HTMLDivElement | null = null;

	$effect(() => {
		const processing = isProcessing; // tracked dependency
		if (!viewerWrapEl) return;

		if (processing) {
			// Dim the existing preview immediately when a new run starts.
			gsap.to(viewerWrapEl, { opacity: 0.25, duration: 0.2, ease: 'power1.out' });
		} else {
			// New result (or error recovery) — fade in from black.
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
				const d = Math.sqrt(dx * dx + dy * dy);

				if (d > 1.04) { line += ' '; continue; }

				const ringPhase = (d * 11) % 1;
				if (ringPhase < 0.14) {
					const ci = Math.floor((1 - d) * (chars.length - 1));
					line += chars[Math.max(1, ci)];
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

			tl.from(heroItems, { opacity: 0, y: isDesktop ? -12 : -6, stagger: 0.1, duration: 0.55 })
			  .from(sections,  { opacity: 0, y: isDesktop ? 16 : 8,  stagger: 0.08, duration: 0.4 }, '-=0.25');

			return () => tl.kill();
		});
	});

	onDestroy(() => { mm?.kill(); });

	async function generate() {
		if (!selectedFile) return;
		isProcessing = true;
		errorMessage = null;
		// Don't clear svgContent here — the old preview stays mounted and
		// fades to 25% while the new one is in flight.

		const formData = new FormData();
		formData.append('image', selectedFile);
		formData.append('preset', selectedPreset);

		try {
			const res = await fetch('/api/process', { method: 'POST', body: formData });
			if (!res.ok) {
				let detail = 'Processing failed';
				try { const err = await res.json(); detail = err.detail || detail; } catch {}
				throw new Error(detail);
			}
			svgContent = await res.text();
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Something went wrong';
		} finally {
			isProcessing = false;
		}
	}
</script>

<Navbar />

<div class="page">
	<!-- Main: left panel (header + controls) | right panel (result) -->
	<div class="main">
		<div class="left-panel">
			<!-- Header lives here, same column as controls -->
			<header class="hero" bind:this={heroEl}>
				<h1>
					<span class="h1-sans">fast marching</span>
					<em class="h1-serif">Contours</em>
				</h1>
				<p class="hero-sub">photographic line art via wave-front propagation</p>
			</header>

			<!-- Controls -->
			<div class="controls" bind:this={controlsEl}>
				<div class="ctrl-section">
					<p class="ctrl-label">(image)</p>
					<ImageUpload bind:file={selectedFile} />
				</div>

				<div class="ctrl-section">
					<p class="ctrl-label">(preset)</p>
					<PresetPicker bind:selected={selectedPreset} />
				</div>

				<div class="ctrl-section">
					<p class="ctrl-label">(generate)</p>
					<button
						class="generate"
						class:processing={isProcessing}
						onclick={generate}
						disabled={!selectedFile || isProcessing}
					>
						{isProcessing ? 'processing...' : 'Generate Contours →'}
					</button>
					{#if errorMessage}
						<p class="error">{errorMessage}</p>
					{/if}
				</div>
			</div>
		</div>

		<!-- Result column: fills remaining space, image constrained within -->
		<div class="result-col">
			<div class="result">
				{#if svgContent}
					<!-- Viewer wrapper — GSAP dims this to 25% while processing,
					     then fades it from 0→1 when the new result arrives. -->
					<div class="result-viewer" bind:this={viewerWrapEl}>
						<SvgViewer {svgContent} preset={selectedPreset} />
					</div>
				{:else if !isProcessing}
					<div class="result-empty">
						<pre class="ascii-art" aria-hidden="true">{asciiArt}</pre>
					</div>
				{/if}

				<!-- Spinner: sibling (not child) of the viewer so it is never
				     affected by the viewer wrapper's dimmed opacity.
				     Fills the space on first generation; overlays on re-runs. -->
				{#if isProcessing}
					<div class="result-spinner" class:overlay={!!svgContent} aria-label="Processing">
						<div class="spinner" role="status"></div>
						<span class="loading-label">processing</span>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	/* ── App shell ── */

	.page {
		display: flex;
		flex-direction: column;
		min-height: 100dvh;
		padding-top: 2.75rem; /* clear the fixed navbar */
	}

	/* ── Main area ── */

	.main {
		flex: 1;
		display: flex;
		flex-direction: column;
	}

	/* ── Left panel (hero + controls) ── */

	.left-panel {
		display: flex;
		flex-direction: column;
		border-bottom: 1px solid var(--border-light);
	}

	.hero {
		padding: 1.5rem 1.5rem 1.25rem;
		border-bottom: 1px solid var(--border-light);
	}

	h1 {
		display: flex;
		flex-direction: column;
		line-height: 0.93;
	}

	.h1-sans {
		font-family: var(--font-sans);
		font-weight: 700;
		font-size: clamp(1.6rem, 5vw, 2rem);
		letter-spacing: -0.025em;
	}

	.h1-serif {
		font-family: var(--font-serif);
		font-style: italic;
		font-weight: 300;
		font-size: clamp(2.2rem, 7vw, 2.8rem);
		letter-spacing: -0.01em;
	}

	.hero-sub {
		margin-top: 0.75rem;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-faint);
	}

	.controls {
		display: flex;
		flex-direction: column;
	}

	.ctrl-section {
		padding: 1.1rem 1.5rem;
		border-bottom: 1px solid var(--border-light);
	}

	.ctrl-label {
		font-family: var(--font-serif);
		font-style: italic;
		font-size: 0.95rem;
		color: var(--text-dim);
		margin-bottom: 0.65rem;
	}

	/* ── Generate button ── */

	.generate {
		position: relative;
		overflow: hidden;
		width: 100%;
		padding: 0.8rem 1rem;
		background: var(--text);
		color: var(--bg);
		border: none;
		border-radius: var(--radius-md);
		font-family: var(--font-sans);
		font-weight: 600;
		font-size: 0.75rem;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		cursor: pointer;
		text-align: left;
		transition: opacity 0.15s;
	}

	.generate:hover:not(:disabled) { opacity: 0.82; }
	.generate:disabled { opacity: 0.2; cursor: not-allowed; }

	.generate.processing::after {
		content: '';
		position: absolute;
		inset: 0;
		background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.18) 45%, rgba(255,255,255,0.18) 55%, transparent 100%);
		animation: sweep 1.6s ease-in-out infinite;
		pointer-events: none;
	}

	@keyframes sweep {
		from { transform: translateX(-120%); }
		to   { transform: translateX(120%); }
	}

	.error {
		margin-top: 0.65rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--error);
	}

	/* ── Result column ── */

	.result-col {
		flex: 1;
		display: flex;
		flex-direction: column;
		padding: 1.5rem;
		min-height: 320px;
	}

	.result {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	/* ── Result viewer wrapper (GSAP-animated) ── */

	.result {
		position: relative; /* anchor for the overlay spinner */
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

	/* ── Spinner (shared between first-gen fill and re-run overlay) ── */

	.result-spinner {
		/* First generation: sits in the flex flow and fills the space */
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.85rem;
		border: 1px solid var(--border-light);
		border-radius: var(--radius-md);
	}

	.result-spinner.overlay {
		/* Re-run: float on top of the dimmed viewer, no border */
		position: absolute;
		inset: 0;
		flex: none;
		border: none;
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

	.result-empty {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid var(--border-light);
		border-radius: var(--radius-md);
	}

	.ascii-art {
		font-family: var(--font-mono);
		font-size: clamp(0.5rem, 1.2vw, 0.72rem);
		line-height: 1.35;
		color: var(--text-ghost);
		white-space: pre;
		overflow: hidden;
		pointer-events: none;
		user-select: none;
	}

	/* ── Desktop: true app layout, viewport-bounded ── */

	@media (min-width: 820px) {
		.page {
			height: 100dvh;
			overflow: hidden;
		}

		.main {
			flex-direction: row;
			min-height: 0;
			flex: 1;
			overflow: hidden;
		}

		.left-panel {
			width: 300px;
			flex-shrink: 0;
			border-bottom: none;
			border-right: 1px solid var(--border-light);
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
