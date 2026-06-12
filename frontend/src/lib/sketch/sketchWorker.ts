/// <reference lib="webworker" />
// Image → plotter-ready SVG, three styles:
//
//  scribble — greedy darkness-chasing polylines (à la DrawingBotV3 "Sketch Lines"):
//             find darkest pixel, repeatedly extend toward the direction passing
//             through the most remaining darkness, bleaching covered pixels.
//  fluid    — same chase, but direction change per step is limited and the result
//             is rendered as Catmull-Rom splines ("Sketch Sweeping Curves").
//  waves    — horizontal scanlines as sine waves whose frequency & amplitude follow
//             darkness (SquiggleDraw / "Hatch Sawtooth"). Single continuous path.

import type { SketchParams } from './presets';

interface StartMessage {
	pixels: Uint8ClampedArray; // RGBA, working resolution
	width: number;
	height: number;
	origWidth: number; // original image size (SVG output size)
	origHeight: number;
	params: SketchParams;
	seed: number; // same seed + params + image = identical output
}

// mulberry32 — tiny seeded PRNG, replaces Math.random for reproducibility
function mulberry32(seed: number) {
	let a = seed >>> 0;
	return () => {
		a |= 0;
		a = (a + 0x6d2b79f5) | 0;
		let t = Math.imul(a ^ (a >>> 15), 1 | a);
		t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

export interface ProgressMessage {
	type: 'progress';
	done: number;
	total: number;
}

export interface DoneMessage {
	type: 'done';
	svg: string;
	shapes: number;
}

self.onmessage = (e: MessageEvent<StartMessage>) => {
	const { pixels, width: W, height: H, origWidth, origHeight, params: P, seed } = e.data;
	const rand = mulberry32(seed ?? 1);

	// --- luminance buffer (bleached in place while drawing) ---
	const lum = new Float32Array(W * H);
	for (let i = 0, p = 0; i < lum.length; i++, p += 4) {
		let l = 0.2126 * pixels[p] + 0.7152 * pixels[p + 1] + 0.0722 * pixels[p + 2];
		l = (l - 127.5) * P.contrast + 127.5;
		lum[i] = Math.max(0, Math.min(255, l));
	}

	const scale = origWidth / W;
	const sx = (v: number) => (v * scale).toFixed(1);

	let lastProgress = 0;
	function progress(done: number, total: number) {
		const now = Date.now();
		if (now - lastProgress > 150) {
			lastProgress = now;
			self.postMessage({ type: 'progress', done, total } satisfies ProgressMessage);
		}
	}

	const pathStrings: string[] = P.style === 'waves' ? waves() : chase();

	const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg width="${origWidth}px" height="${origHeight}px" viewBox="0 0 ${origWidth} ${origHeight}" xmlns="http://www.w3.org/2000/svg">
<!-- style: ${P.style} | shapes: ${pathStrings.length} -->
<g style="fill:none;stroke:rgb(49,43,43);stroke-width:${(P.strokeW * scale).toFixed(2)};stroke-linecap:round;stroke-linejoin:round;">
${pathStrings.join('\n')}
</g>
</svg>`;

	self.postMessage({ type: 'done', svg, shapes: pathStrings.length } satisfies DoneMessage);

	// ════════════════ scribble & fluid ════════════════

	function darkestStart() {
		// random sampling + greedy descent ≈ darkest remaining pixel
		let bx = 0,
			by = 0,
			bv = 256;
		for (let i = 0; i < 3000; i++) {
			const x = (rand() * W) | 0;
			const y = (rand() * H) | 0;
			const v = lum[y * W + x];
			if (v < bv) {
				bv = v;
				bx = x;
				by = y;
			}
		}
		let moved = true;
		while (moved) {
			moved = false;
			for (let dy = -1; dy <= 1; dy++)
				for (let dx = -1; dx <= 1; dx++) {
					const x = bx + dx,
						y = by + dy;
					if (x < 0 || y < 0 || x >= W || y >= H) continue;
					const v = lum[y * W + x];
					if (v < bv) {
						bv = v;
						bx = x;
						by = y;
						moved = true;
					}
				}
		}
		return { x: bx, y: by, v: bv };
	}

	function bestSegment(x: number, y: number, angle: number) {
		const dx = Math.cos(angle),
			dy = Math.sin(angle);
		let sum = 0,
			bestAvg = -1,
			bestT = 0;
		for (let t = 1; t <= P.maxLen; t++) {
			const px = Math.round(x + dx * t),
				py = Math.round(y + dy * t);
			if (px < 0 || py < 0 || px >= W || py >= H) break;
			sum += 255 - lum[py * W + px];
			if (t >= P.minLen) {
				const avg = sum / t;
				if (avg > bestAvg) {
					bestAvg = avg;
					bestT = t;
				}
			}
		}
		return { avg: bestAvg, t: bestT, dx, dy, angle };
	}

	function bleachLine(x0: number, y0: number, x1: number, y1: number) {
		const steps = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0)) | 0;
		for (let t = 0; t <= steps; t++) {
			const x = Math.round(x0 + ((x1 - x0) * t) / (steps || 1));
			const y = Math.round(y0 + ((y1 - y0) * t) / (steps || 1));
			const i = y * W + x;
			lum[i] = Math.min(255, lum[i] + P.bleach);
			if (x + 1 < W) lum[i + 1] = Math.min(255, lum[i + 1] + P.bleach * 0.35);
			if (x - 1 >= 0) lum[i - 1] = Math.min(255, lum[i - 1] + P.bleach * 0.35);
		}
	}

	function chase(): string[] {
		const out: string[] = [];
		const fluid = P.style === 'fluid';
		while (out.length < P.maxLines) {
			const s = darkestStart();
			if (255 - s.v < P.cutoff) break; // image exhausted
			let x = s.x,
				y = s.y;
			let heading = rand() * Math.PI * 2;
			const pts: number[] = [x, y];
			for (let k = 0; k < P.maxSegs; k++) {
				let best: ReturnType<typeof bestSegment> | null = null;
				for (let a = 0; a < P.tests; a++) {
					// fluid after the first segment: only gentle turns from current heading
					const angle =
						fluid && k > 0
							? heading + (rand() * 2 - 1) * P.maxTurn
							: rand() * Math.PI * 2;
					const c = bestSegment(x, y, angle);
					if (c.t > 0 && (!best || c.avg > best.avg)) best = c;
				}
				if (!best || best.avg < P.cutoff) break;
				const nx = x + best.dx * best.t,
					ny = y + best.dy * best.t;
				bleachLine(x, y, nx, ny);
				heading = best.angle;
				x = nx;
				y = ny;
				pts.push(Math.round(x), Math.round(y));
			}
			if (pts.length <= 2) break; // darkest spot can't grow a line: done
			out.push(fluid ? splinePath(pts) : linePath(pts));
			progress(out.length, P.maxLines);
		}
		return out;
	}

	function linePath(pts: number[]): string {
		let d = `M${sx(pts[0])} ${sx(pts[1])}`;
		for (let i = 2; i < pts.length; i += 2) d += ` L${sx(pts[i])} ${sx(pts[i + 1])}`;
		return `<path d="${d}"/>`;
	}

	// Catmull-Rom through all points, emitted as cubic Béziers
	function splinePath(pts: number[]): string {
		const n = pts.length / 2;
		if (n < 3) return linePath(pts);
		const px = (i: number) => pts[2 * Math.max(0, Math.min(n - 1, i))];
		const py = (i: number) => pts[2 * Math.max(0, Math.min(n - 1, i)) + 1];
		let d = `M${sx(px(0))} ${sx(py(0))}`;
		for (let i = 0; i < n - 1; i++) {
			const c1x = px(i) + (px(i + 1) - px(i - 1)) / 6;
			const c1y = py(i) + (py(i + 1) - py(i - 1)) / 6;
			const c2x = px(i + 1) - (px(i + 2) - px(i)) / 6;
			const c2y = py(i + 1) - (py(i + 2) - py(i)) / 6;
			d += ` C${sx(c1x)} ${sx(c1y)} ${sx(c2x)} ${sx(c2y)} ${sx(px(i + 1))} ${sx(py(i + 1))}`;
		}
		return `<path d="${d}"/>`;
	}

	// ════════════════ waves ════════════════

	function waves(): string[] {
		const spacing = P.rowSpacing;
		const halfAmp = spacing * 0.48;
		const rows = Math.max(1, Math.floor(H / spacing));
		// darkness at (x, rowY), averaged over a small vertical band for stability
		const band = Math.max(1, Math.round(spacing / 3));
		const darkness = (x: number, y: number) => {
			let s = 0,
				c = 0;
			for (let dy = -band; dy <= band; dy += band) {
				const yy = y + dy;
				if (yy < 0 || yy >= H) continue;
				s += 255 - lum[yy * W + x];
				c++;
			}
			return s / c / 255; // 0..1
		};

		// One continuous boustrophedon path: rows linked at alternating edges.
		let d = '';
		let phase = 0;
		for (let r = 0; r < rows; r++) {
			const y0 = Math.round(spacing / 2 + r * spacing);
			if (y0 >= H) break;
			const ltr = r % 2 === 0;
			// emitted points, with collinear-point decimation to keep the SVG lean
			let lastX = -1,
				lastY = -1,
				prevX = -1,
				prevY = -1,
				havePrev = false;
			const emit: string[] = [];
			const flushPrev = () => {
				if (havePrev) emit.push(`L${sx(prevX)} ${sx(prevY)}`);
				havePrev = false;
			};
			for (let step = 0; step < W; step++) {
				const x = ltr ? step : W - 1 - step;
				const dk = darkness(x, y0);
				const freq = P.minFreq + (P.maxFreq - P.minFreq) * Math.pow(dk, 1.2);
				const amp = halfAmp * (P.ampFloor + (1 - P.ampFloor) * Math.pow(dk, 0.85));
				phase += freq;
				const y = y0 + amp * Math.sin(phase);
				if (step === 0) {
					emit.push(`${d === '' ? 'M' : 'L'}${sx(x)} ${sx(y)}`);
					lastX = x;
					lastY = y;
					continue;
				}
				// decimation: drop the middle point of near-collinear triples
				if (havePrev) {
					const cross = (prevX - lastX) * (y - lastY) - (prevY - lastY) * (x - lastX);
					if (Math.abs(cross) < 0.35) {
						prevX = x;
						prevY = y; // extend, middle point absorbed
						continue;
					}
					emit.push(`L${sx(prevX)} ${sx(prevY)}`);
					lastX = prevX;
					lastY = prevY;
				}
				prevX = x;
				prevY = y;
				havePrev = true;
			}
			flushPrev();
			d += emit.join(' ') + ' ';
			progress(r + 1, rows);
		}
		return [`<path d="${d.trim()}"/>`];
	}
};
