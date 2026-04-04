import {
  interpolateViridis,
  interpolatePlasma,
  interpolateInferno,
  interpolateMagma,
} from "d3-scale-chromatic";

export type ColormapName = "viridis" | "plasma" | "inferno" | "magma";

const LUT_SIZE = 256;

function hexToRgb(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  return [r, g, b];
}

function parseD3Color(color: string): [number, number, number] {
  if (color.startsWith("#")) return hexToRgb(color);
  const match = color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (match) {
    return [
      parseInt(match[1]) / 255,
      parseInt(match[2]) / 255,
      parseInt(match[3]) / 255,
    ];
  }
  return [0, 0, 0];
}

const interpolators: Record<ColormapName, (t: number) => string> = {
  viridis: interpolateViridis,
  plasma: interpolatePlasma,
  inferno: interpolateInferno,
  magma: interpolateMagma,
};

const lutCache = new Map<ColormapName, Float32Array>();

export function buildLUT(colormap: ColormapName = "viridis"): Float32Array {
  const cached = lutCache.get(colormap);
  if (cached) return cached;

  const lut = new Float32Array(LUT_SIZE * 3);
  const interpolate = interpolators[colormap];

  for (let i = 0; i < LUT_SIZE; i++) {
    const t = i / (LUT_SIZE - 1);
    const [r, g, b] = parseD3Color(interpolate(t));
    lut[i * 3] = r;
    lut[i * 3 + 1] = g;
    lut[i * 3 + 2] = b;
  }

  lutCache.set(colormap, lut);
  return lut;
}

export function valueToColor(
  value: number,
  lut: Float32Array,
): [number, number, number] {
  const clamped = Math.max(0, Math.min(1, value));
  const idx = Math.round(clamped * (LUT_SIZE - 1));
  return [lut[idx * 3], lut[idx * 3 + 1], lut[idx * 3 + 2]];
}

export function valuesToColorArray(
  values: number[],
  colormap: ColormapName = "viridis",
): Float32Array {
  const lut = buildLUT(colormap);
  const colors = new Float32Array(values.length * 3);

  for (let i = 0; i < values.length; i++) {
    const [r, g, b] = valueToColor(values[i], lut);
    colors[i * 3] = r;
    colors[i * 3 + 1] = g;
    colors[i * 3 + 2] = b;
  }

  return colors;
}

export function getColormapGradientStops(
  colormap: ColormapName = "viridis",
  steps = 10,
): string[] {
  const interpolate = interpolators[colormap];
  return Array.from({ length: steps }, (_, i) =>
    interpolate(i / (steps - 1)),
  );
}
