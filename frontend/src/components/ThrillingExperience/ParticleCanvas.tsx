import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const PARTICLE_COUNT = 3000;

function Particles({ scrollProgress }: { scrollProgress: number }) {
  const pointsRef = useRef<THREE.Points>(null);
  
  // Create geometry and initial positions
  const [positions, targetPositions] = React.useMemo(() => {
    const pos = new Float32Array(PARTICLE_COUNT * 3);
    const target = new Float32Array(PARTICLE_COUNT * 3);

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      // Random spread for Denial phase
      pos[i * 3] = (Math.random() - 0.5) * 10;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 10;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 10;

      // Target cluster/shape for Intelligence phase (e.g., a sphere or grid)
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos((Math.random() * 2) - 1);
      const r = 2 + Math.random(); 
      target[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      target[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      target[i * 3 + 2] = r * Math.cos(phi);
    }
    return [pos, target];
  }, []);

  useFrame((state) => {
    if (!pointsRef.current) return;
    const geom = pointsRef.current.geometry;
    const attr = geom.attributes.position as THREE.BufferAttribute;

    const arr = attr.array as Float32Array;
    
    // Lerp from random to structured shape between 0.25 and 0.5 progress
    const mixFactor = Math.max(0, Math.min(1, (scrollProgress - 0.2) / 0.3));

    // Mouse distortion
    const mouseX = (state.mouse.x * state.viewport.width) / 2;
    const mouseY = (state.mouse.y * state.viewport.height) / 2;

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const idx = i * 3;
      // Base blended position
      const bx = THREE.MathUtils.lerp(positions[idx], targetPositions[idx], mixFactor);
      const by = THREE.MathUtils.lerp(positions[idx + 1], targetPositions[idx + 1], mixFactor);
      const bz = THREE.MathUtils.lerp(positions[idx + 2], targetPositions[idx + 2], mixFactor);

      // Simple mouse repel if in Intelligence phase
      let dx = 0, dy = 0;
      if (mixFactor > 0.5) {
        const distSq = Math.pow(bx - mouseX, 2) + Math.pow(by - mouseY, 2);
        if (distSq < 4) {
          const force = (4 - distSq) / 4;
          dx = (bx - mouseX) * force * 2;
          dy = (by - mouseY) * force * 2;
        }
      }

      // Add gentle rotation or noise
      const time = state.clock.elapsedTime;
      const noise = Math.sin(time + i) * 0.05 * (1 - mixFactor);

      arr[idx] = bx + dx + noise;
      arr[idx + 1] = by + dy + noise;
      arr[idx + 2] = bz;
    }
    attr.needsUpdate = true;
    
    // Rotate entire field slightly 
    pointsRef.current.rotation.y = state.clock.elapsedTime * 0.1;
    pointsRef.current.rotation.x = state.clock.elapsedTime * 0.05;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.03}
        color={scrollProgress > 0.25 ? '#f5695b' : '#b796ac'} // Turns red in Intelligence
        transparent
        opacity={0.6 + scrollProgress * 0.4}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

export function ParticleCanvas({ scrollProgress }: { scrollProgress: number }) {
  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none' }}>
      <Canvas camera={{ position: [0, 0, 7], fov: 60 }}>
        <Particles scrollProgress={scrollProgress} />
      </Canvas>
      {/* Dynamic Grain Overlay */}
      <div 
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          opacity: Math.max(0, (scrollProgress - 0.25) * 0.5), // Increases opacity with scroll
          backgroundSize: '128px 128px',
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
          mixBlendMode: 'overlay',
          zIndex: 1,
        }}
      />
    </div>
  );
}
