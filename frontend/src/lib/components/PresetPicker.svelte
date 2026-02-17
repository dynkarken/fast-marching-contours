<script lang="ts">
	import { gsap } from 'gsap';
	import { onMount, onDestroy } from 'svelte';

	let { selected = $bindable() }: { selected: string } = $props();

	const presets = [
		{ id: 'A', desc: 'Current settings' },
		{ id: 'B', desc: 'More contrast, less bright' },
		{ id: 'C', desc: 'Less contrast, brighter' },
		{ id: 'D', desc: 'With gamma darkening' },
		{ id: 'E', desc: 'More blur, less contrast' },
		{ id: 'F', desc: 'Less blur, subtle processing' },
	];

	let presetsEl: HTMLDivElement;
	let tween: gsap.core.Tween | null = null;

	onMount(() => {
		if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
			gsap.set(presetsEl.children, { opacity: 1, scale: 1 });
			return;
		}

		tween = gsap.from(Array.from(presetsEl.children), {
			opacity: 0,
			scale: 0.8,
			stagger: 0.05,
			duration: 0.35,
			ease: 'back.out(2)',
			onComplete: () => {
				gsap.set(presetsEl.children, { clearProps: 'all' });
			},
		});
	});

	onDestroy(() => {
		tween?.kill();
	});
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

<p class="desc">{presets.find((p) => p.id === selected)?.desc}</p>

<style>
	.presets {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.preset {
		min-width: 3rem;
		height: 3rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: transparent;
		color: var(--text-secondary);
		font-family: var(--font-mono);
		font-size: 1rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
	}

	.preset:hover {
		border-color: var(--border-hover);
		color: var(--text-primary);
	}

	.preset.active {
		border-color: var(--text-primary);
		background: var(--text-primary);
		color: var(--bg-primary);
	}

	.desc {
		font-size: 0.8rem;
		color: var(--text-muted);
		margin-top: 0.5rem;
	}
</style>
