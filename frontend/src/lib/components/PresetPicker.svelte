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
			y: 5,
			stagger: 0.04,
			duration: 0.28,
			ease: 'power2.out',
			onComplete: () => gsap.set(presetsEl.children, { clearProps: 'all' }),
		});
	});

	onDestroy(() => { tween?.kill(); });

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

<p class="desc">{activeDesc}</p>

<style>
	.presets {
		display: flex;
		gap: 0.28rem;
		flex-wrap: wrap;
	}

	.preset {
		width: 2.1rem;
		height: 2.1rem;
		border: 2px solid var(--border-light);
		border-radius: var(--radius-sm);
		background: var(--bg-inset);
		color: var(--text-faint);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		font-weight: 500;
		cursor: pointer;
		transition: border-color 0.1s, color 0.1s, background 0.1s;
	}

	.preset:hover {
		border-color: var(--border);
		color: var(--text);
		background: var(--bg-off);
	}

	.preset.active {
		border-color: var(--border);
		border-width: 2px;
		background: var(--text);
		color: var(--bg);
	}

	.desc {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		letter-spacing: 0.04em;
		color: var(--text-faint);
		margin-top: 0.55rem;
	}
</style>
