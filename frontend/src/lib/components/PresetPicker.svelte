<script lang="ts">
	import { gsap } from 'gsap';
	import { onMount, onDestroy } from 'svelte';

	let { selected = $bindable() }: { selected: string } = $props();

	const presets = [
		{ id: 'A', desc: 'balanced · default settings' },
		{ id: 'B', desc: 'high contrast, low brightness' },
		{ id: 'C', desc: 'low contrast, high brightness' },
		{ id: 'D', desc: 'gamma darkening applied' },
		{ id: 'E', desc: 'heavy blur, soft contrast' },
		{ id: 'F', desc: 'sharp, subtle processing' },
	];

	let presetsEl: HTMLDivElement;
	let tween: gsap.core.Tween | null = null;

	onMount(() => {
		if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
			gsap.set(presetsEl.children, { opacity: 1 });
			return;
		}

		tween = gsap.from(Array.from(presetsEl.children), {
			opacity: 0,
			y: 6,
			stagger: 0.05,
			duration: 0.3,
			ease: 'power2.out',
			onComplete: () => {
				gsap.set(presetsEl.children, { clearProps: 'all' });
			},
		});
	});

	onDestroy(() => {
		tween?.kill();
	});

	const activeDesc = $derived(presets.find((p) => p.id === selected)?.desc ?? '');
</script>

<div class="presets" bind:this={presetsEl}>
	{#each presets as preset}
		<button
			class="preset"
			class:active={selected === preset.id}
			onclick={() => (selected = preset.id)}
			title={preset.desc}
		>
			{preset.id}
		</button>
	{/each}
</div>

<p class="desc"><em>{activeDesc}</em></p>

<style>
	.presets {
		display: flex;
		gap: 0.3rem;
		flex-wrap: wrap;
	}

	.preset {
		width: 2.2rem;
		height: 2.2rem;
		border: 1px solid var(--border-mid);
		border-radius: var(--radius-sm);
		background: transparent;
		color: var(--text-faint);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		font-weight: 500;
		cursor: pointer;
		transition: border-color 0.12s, color 0.12s, background 0.12s;
	}

	.preset:hover {
		border-color: var(--border);
		color: var(--text);
	}

	.preset.active {
		border-color: var(--border);
		background: var(--text);
		color: var(--bg);
	}

	.desc {
		font-family: var(--font-serif);
		font-style: italic;
		font-weight: 300;
		font-size: 0.9rem;
		color: var(--text-faint);
		margin-top: 0.6rem;
	}
</style>
