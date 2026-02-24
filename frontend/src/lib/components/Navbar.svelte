<script lang="ts">
	import { onMount } from 'svelte';
	import { gsap } from 'gsap';

	const items = [
		{ label: 'Home',      icon: false },
		{ label: 'Generate',  icon: false },
		{ label: 'Presets',   icon: false },
		{ label: 'About',     icon: false },
		{ label: 'Export',    icon: true  },
	];

	let activeIndex = $state(0);

	let navEl: HTMLElement;
	let fillEls: HTMLElement[] = [];
	let textEls: HTMLElement[] = [];

	// Colors — match CSS vars directly since GSAP can't read var()
	const C_ON    = '#ffffff'; // text sitting on fill
	const C_REST  = '#888888'; // dim resting text for inactive items

	type Edge = 'left' | 'right' | 'top' | 'bottom';

	/** Determine which edge a MouseEvent is closest to, relative to its target. */
	function getEdge(e: MouseEvent): Edge {
		const el = e.currentTarget as HTMLElement;
		const r  = el.getBoundingClientRect();
		const x  = (e.clientX - r.left) / r.width  * 100;
		const y  = (e.clientY - r.top)  / r.height * 100;
		const dl = x, dr = 100 - x, dt = y, db = 100 - y;
		const m  = Math.min(dl, dr, dt, db);
		if (m === dl) return 'left';
		if (m === dr) return 'right';
		if (m === dt) return 'top';
		return 'bottom';
	}

	/**
	 * The collapsed inset() clip-path for a given entry/exit edge.
	 * Enter: animate FROM this value TO 'inset(0 0 0 0)'.
	 * Leave: animate FROM 'inset(0 0 0 0)' TO this value.
	 */
	function wipeClip(edge: Edge): string {
		switch (edge) {
			case 'left':   return 'inset(0 100% 0 0)';   // fill slides in/out from left
			case 'right':  return 'inset(0 0 0 100%)';   // fill slides in/out from right
			case 'top':    return 'inset(0 0 100% 0)';   // fill slides in/out from top
			case 'bottom': return 'inset(100% 0 0 0)';   // fill slides in/out from bottom
		}
	}

	function onEnter(i: number, e: MouseEvent) {
		if (i === activeIndex) return;
		const edge = getEdge(e);
		gsap.killTweensOf(fillEls[i]);
		gsap.killTweensOf(textEls[i]);
		gsap.fromTo(
			fillEls[i],
			{ clipPath: wipeClip(edge) },
			{ clipPath: 'inset(0 0 0 0)', duration: 0.38, ease: 'power2.out' },
		);
		gsap.to(textEls[i], { color: C_ON, duration: 0.2, ease: 'none' });
	}

	function onLeave(i: number, e: MouseEvent) {
		if (i === activeIndex) return;
		const edge = getEdge(e);
		gsap.killTweensOf(fillEls[i]);
		gsap.killTweensOf(textEls[i]);
		gsap.to(fillEls[i], { clipPath: wipeClip(edge), duration: 0.28, ease: 'power2.in' });
		gsap.to(textEls[i], { color: C_REST, duration: 0.16, ease: 'none' });
	}

	function onClick(i: number) {
		if (i === activeIndex) return;
		const prev = activeIndex;
		activeIndex = i;
		gsap.killTweensOf(fillEls[prev]);
		gsap.killTweensOf(textEls[prev]);
		// No cursor event — collapse downward by default
		gsap.to(fillEls[prev], { clipPath: 'inset(0 0 100% 0)', duration: 0.28, ease: 'power2.in' });
		gsap.to(textEls[prev], { color: C_REST, duration: 0.16, ease: 'none' });
	}

	onMount(() => {
		// Active item: fully revealed, text white
		gsap.set(fillEls[activeIndex], { clipPath: 'inset(0 0 0 0)' });
		gsap.set(textEls[activeIndex], { color: C_ON });

		// All other items start at resting dim color
		textEls.forEach((el, i) => {
			if (i !== activeIndex) gsap.set(el, { color: C_REST });
		});

		// Nav entrance: slide down from above
		gsap.from(navEl, {
			y: -44,
			opacity: 0,
			duration: 0.6,
			ease: 'power3.out',
			delay: 0.1,
		});
	});
</script>

<nav class="nav-bar" bind:this={navEl}>
	<!-- Brand mark — mirrors the h1 typography at nav scale -->
	<a class="brand" href="/" aria-label="fast marching contours">
		<span class="brand-sans">fast marching</span>
		<em class="brand-serif">Contours</em>
	</a>

	<!-- Navigation items -->
	<ul class="nav-items">
		{#each items as item, i}
			<li>
				<button
					class="nav-item"
					onmouseenter={(e) => onEnter(i, e)}
					onmouseleave={(e) => onLeave(i, e)}
					onclick={() => onClick(i)}
				>
					<!-- Linear wipe fill — direction follows cursor entry/exit edge -->
					<span class="fill" bind:this={fillEls[i]} aria-hidden="true"></span>

					<!-- Label floats above fill via z-index -->
					<span class="label" bind:this={textEls[i]}>
						{#if item.icon}
							<svg class="icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" aria-hidden="true">
								<circle cx="8" cy="8" r="6.25" />
								<ellipse cx="8" cy="8" rx="2.75" ry="6.25" />
								<line x1="1.75" y1="8" x2="14.25" y2="8" />
							</svg>
						{/if}
						{item.label}
					</span>
				</button>
			</li>
		{/each}
	</ul>
</nav>

<style>
	/* Full-width masthead bar */
	.nav-bar {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 100;
		height: 2.75rem; /* 44px */
		background: var(--bg);
		border-bottom: 1px solid var(--border-light);
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 1.5rem;
	}

	/* Brand logotype — echoes the h1 at reduced scale */
	.brand {
		display: flex;
		align-items: baseline;
		gap: 0.45rem;
		text-decoration: none;
		color: inherit;
		flex-shrink: 0;
	}

	.brand-sans {
		font-family: var(--font-sans);
		font-weight: 700;
		font-size: 0.62rem;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text);
	}

	.brand-serif {
		font-family: var(--font-serif);
		font-style: italic;
		font-weight: 300;
		font-size: 0.92rem;
		color: var(--text-dim);
		line-height: 1;
	}

	/* Nav items list — flush height to fill the bar */
	.nav-items {
		display: flex;
		align-items: stretch;
		list-style: none;
		height: 100%;
	}

	li {
		list-style: none;
		display: flex;
	}

	/* Individual nav item — no visible pill border, fills full bar height */
	.nav-item {
		position: relative;
		overflow: hidden;
		display: flex;
		align-items: center;
		padding: 0 0.8rem;
		background: transparent;
		border: none;
		border-radius: 0;
		color: var(--text);
		cursor: pointer;
		height: 100%;
		/* No CSS transitions — GSAP owns all motion */
	}

	/* Animated fill — starts collapsed to the right, expands on hover/active */
	.fill {
		position: absolute;
		inset: 0;
		background: var(--text);
		clip-path: inset(0 100% 0 0);
		pointer-events: none;
	}

	/* Label text — DM Mono echoes hero-sub and loading-label styles */
	.label {
		position: relative;
		z-index: 1;
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		font-family: var(--font-mono);
		font-weight: 400;
		font-size: 0.595rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		line-height: 1;
		white-space: nowrap;
		/* color driven entirely by GSAP */
	}

	.icon {
		width: 0.85em;
		height: 0.85em;
		flex-shrink: 0;
		stroke-width: 1.35;
	}
</style>
