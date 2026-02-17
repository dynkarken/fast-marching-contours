<script lang="ts">
	import { gsap } from 'gsap';
	import { onDestroy } from 'svelte';

	let { file = $bindable() }: { file: File | null } = $props();

	let dragging = $state(false);
	let previewUrl = $state<string | null>(null);
	let inputEl: HTMLInputElement;
	let previewEl = $state<HTMLImageElement | null>(null);
	let tween: gsap.core.Tween | null = null;

	function handleFile(f: File) {
		file = f;
		if (previewUrl) URL.revokeObjectURL(previewUrl);
		previewUrl = URL.createObjectURL(f);

		requestAnimationFrame(() => {
			if (!previewEl) return;
			if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
				gsap.set(previewEl, { opacity: 1, scale: 1 });
				return;
			}
			tween?.kill();
			tween = gsap.from(previewEl, {
				opacity: 0,
				scale: 0.85,
				duration: 0.4,
				ease: 'back.out(1.7)',
			});
		});
	}

	function onDrop(e: DragEvent) {
		dragging = false;
		const f = e.dataTransfer?.files[0];
		if (f) handleFile(f);
	}

	function onSelect(e: Event) {
		const target = e.target as HTMLInputElement;
		const f = target.files?.[0];
		if (f) handleFile(f);
	}

	onDestroy(() => {
		tween?.kill();
		if (previewUrl) URL.revokeObjectURL(previewUrl);
	});
</script>

<div
	class="dropzone"
	class:dragging
	class:has-file={!!previewUrl}
	role="button"
	tabindex="0"
	ondragover={(e) => { e.preventDefault(); dragging = true; }}
	ondragleave={() => (dragging = false)}
	ondrop={(e) => { e.preventDefault(); onDrop(e); }}
	onclick={() => inputEl.click()}
	onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputEl.click(); }}
>
	<input
		bind:this={inputEl}
		type="file"
		accept=".jpg,.jpeg,.png,.webp"
		onchange={onSelect}
		hidden
	/>

	{#if previewUrl}
		<img bind:this={previewEl} src={previewUrl} alt="Preview" class="preview" />
		<div class="file-info">
			<p class="filename">{file?.name}</p>
			<p class="change">Click to change</p>
		</div>
	{:else}
		<div class="empty">
			<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
				<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
				<polyline points="17 8 12 3 7 8"/>
				<line x1="12" y1="3" x2="12" y2="15"/>
			</svg>
			<p class="prompt">Drop image or click to browse</p>
			<p class="hint">JPG, PNG, WebP</p>
		</div>
	{/if}
</div>

<style>
	.dropzone {
		border: 1px dashed var(--border-hover);
		border-radius: var(--radius-md);
		padding: 1.5rem;
		text-align: center;
		cursor: pointer;
		transition: border-color 0.2s, background 0.2s;
		background: transparent;
	}

	.dropzone:hover,
	.dropzone.dragging {
		border-color: var(--border-active);
		background: var(--bg-elevated);
	}

	.dropzone.has-file {
		display: flex;
		align-items: center;
		gap: 1rem;
		text-align: left;
		padding: 1rem;
	}

	.empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		color: var(--text-muted);
	}

	.preview {
		width: 64px;
		height: 64px;
		border-radius: var(--radius-sm);
		object-fit: cover;
		flex-shrink: 0;
	}

	.file-info {
		min-width: 0;
	}

	.filename {
		font-size: 0.85rem;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.change {
		font-size: 0.75rem;
		color: var(--text-muted);
		margin-top: 0.15rem;
	}

	.prompt {
		font-size: 0.9rem;
		color: var(--text-secondary);
	}

	.hint {
		font-size: 0.75rem;
		color: var(--text-muted);
		font-family: var(--font-mono);
	}
</style>
