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
				scale: 0.9,
				duration: 0.35,
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
			<p class="change-hint">click to change</p>
		</div>
	{:else}
		<div class="empty">
			<p class="prompt">drop image or click to browse</p>
			<p class="hint">jpg · png · webp</p>
		</div>
	{/if}
</div>

<style>
	.dropzone {
		border: 1px solid var(--border-mid);
		border-radius: var(--radius-md);
		padding: 1.5rem 1.25rem;
		text-align: center;
		cursor: pointer;
		transition: border-color 0.15s, background 0.15s;
	}

	.dropzone:hover,
	.dropzone.dragging {
		border-color: var(--border);
		background: var(--bg-off);
	}

	.dropzone.has-file {
		display: flex;
		align-items: center;
		gap: 0.85rem;
		text-align: left;
		padding: 0.85rem 1rem;
	}

	.empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.35rem;
	}

	.preview {
		width: 48px;
		height: 48px;
		object-fit: cover;
		flex-shrink: 0;
		border: 1px solid var(--border-light);
		border-radius: var(--radius-sm);
	}

	.file-info {
		min-width: 0;
	}

	.filename {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.change-hint {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text-faint);
		margin-top: 0.15rem;
	}

	.prompt {
		font-family: var(--font-serif);
		font-style: italic;
		font-size: 0.95rem;
		color: var(--text-dim);
	}

	.hint {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		letter-spacing: 0.08em;
		color: var(--text-ghost);
	}
</style>
