"use client";

import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

/**
 * Fullscreen GLSL shader background — an animated perspective grid with a
 * teal/violet aurora and a cursor light. Renders on the GPU as a single
 * fullscreen quad, so it stays cheap (capped DPR, one draw call).
 */

const vertexShader = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position, 1.0);
  }
`;

const fragmentShader = /* glsl */ `
  precision highp float;
  varying vec2 vUv;
  uniform float uTime;
  uniform vec2 uMouse;
  uniform float uAspect;

  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
  }
  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(
      mix(hash(i + vec2(0.0, 0.0)), hash(i + vec2(1.0, 0.0)), u.x),
      mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
      u.y
    );
  }
  float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 5; i++) {
      v += a * noise(p);
      p *= 2.0;
      a *= 0.5;
    }
    return v;
  }

  void main() {
    vec2 uv = vUv;
    vec2 p = (uv - 0.5);
    p.x *= uAspect;
    float t = uTime * 0.05;

    // --- Aurora flow ---
    float n1 = fbm(p * 2.2 + vec2(t, t * 0.6));
    float n2 = fbm(p * 3.4 - vec2(t * 0.8, t * 1.1));

    vec3 base = vec3(0.012, 0.020, 0.040);
    vec3 teal = vec3(0.176, 0.831, 0.749);
    vec3 violet = vec3(0.545, 0.361, 0.965);

    vec3 col = base;
    col += teal * smoothstep(0.40, 0.95, n1) * 0.32;
    col += violet * smoothstep(0.50, 1.0, n2) * 0.24;

    // --- Animated grid (panning toward viewer) ---
    vec2 grid = uv * vec2(46.0, 28.0);
    grid.y += uTime * 0.45;
    vec2 gp = fract(grid) - 0.5;
    float lineX = smoothstep(0.03, 0.0, abs(gp.x));
    float lineY = smoothstep(0.03, 0.0, abs(gp.y));
    float g = max(lineX, lineY);
    // Brighten grid near a "horizon" band, fade top & bottom
    float band = smoothstep(0.0, 0.45, uv.y) * smoothstep(1.0, 0.5, uv.y);
    col += teal * g * band * 0.15;

    // --- Cursor light ---
    vec2 m = uMouse;
    m.x = (m.x - 0.5) * uAspect + 0.5;
    vec2 pc = uv;
    pc.x = (pc.x - 0.5) * uAspect + 0.5;
    float md = distance(pc, m);
    col += teal * smoothstep(0.40, 0.0, md) * 0.18;
    col += violet * smoothstep(0.28, 0.0, md) * 0.08;

    // --- Vignette ---
    col *= smoothstep(1.25, 0.25, length(p));

    gl_FragColor = vec4(col, 1.0);
  }
`;

function ShaderPlane() {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const target = useRef(new THREE.Vector2(0.5, 0.5));
  const { size } = useThree();

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uMouse: { value: new THREE.Vector2(0.5, 0.5) },
      uAspect: { value: 1 },
    }),
    []
  );

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      target.current.set(e.clientX / window.innerWidth, 1 - e.clientY / window.innerHeight);
    };
    window.addEventListener("pointermove", onMove);
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  useFrame((state) => {
    uniforms.uTime.value = state.clock.elapsedTime;
    uniforms.uAspect.value = size.width / size.height;
    (uniforms.uMouse.value as THREE.Vector2).lerp(target.current, 0.04);
  });

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        ref={materialRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        uniforms={uniforms}
      />
    </mesh>
  );
}

export function ShaderBackground() {
  return (
    <Canvas
      className="!absolute inset-0"
      dpr={[1, 1.5]}
      gl={{ antialias: false, powerPreference: "high-performance" }}
      camera={{ position: [0, 0, 1] }}
    >
      <ShaderPlane />
    </Canvas>
  );
}
