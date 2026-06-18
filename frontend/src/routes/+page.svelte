<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { gsap } from 'gsap';
	import ImageUpload from '$lib/components/ImageUpload.svelte';
	import PresetPicker from '$lib/components/PresetPicker.svelte';
	import SvgViewer from '$lib/components/SvgViewer.svelte';
	import PixelTransition from '$lib/components/PixelTransition.svelte';
	import Topbar from '$lib/components/Topbar.svelte';
	import { runSketch, SCRIBBLE_PRESETS, FLUID_PRESETS, WAVES_PRESETS } from '$lib/sketch';
	import type { SketchPreset } from '$lib/sketch';

	const STYLES = [
		{ id: 'contours', label: 'Contours', sub: 'wave-front propagation' },
		{ id: 'scribble', label: 'Scribble', sub: 'darkness-chasing lines' },
		{ id: 'fluid', label: 'Fluid', sub: 'sweeping curves' },
		{ id: 'waves', label: 'Waves', sub: 'squiggle scanlines' },
	] as const;

	type StyleId = (typeof STYLES)[number]['id'];

	const SKETCH_STYLE_PRESETS: Partial<Record<StyleId, SketchPreset[]>> = {
		scribble: SCRIBBLE_PRESETS,
		fluid: FLUID_PRESETS,
		waves: WAVES_PRESETS,
	};

	let selectedFile = $state<File | null>(null);
	let selectedStyle = $state<StyleId>('contours');
	let selectedPreset = $state('A');
	let sketchProgress = $state<string | null>(null);
	let seed = $state(Math.floor(Math.random() * 100000));

	function rerollSeed() {
		seed = Math.floor(Math.random() * 100000);
	}

	// waves is deterministic, contours runs on the backend — seed only matters here
	const seedRelevant = $derived(selectedStyle === 'scribble' || selectedStyle === 'fluid');
	let svgContent = $state<string | null>(null);
	let isProcessing = $state(false);
	let coverActive = $state(false);
	let errorMessage = $state<string | null>(null);

	let heroEl: HTMLElement;
	let controlsEl: HTMLElement;
	let mm: gsap.MatchMedia | null = null;

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
				onComplete: () => { gsap.set([...heroItems, ...sections], { clearProps: 'all' }); },
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
		coverActive = true;
		errorMessage = null;
		sketchProgress = null;

		try {
			const stylePresets = SKETCH_STYLE_PRESETS[selectedStyle];
			if (stylePresets) {
				const preset = stylePresets.find((p) => p.id === selectedPreset) ?? stylePresets[0];
				svgContent = await runSketch(selectedFile, preset.params, seed, (done, total) => {
					sketchProgress = `${Math.round((done / total) * 100)}%`;
				});
			} else {
				const formData = new FormData();
				formData.append('image', selectedFile);
				formData.append('preset', selectedPreset);

				const res = await fetch('/api/process', { method: 'POST', body: formData });
				if (!res.ok) {
					let detail = 'Processing failed';
					try { const err = await res.json(); detail = err.detail || detail; } catch {}
					throw new Error(detail);
				}
				svgContent = await res.text();
			}
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Something went wrong';
			coverActive = false;
		} finally {
			isProcessing = false;
			sketchProgress = null;
		}
	}

	function onPreviewReady() {
		if (coverActive) coverActive = false;
	}
</script>

<div class="page">
	<Topbar />

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
					<p class="ctrl-label">(style)</p>
					<div class="styles">
						{#each STYLES as style}
							<button
								class="style-btn"
								class:active={selectedStyle === style.id}
								onclick={() => (selectedStyle = style.id)}
							>
								<span class="style-name">{style.label}</span>
								<span class="style-sub">{style.sub}</span>
							</button>
						{/each}
					</div>
				</div>

				<div class="ctrl-section">
					<p class="ctrl-label">(preset)</p>
					{#if SKETCH_STYLE_PRESETS[selectedStyle]}
						<PresetPicker
							bind:selected={selectedPreset}
							presets={SKETCH_STYLE_PRESETS[selectedStyle]!.map(({ id, desc }) => ({ id, desc }))}
						/>
					{:else}
						<PresetPicker bind:selected={selectedPreset} />
					{/if}
				</div>

				{#if seedRelevant}
					<div class="ctrl-section">
						<p class="ctrl-label">(seed)</p>
						<div class="seed-row">
							<input
								class="seed-input"
								type="number"
								bind:value={seed}
								min="0"
								max="999999"
								aria-label="random seed"
							/>
							<button class="seed-reroll" onclick={rerollSeed} title="new random seed">↻</button>
						</div>
						<p class="seed-hint">same seed = identical drawing</p>
					</div>
				{/if}

				<div class="ctrl-section">
					<p class="ctrl-label">(generate)</p>
					<button
						class="generate"
						class:processing={coverActive}
						onclick={generate}
						disabled={!selectedFile || coverActive}
					>
						{coverActive
							? sketchProgress
								? `drawing… ${sketchProgress}`
								: 'processing...'
							: `Generate ${STYLES.find((s) => s.id === selectedStyle)?.label} →`}
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
					<div class="result-viewer">
						<SvgViewer {svgContent} preset={selectedPreset} onReady={onPreviewReady} />
					</div>
				{:else if !isProcessing}
					<div class="result-empty">
						<pre class="ascii-art" aria-hidden="true">{asciiArt}</pre>
					</div>
				{/if}

				<PixelTransition active={coverActive} />
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

	/* ── Style toggle ── */

	.styles {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.3rem;
	}

	.style-btn {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		padding: 0.55rem 0.65rem;
		border: 1px solid var(--border-mid);
		border-radius: var(--radius-sm);
		background: transparent;
		text-align: left;
		cursor: pointer;
		transition: border-color 0.12s, color 0.12s, background 0.12s;
	}

	.style-name {
		font-family: var(--font-sans);
		font-weight: 600;
		font-size: 0.72rem;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--text-faint);
		transition: color 0.12s;
	}

	.style-sub {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-faint);
		opacity: 0.7;
	}

	.style-btn:hover {
		border-color: var(--border);
	}

	.style-btn:hover .style-name {
		color: var(--text);
	}

	.style-btn.active {
		border-color: var(--border);
		background: var(--text);
	}

	.style-btn.active .style-name,
	.style-btn.active .style-sub {
		color: var(--bg);
	}

	/* ── Seed control ── */

	.seed-row {
		display: flex;
		gap: 0.3rem;
	}

	.seed-input {
		flex: 1;
		min-width: 0;
		padding: 0.45rem 0.6rem;
		border: 1px solid var(--border-mid);
		border-radius: var(--radius-sm);
		background: transparent;
		color: var(--text);
		font-family: var(--font-mono);
		font-size: 0.78rem;
	}

	.seed-input:focus {
		outline: none;
		border-color: var(--border);
	}

	.seed-reroll {
		width: 2.2rem;
		border: 1px solid var(--border-mid);
		border-radius: var(--radius-sm);
		background: transparent;
		color: var(--text-faint);
		font-size: 0.9rem;
		cursor: pointer;
		transition: border-color 0.12s, color 0.12s;
	}

	.seed-reroll:hover {
		border-color: var(--border);
		color: var(--text);
	}

	.seed-hint {
		margin-top: 0.45rem;
		font-family: var(--font-mono);
		font-size: 0.58rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-faint);
	}

	/* ── Generate button ── */

	.generate {
		position: relative;
		overflow: hidden;
		width: 100%;
		padding: 0.8rem 1rem;
		background: var(--accent);
		color: #ffffff;
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
