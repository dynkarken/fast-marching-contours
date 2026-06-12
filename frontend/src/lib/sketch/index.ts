import type { SketchParams } from './presets';
import type { DoneMessage, ProgressMessage } from './sketchWorker';

export { SCRIBBLE_PRESETS, FLUID_PRESETS, WAVES_PRESETS, SKETCH_PRESETS } from './presets';
export type { SketchParams, SketchPreset, SketchStyle } from './presets';

const WORK_MAX = 1400; // working resolution, longest side

/** Run a sketch style on an image file in a Web Worker. Resolves to an SVG string.
 *  Same seed + params + image = identical output. */
export async function runSketch(
	file: File,
	params: SketchParams,
	seed: number,
	onProgress?: (done: number, total: number) => void
): Promise<string> {
	const bitmap = await createImageBitmap(file);
	const origWidth = bitmap.width;
	const origHeight = bitmap.height;
	const r = Math.min(1, WORK_MAX / Math.max(origWidth, origHeight));
	const W = Math.round(origWidth * r);
	const H = Math.round(origHeight * r);

	const canvas = document.createElement('canvas');
	canvas.width = W;
	canvas.height = H;
	const ctx = canvas.getContext('2d')!;
	ctx.drawImage(bitmap, 0, 0, W, H);
	bitmap.close();
	const { data } = ctx.getImageData(0, 0, W, H);

	return new Promise((resolve, reject) => {
		const worker = new Worker(new URL('./sketchWorker.ts', import.meta.url), { type: 'module' });
		worker.onmessage = (e: MessageEvent<ProgressMessage | DoneMessage>) => {
			if (e.data.type === 'progress') {
				onProgress?.(e.data.done, e.data.total);
			} else {
				worker.terminate();
				resolve(e.data.svg);
			}
		};
		worker.onerror = (err) => {
			worker.terminate();
			reject(new Error(err.message || 'Sketch worker failed'));
		};
		worker.postMessage(
			{ pixels: data, width: W, height: H, origWidth, origHeight, params, seed },
			[data.buffer]
		);
	});
}
