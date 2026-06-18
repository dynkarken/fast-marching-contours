<script lang="ts">
	import Topbar from '$lib/components/Topbar.svelte';
	import SvgViewer from '$lib/components/SvgViewer.svelte';
	import PixelTransition from '$lib/components/PixelTransition.svelte';

	let address = $state('');
	let scale = $state<1000 | 5000>(1000);
	let svgContent = $state<string | null>(null);
	let isProcessing = $state(false);
	let coverActive = $state(false);
	let errorMessage = $state<string | null>(null);

	let suggestions = $state<{ tekst: string }[]>([]);
	let showSuggestions = $state(false);
	let selectedIndex = $state(-1);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;

	function onInput() {
		selectedIndex = -1;
		if (debounceTimer) clearTimeout(debounceTimer);
		const q = address.trim();
		if (q.length < 2) {
			suggestions = [];
			showSuggestions = false;
			return;
		}
		debounceTimer = setTimeout(async () => {
			try {
				const res = await fetch(`https://dawa.aws.dk/autocomplete?q=${encodeURIComponent(q)}&type=adresse&per_side=6`);
				if (res.ok) {
					suggestions = await res.json();
					showSuggestions = suggestions.length > 0;
				}
			} catch {}
		}, 150);
	}

	function pickSuggestion(text: string) {
		address = text;
		showSuggestions = false;
		suggestions = [];
	}

	async function generate() {
		if (!address.trim()) return;
		showSuggestions = false;
		isProcessing = true;
		coverActive = true;
		errorMessage = null;

		try {
			const params = new URLSearchParams({ address: address.trim(), scale: String(scale) });
			const res = await fetch(`/api/husportraet?${params}`);
			if (!res.ok) {
				let detail = 'Generering fejlede';
				try { const err = await res.json(); detail = err.detail || detail; } catch {}
				throw new Error(detail);
			}
			svgContent = await res.text();
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Noget gik galt';
			coverActive = false;
		} finally {
			isProcessing = false;
		}
	}

	function onPreviewReady() {
		if (coverActive) coverActive = false;
	}

	function onKeydown(e: KeyboardEvent) {
		if (showSuggestions && suggestions.length > 0) {
			if (e.key === 'ArrowDown') {
				e.preventDefault();
				selectedIndex = Math.min(selectedIndex + 1, suggestions.length - 1);
				return;
			}
			if (e.key === 'ArrowUp') {
				e.preventDefault();
				selectedIndex = Math.max(selectedIndex - 1, -1);
				return;
			}
			if (e.key === 'Enter' && selectedIndex >= 0) {
				e.preventDefault();
				pickSuggestion(suggestions[selectedIndex].tekst);
				return;
			}
			if (e.key === 'Escape') {
				showSuggestions = false;
				return;
			}
		}
		if (e.key === 'Enter' && address.trim() && !coverActive) generate();
	}
</script>

<div class="page">
	<Topbar />

	<div class="main">
		<div class="left-panel">
			<header class="hero">
				<h1>
					<span class="h1-sans">hus</span>
					<em class="h1-serif">Portræt</em>
				</h1>
				<p class="hero-sub">arkitektonisk plakat fra openstreetmap</p>
			</header>

			<div class="controls">
				<div class="ctrl-section">
					<p class="ctrl-label">(adresse)</p>
					<div class="address-wrap">
						<input
							class="address-input"
							type="text"
							bind:value={address}
							oninput={onInput}
							onkeydown={onKeydown}
							onfocusin={() => { if (suggestions.length) showSuggestions = true; }}
							onfocusout={() => { setTimeout(() => showSuggestions = false, 150); }}
							placeholder="Strandvejen 100, Hellerup"
							autocomplete="off"
						/>
						{#if showSuggestions}
							<ul class="suggestions">
								{#each suggestions as s, i}
									<li>
										<button
											class="suggestion"
											class:highlighted={i === selectedIndex}
											onmousedown={() => pickSuggestion(s.tekst)}
										>{s.tekst}</button>
									</li>
								{/each}
							</ul>
						{/if}
					</div>
				</div>

				<div class="ctrl-section">
					<p class="ctrl-label">(skala)</p>
					<div class="scales">
						<button
							class="scale-btn"
							class:active={scale === 1000}
							onclick={() => (scale = 1000)}
						>
							<span class="scale-name">1:1 000</span>
							<span class="scale-sub">420 × 594 m</span>
						</button>
						<button
							class="scale-btn"
							class:active={scale === 5000}
							onclick={() => (scale = 5000)}
						>
							<span class="scale-name">1:5 000</span>
							<span class="scale-sub">2 100 × 2 970 m</span>
						</button>
					</div>
				</div>

				<div class="ctrl-section">
					<p class="ctrl-label">(generér)</p>
					<button
						class="generate"
						class:processing={coverActive}
						onclick={generate}
						disabled={!address.trim() || coverActive}
					>
						{coverActive ? 'genererer…' : 'Generér Husportræt →'}
					</button>
					{#if errorMessage}
						<p class="error">{errorMessage}</p>
					{/if}
				</div>
			</div>
		</div>

		<div class="result-col">
			<div class="result">
				{#if svgContent}
					<div class="result-viewer">
						<SvgViewer {svgContent} preset={String(scale)} onReady={onPreviewReady} />
					</div>
				{:else if !isProcessing}
					<div class="result-empty">
						<div class="empty-text">
							<span class="empty-icon">⌂</span>
							<span class="empty-label">indtast en adresse</span>
						</div>
					</div>
				{/if}

				<PixelTransition active={coverActive} />
			</div>
		</div>
	</div>
</div>

<style>
	.page {
		display: flex;
		flex-direction: column;
		min-height: 100dvh;
	}

	.main {
		flex: 1;
		display: flex;
		flex-direction: column;
	}

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

	.address-wrap {
		position: relative;
	}

	.address-input {
		width: 100%;
		padding: 0.55rem 0.7rem;
		border: 1px solid var(--border-mid);
		border-radius: var(--radius-sm);
		background: transparent;
		color: var(--text);
		font-family: var(--font-sans);
		font-size: 0.85rem;
	}

	.address-input:focus {
		outline: none;
		border-color: var(--border);
	}

	.address-input::placeholder {
		color: var(--text-ghost);
	}

	.suggestions {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		z-index: 50;
		list-style: none;
		background: var(--bg);
		border: 1px solid var(--border);
		border-top: none;
		border-radius: 0 0 var(--radius-sm) var(--radius-sm);
		max-height: 220px;
		overflow-y: auto;
	}

	.suggestion {
		display: block;
		width: 100%;
		padding: 0.5rem 0.7rem;
		border: none;
		background: transparent;
		color: var(--text);
		font-family: var(--font-sans);
		font-size: 0.78rem;
		text-align: left;
		cursor: pointer;
		transition: background 0.08s;
	}

	.suggestion:hover,
	.suggestion.highlighted {
		background: var(--bg-off);
	}

	.scales {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.3rem;
	}

	.scale-btn {
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

	.scale-name {
		font-family: var(--font-sans);
		font-weight: 600;
		font-size: 0.72rem;
		letter-spacing: 0.04em;
		color: var(--text-faint);
		transition: color 0.12s;
	}

	.scale-sub {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-faint);
		opacity: 0.7;
	}

	.scale-btn:hover {
		border-color: var(--border);
	}

	.scale-btn:hover .scale-name {
		color: var(--text);
	}

	.scale-btn.active {
		border-color: var(--border);
		background: var(--text);
	}

	.scale-btn.active .scale-name,
	.scale-btn.active .scale-sub {
		color: var(--bg);
	}

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

	.empty-text {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
	}

	.empty-icon {
		font-size: 2rem;
		color: var(--text-ghost);
	}

	.empty-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-ghost);
	}

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
