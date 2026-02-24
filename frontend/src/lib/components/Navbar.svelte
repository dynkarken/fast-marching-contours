<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { gsap } from 'gsap';

	const items = [
		{ label: 'File'     },
		{ label: 'Edit'     },
		{ label: 'Generate' },
		{ label: 'View'     },
		{ label: 'Help'     },
	];

	let activeIndex = $state(2); // "Generate" active by default

	let navEl: HTMLElement;
	let fillEls: HTMLElement[] = [];
	let textEls: HTMLElement[] = [];

	// Black fill — text inverts to white on hover/active
	const C_ON   = '#f5f5f5';
	const C_REST = '#a0a0a0';

	type Edge = 'left' | 'right' | 'top' | 'bottom';

	function getEdge(e: MouseEvent): Edge {
		const el = e.currentTarget as HTMLElement;
		const r  = el.getBoundingClientRect();
		const x  = (e.clientX - r.left) / r.width  * 100;
		const y  = (e.clientY - r.top)  / r.height * 100;
		const m  = Math.min(x, 100 - x, y, 100 - y);
		if (m === x)       return 'left';
		if (m === 100 - x) return 'right';
		if (m === y)       return 'top';
		return 'bottom';
	}

	function wipeClip(edge: Edge): string {
		switch (edge) {
			case 'left':   return 'inset(0 100% 0 0)';
			case 'right':  return 'inset(0 0 0 100%)';
			case 'top':    return 'inset(0 0 100% 0)';
			case 'bottom': return 'inset(100% 0 0 0)';
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
			{ clipPath: 'inset(0 0 0 0)', duration: 0.34, ease: 'power2.out' },
		);
		gsap.to(textEls[i], { color: C_ON, duration: 0.18, ease: 'none' });
	}

	function onLeave(i: number, e: MouseEvent) {
		if (i === activeIndex) return;
		const edge = getEdge(e);
		gsap.killTweensOf(fillEls[i]);
		gsap.killTweensOf(textEls[i]);
		gsap.to(fillEls[i], { clipPath: wipeClip(edge), duration: 0.26, ease: 'power2.in' });
		gsap.to(textEls[i], { color: C_REST, duration: 0.14, ease: 'none' });
	}

	function onClick(i: number) {
		if (i === activeIndex) return;
		const prev = activeIndex;
		activeIndex = i;
		gsap.killTweensOf(fillEls[prev]);
		gsap.killTweensOf(textEls[prev]);
		gsap.to(fillEls[prev], { clipPath: 'inset(0 0 100% 0)', duration: 0.26, ease: 'power2.in' });
		gsap.to(textEls[prev], { color: C_REST, duration: 0.14, ease: 'none' });
	}

	// Live clock
	let clockStr = $state('');
	let clockInterval: ReturnType<typeof setInterval>;

	function tick() {
		const now   = new Date();
		const h     = now.getHours();
		const m     = now.getMinutes().toString().padStart(2, '0');
		const ampm  = h >= 12 ? 'PM' : 'AM';
		const h12   = h % 12 || 12;
		const days  = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
		const months= ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
		               'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
		clockStr = `${days[now.getDay()]} ${months[now.getMonth()]} ${now.getDate()}  ${h12}:${m} ${ampm}`;
	}

	onMount(() => {
		gsap.set(fillEls[activeIndex], { clipPath: 'inset(0 0 0 0)' });
		gsap.set(textEls[activeIndex], { color: C_ON });
		textEls.forEach((el, i) => {
			if (i !== activeIndex) gsap.set(el, { color: C_REST });
		});

		// Entrance
		gsap.from(navEl, { y: -36, opacity: 0, duration: 0.5, ease: 'power3.out', delay: 0.05 });

		// Clock
		tick();
		clockInterval = setInterval(tick, 30000);
	});

	onDestroy(() => {
		clearInterval(clockInterval);
	});
</script>

<nav class="taskbar" bind:this={navEl}>
	<!-- Brand mark -->
	<a class="brand" href="/" aria-label="fast marching contours home">
		<svg class="brand-icon" viewBox="0 0 14 12" fill="none" stroke="currentColor" aria-hidden="true">
			<rect x="0.75" y="0.75" width="12.5" height="8.5" rx="1.25" stroke-width="1.5"/>
			<line x1="4.5"  y1="9.25" x2="4.5"  y2="11.25" stroke-width="1.5"/>
			<line x1="9.5"  y1="9.25" x2="9.5"  y2="11.25" stroke-width="1.5"/>
			<line x1="3"    y1="11.25" x2="11"  y2="11.25" stroke-width="1.5"/>
		</svg>
		<span class="brand-name">fast-marching</span>
	</a>

	<span class="sep" aria-hidden="true">|</span>

	<!-- Menu items -->
	<ul class="menu-items">
		{#each items as item, i}
			<li>
				<button
					class="menu-item"
					onmouseenter={(e) => onEnter(i, e)}
					onmouseleave={(e) => onLeave(i, e)}
					onclick={() => onClick(i)}
				>
					<span class="fill" bind:this={fillEls[i]} aria-hidden="true"></span>
					<span class="label" bind:this={textEls[i]}>{item.label}</span>
				</button>
			</li>
		{/each}
	</ul>

	<!-- Clock -->
	<span class="clock" aria-live="polite">{clockStr}</span>
</nav>

<style>
	.taskbar {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 100;
		height: 2rem; /* 32px */
		background: var(--bg-window);
		border-bottom: 2px solid var(--border);
		display: flex;
		align-items: stretch;
		padding: 0 0.75rem;
		gap: 0;
	}

	/* Brand */
	.brand {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		text-decoration: none;
		color: var(--text);
		flex-shrink: 0;
		padding: 0 0.5rem 0 0;
	}

	.brand-icon {
		width: 14px;
		height: 12px;
		flex-shrink: 0;
		color: var(--text);
	}

	.brand-name {
		font-family: var(--font-mono);
		font-weight: 500;
		font-size: 0.62rem;
		letter-spacing: 0.04em;
		color: var(--text);
		white-space: nowrap;
	}

	.sep {
		display: flex;
		align-items: center;
		padding: 0 0.35rem;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--border-light);
		user-select: none;
	}

	/* Menu items */
	.menu-items {
		display: flex;
		align-items: stretch;
		list-style: none;
		height: 100%;
		flex: 1;
	}

	li {
		list-style: none;
		display: flex;
	}

	.menu-item {
		position: relative;
		overflow: hidden;
		display: flex;
		align-items: center;
		padding: 0 0.65rem;
		background: transparent;
		border: none;
		border-radius: 0;
		color: var(--text);
		cursor: pointer;
		height: 100%;
	}

	/* White fill — expands on hover/active, inverts text to black */
	.fill {
		position: absolute;
		inset: 0;
		background: var(--accent);
		clip-path: inset(0 100% 0 0);
		pointer-events: none;
	}

	.label {
		position: relative;
		z-index: 1;
		font-family: var(--font-mono);
		font-weight: 400;
		font-size: 0.6rem;
		letter-spacing: 0.06em;
		white-space: nowrap;
		line-height: 1;
	}

	/* Clock */
	.clock {
		display: flex;
		align-items: center;
		padding: 0 0.25rem 0 0.5rem;
		font-family: var(--font-mono);
		font-size: 0.58rem;
		letter-spacing: 0.04em;
		color: var(--text-dim);
		white-space: nowrap;
		flex-shrink: 0;
		border-left: 1px solid var(--border-light);
		margin-left: auto;
	}
</style>
