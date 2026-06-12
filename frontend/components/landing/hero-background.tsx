"use client";

import dynamic from "next/dynamic";
import { AnimatedGridBackground } from "@/components/animated-grid-background";

/**
 * Layered hero background:
 *  1. WebGL shader: aurora FBM noise + animated perspective grid + cursor light
 *  2. CSS/Motion:   drifting blur orbs + floating particles + scan line
 *
 * Both layers render once the shader's up. While it's still loading (or if WebGL
 * isn't available at all) the CSS layer carries the background on its own, so the
 * hero is never just empty.
 */
const ShaderBackground = dynamic(
  () => import("./shader-background").then((m) => m.ShaderBackground),
  // while the GPU shader hydrates, show the full animated grid instead
  { ssr: false, loading: () => <AnimatedGridBackground scan orbs particles={28} /> }
);

export function HeroBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      {/* ── Layer 1: GPU shader ──────────────────────────────────────────── */}
      {/* Aurora flow + animated perspective grid + cursor light.            */}
      {/* Dialed back to 80% so the CSS orbs below bleed through.            */}
      <div className="absolute inset-0 opacity-80">
        <ShaderBackground />
      </div>

      {/* ── Layer 2: CSS / Motion ────────────────────────────────────────── */}
      {/* Large drifting glow orbs (teal + violet), floating teal particles, */}
      {/* and a scanning horizontal beam.                                    */}
      {/* grid=false — the shader already draws an animated perspective grid */}
      {/* so we skip the static CSS lines to avoid visual doubling.          */}
      <AnimatedGridBackground
        grid={false}
        orbs
        scan
        particles={28}
      />

      {/* ── Layer 3: Dots texture ────────────────────────────────────────── */}
      {/* Subtle radial-masked dot grid for extra depth.                     */}
      <div className="absolute inset-0 dots-overlay opacity-40" />

      {/* ── Layer 4: Legibility gradients ───────────────────────────────── */}
      <div className="absolute inset-0 bg-gradient-to-b from-ink-950/30 via-transparent to-ink-950" />
      <div className="absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-ink-950 to-transparent" />
    </div>
  );
}
