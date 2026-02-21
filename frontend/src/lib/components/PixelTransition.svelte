<script lang="ts">
	import { gsap } from 'gsap';
	import { untrack, tick } from 'svelte';

	let { active = false }: { active: boolean } = $props();

	let gridEl: HTMLDivElement;
	let phase = $state<'idle' | 'covering' | 'holding' | 'revealing'>('idle');
	let wantReveal = false;
	let currentTl: gsap.core.Timeline | null = null;

	const COLS = 20;
	const ROWS = 14;
	const TOTAL = COLS * ROWS;
	const corners = new Set([0, COLS - 1, TOTAL - COLS, TOTAL - 1]);
	const blocks = Array.from({ length: TOTAL });

	$effect(() => {
		const isActive = active;
		const currentPhase = untrack(() => phase);

		if (isActive && currentPhase === 'idle') {
			cover();
		} else if (!isActive) {
			if (currentPhase === 'holding') {
				reveal();
			} else if (currentPhase === 'covering') {
				wantReveal = true;
			}
		}
	});

	async function cover() {
		phase = 'covering';
		wantReveal = false;
		await tick();

		if (!gridEl) return;
		if (currentTl) currentTl.kill();

		const cells = Array.from(gridEl.children);
		gsap.set(cells, { opacity: 0 });

		currentTl = gsap.timeline({
			onComplete: () => {
				phase = 'holding';
				if (wantReveal) {
					setTimeout(() => reveal(), 350);
				}
			}
		});

		currentTl.to(cells, {
			opacity: 1,
			duration: 0.001,
			stagger: { amount: 0.55, from: 'random' },
			ease: 'none'
		});
	}

	function reveal() {
		phase = 'revealing';
		if (currentTl) currentTl.kill();

		const cells = Array.from(gridEl.children);

		currentTl = gsap.timeline({
			onComplete: () => {
				phase = 'idle';
				wantReveal = false;
			}
		});

		currentTl.to(cells, {
			opacity: 0,
			duration: 0.001,
			stagger: { amount: 0.7, from: 'random' },
			ease: 'none'
		});
	}
</script>

<div class="px-overlay" class:visible={phase !== 'idle'}>
	<div class="px-grid" bind:this={gridEl} style="--cols: {COLS}; --rows: {ROWS}">
		{#each blocks as _, i}
			<div class="px-block" class:corner-tl={i === 0} class:corner-tr={i === COLS - 1} class:corner-bl={i === TOTAL - COLS} class:corner-br={i === TOTAL - 1}></div>
		{/each}
	</div>
	<div class="px-label" class:visible={phase === 'covering' || phase === 'holding'}>
		<div class="px-spinner"></div>
		<span>processing</span>
	</div>
</div>

<style>
	.px-overlay {
		position: absolute;
		inset: 0;
		z-index: 10;
		pointer-events: none;
		visibility: hidden;
	}

	.px-overlay.visible {
		visibility: visible;
	}

	.px-grid {
		position: absolute;
		inset: 0;
		display: grid;
		grid-template-columns: repeat(var(--cols), 1fr);
		grid-template-rows: repeat(var(--rows), 1fr);
	}

	.px-block {
		background: var(--accent, #d42f14);
		opacity: 0;
	}

	.px-block.corner-tl { border-top-left-radius: 5px; }
	.px-block.corner-tr { border-top-right-radius: 5px; }
	.px-block.corner-bl { border-bottom-left-radius: 5px; }
	.px-block.corner-br { border-bottom-right-radius: 5px; }

	.px-label {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.85rem;
		z-index: 1;
		opacity: 0;
		transition: opacity 0.25s ease-out;
	}

	.px-label.visible {
		opacity: 1;
	}

	.px-label span {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: rgba(255, 255, 255, 0.6);
	}

	.px-spinner {
		width: 22px;
		height: 22px;
		border: 1.5px solid rgba(255, 255, 255, 0.12);
		border-top-color: rgba(255, 255, 255, 0.8);
		border-radius: 50%;
		animation: px-spin 0.75s linear infinite;
	}

	@keyframes px-spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
