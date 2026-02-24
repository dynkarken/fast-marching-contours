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
				scale: 0.92,
				duration: 0.3,
				ease: 'back.out(1.4)',
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
			<p class="change-hint">[ click to change ]</p>
		</div>
	{:else}
		<div class="empty">
			<p class="prompt">[ drop image or click to browse ]</p>
			<p class="hint">jpg · png · webp</p>
		</div>
	{/if}
</div>

<style>
	.dropzone {
		border: 2px dashed var(--border-light);
		border-radius: var(--radius-sm);
		padding: 1.25rem 1rem;
		text-align: center;
		cursor: pointer;
		background: var(--bg-inset);
		transition: border-color 0.12s, background 0.12s;
	}

	.dropzone:hover,
	.dropzone.dragging {
		border-color: var(--accent-dark);
		background: var(--bg-off);
	}

	.dropzone.has-file {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		text-align: left;
		padding: 0.7rem 0.85rem;
	}

	.empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.3rem;
	}

	.preview {
		width: 44px;
		height: 44px;
		object-fit: cover;
		flex-shrink: 0;
		border: 2px solid var(--border);
		border-radius: var(--radius-sm);
	}

	.file-info { min-width: 0; }

	.filename {
		font-family: var(--font-mono);
		font-size: 0.66rem;
		color: var(--text);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.change-hint {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		color: var(--text-faint);
		margin-top: 0.1rem;
		letter-spacing: 0.04em;
	}

	.prompt {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text-dim);
		letter-spacing: 0.02em;
	}

	.hint {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		letter-spacing: 0.08em;
		color: var(--text-ghost);
	}
</style>
