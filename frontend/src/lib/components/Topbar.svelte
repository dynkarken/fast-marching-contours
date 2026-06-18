<script lang="ts">
	import { page } from '$app/state';
</script>

<nav class="topbar">
	<div class="brand">
		<em class="brand-soft">.soft</em>
		<span class="brand-name">CONTOURS</span>
	</div>
	<div class="topbar-nav">
		<a href="/" class="nav-link" class:active={page.url.pathname === '/'}>Contours</a>
		<a href="/husportraet" class="nav-link" class:active={page.url.pathname === '/husportraet'}>Husportræt</a>
	</div>
</nav>

<style>
	.topbar {
		flex-shrink: 0;
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.85rem 1.5rem;
		border-bottom: 1px solid var(--border-light);
	}

	.brand {
		display: inline-flex;
		align-items: center;
		gap: 0.2rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 0.2rem 0.5rem 0.25rem;
		line-height: 1;
	}

	.brand-soft {
		font-family: var(--font-serif);
		font-style: italic;
		font-size: 0.85rem;
	}

	.brand-name {
		font-family: var(--font-sans);
		font-weight: 700;
		font-size: 0.78rem;
		letter-spacing: 0.08em;
	}

	.topbar-nav {
		display: flex;
		gap: 1.2rem;
	}

	.nav-link {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-faint);
		text-decoration: none;
		transition: color 0.12s;
	}

	.nav-link:hover {
		color: var(--text);
	}

	.nav-link.active {
		color: var(--text);
	}
</style>
