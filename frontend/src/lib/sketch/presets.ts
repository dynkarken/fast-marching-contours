export type SketchStyle = 'scribble' | 'fluid' | 'waves';

export interface SketchParams {
	style: SketchStyle;
	// shared
	contrast: number; // applied around midpoint before drawing
	strokeW: number; // stroke width in working px
	// scribble + fluid
	maxLines: number; // total polylines
	maxSegs: number; // segments per polyline
	minLen: number; // min segment length (working px)
	maxLen: number; // max segment length (working px)
	bleach: number; // luminance added under each drawn segment (0–255)
	cutoff: number; // min avg darkness to keep drawing (0–255)
	tests: number; // candidate angles per segment
	// fluid only
	maxTurn: number; // max direction change per segment (radians)
	// waves only
	rowSpacing: number; // distance between scanlines (working px)
	minFreq: number; // wave frequency in highlights (rad / px)
	maxFreq: number; // wave frequency in shadows (rad / px)
	ampFloor: number; // 0–1 fraction of full amplitude kept in highlights
}

export interface SketchPreset {
	id: string;
	desc: string;
	params: SketchParams;
}

const scribbleBase: SketchParams = {
	style: 'scribble',
	contrast: 1.0,
	strokeW: 1.0,
	maxLines: 6000,
	maxSegs: 60,
	minLen: 3,
	maxLen: 40,
	bleach: 55,
	cutoff: 60,
	tests: 16,
	maxTurn: Math.PI, // unrestricted
	rowSpacing: 0,
	minFreq: 0,
	maxFreq: 0,
	ampFloor: 0,
};

export const SCRIBBLE_PRESETS: SketchPreset[] = [
	{ id: 'A', desc: 'balanced · default scribble', params: { ...scribbleBase } },
	{
		id: 'B',
		desc: 'dense portrait · long travel',
		params: { ...scribbleBase, maxLines: 8000, maxSegs: 80, maxLen: 58, bleach: 45, cutoff: 50, contrast: 1.1 },
	},
	{
		id: 'C',
		desc: 'light & airy · sparse lines',
		params: { ...scribbleBase, maxLines: 3000, maxSegs: 40, bleach: 80, cutoff: 80 },
	},
	{
		id: 'D',
		desc: 'high contrast · deep shadows',
		params: { ...scribbleBase, contrast: 1.6, cutoff: 70 },
	},
	{
		id: 'E',
		desc: 'long scribbles · gestural',
		params: { ...scribbleBase, maxLines: 2500, maxSegs: 200, maxLen: 90 },
	},
	{
		id: 'F',
		desc: 'fine detail · short strokes',
		params: { ...scribbleBase, maxLines: 12000, maxLen: 24, minLen: 2, strokeW: 0.8 },
	},
];

const fluidBase: SketchParams = {
	...scribbleBase,
	style: 'fluid',
	minLen: 8,
	maxLen: 55,
	maxSegs: 90,
	maxLines: 5000,
	bleach: 50,
	cutoff: 55,
	tests: 12,
	maxTurn: 0.65, // ≈ 37° per step → gentle sweeps
};

export const FLUID_PRESETS: SketchPreset[] = [
	{ id: 'A', desc: 'balanced · gentle sweeps', params: { ...fluidBase } },
	{
		id: 'B',
		desc: 'very gentle · long arcs',
		params: { ...fluidBase, maxTurn: 0.4, minLen: 12, maxLen: 75, maxSegs: 140, maxLines: 3500 },
	},
	{
		id: 'C',
		desc: 'light & airy · sparse curves',
		params: { ...fluidBase, maxLines: 2500, bleach: 80, cutoff: 80 },
	},
	{
		id: 'D',
		desc: 'high contrast · deep shadows',
		params: { ...fluidBase, contrast: 1.6, cutoff: 70 },
	},
	{
		id: 'E',
		desc: 'flowing · near-continuous',
		params: { ...fluidBase, maxSegs: 300, maxLines: 1500, maxTurn: 0.5 },
	},
	{
		id: 'F',
		desc: 'fine detail · tight curves',
		params: { ...fluidBase, maxLines: 9000, minLen: 5, maxLen: 30, strokeW: 0.8, maxTurn: 0.9 },
	},
];

const wavesBase: SketchParams = {
	...scribbleBase,
	style: 'waves',
	rowSpacing: 7,
	minFreq: 0.12,
	maxFreq: 1.6,
	ampFloor: 0.12,
	strokeW: 1.0,
};

export const WAVES_PRESETS: SketchPreset[] = [
	{ id: 'A', desc: 'balanced · classic squiggle', params: { ...wavesBase } },
	{
		id: 'B',
		desc: 'fine lines · dense rows',
		params: { ...wavesBase, rowSpacing: 5, maxFreq: 2.0, strokeW: 0.8 },
	},
	{
		id: 'C',
		desc: 'bold rows · big waves',
		params: { ...wavesBase, rowSpacing: 11, maxFreq: 1.3, strokeW: 1.4 },
	},
	{
		id: 'D',
		desc: 'high contrast · sharp jumps',
		params: { ...wavesBase, contrast: 1.6 },
	},
	{
		id: 'E',
		desc: 'calm · low frequency',
		params: { ...wavesBase, maxFreq: 0.9, ampFloor: 0.05 },
	},
	{
		id: 'F',
		desc: 'electric · max frequency',
		params: { ...wavesBase, maxFreq: 2.6, minFreq: 0.2 },
	},
];

export const SKETCH_PRESETS = SCRIBBLE_PRESETS; // backwards-compat alias
