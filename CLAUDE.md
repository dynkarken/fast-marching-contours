# fast-marching-contours — Claude Guidelines

## Git discipline
- **Commit often** with descriptive, specific commit messages — e.g. `"Add cursor-direction fill animation to Navbar"`, not `"update stuff"`
- Each logical change (feature, fix, refactor) gets its own commit
- Never batch unrelated changes into a single commit

## Project overview
Photographic line-art generator using the Fast Marching Method for wavefront-based contour extraction.

## Stack
- **Backend**: Python / FastAPI (`backend/`), core algorithm in `ffm.py`
- **Frontend**: SvelteKit + Vite (`frontend/`), GSAP for all animations
- **Dev server**: `cd frontend && npm run dev` → `http://localhost:5173` (or next available port)

## Frontend conventions
- **Animations**: GSAP owns all motion — no competing CSS transitions on animated properties
- **Colors in GSAP**: CSS variables can't be read by GSAP directly; use hardcoded hex values that mirror the CSS vars (e.g. `#0c0c0c` for `--text`, `#ffffff` for `--bg`)
- **Svelte version**: Svelte 5 — use `$state`, `$effect`, `onMount`; avoid legacy `export let` reactivity where possible

## Key files
| Path | Purpose |
|------|---------|
| `frontend/src/app.css` | Global CSS variables (colors, fonts, radii) |
| `frontend/src/routes/+page.svelte` | Main app page |
| `frontend/src/lib/components/Navbar.svelte` | Fixed top nav with GSAP pill animations |
| `frontend/src/lib/components/SvgViewer.svelte` | SVG result viewer |
| `frontend/src/lib/components/ImageUpload.svelte` | Image upload control |
| `frontend/src/lib/components/PresetPicker.svelte` | Preset selector |
| `backend/` | FastAPI app, `/api/process` endpoint |
| `ffm.py` | Core Fast Marching Method algorithm |

## GSAP animation patterns
- Cursor-direction-aware fill: `clip-path: circle()` with origin set to the cursor's entry/exit position (see `Navbar.svelte`)
- Entrance animations: `gsap.from(el, { y: -48, opacity: 0, ... })` with short delays
- Always `gsap.killTweensOf(el)` before starting a new tween on the same element
