import * as Tone from 'tone';

/**
 * AudioEngine encapsulating Tone.js logic for the Thrilling Experience.
 * It manages the heartbeat, synth pad, and glitch noises.
 */
class AudioEngineManager {
  private hasStarted = false;
  private heartbeatObj: Tone.MembraneSynth | null = null;
  private heartbeatLoop: Tone.Loop | null = null;
  private padSynth: Tone.PolySynth | null = null;
  private autoFilter: Tone.AutoFilter | null = null;
  private noiseSynth: Tone.NoiseSynth | null = null;
  private dist: Tone.Distortion | null = null;

  async start() {
    if (this.hasStarted) return;
    await Tone.start();
    this.hasStarted = true;

    // Heartbeat setup
    this.heartbeatObj = new Tone.MembraneSynth({
      pitchDecay: 0.05,
      octaves: 2,
      oscillator: { type: 'sine' },
      envelope: { attack: 0.001, decay: 0.4, sustain: 0.01, release: 1.4, attackCurve: 'exponential' }
    }).toDestination();
    this.heartbeatObj.volume.value = -12;

    this.heartbeatLoop = new Tone.Loop((time) => {
      // 2 quick beats
      this.heartbeatObj?.triggerAttackRelease('C1', '8n', time);
      this.heartbeatObj?.triggerAttackRelease('C1', '8n', time + 0.2);
    }, '1m');

    // Synth Pad setup
    this.autoFilter = new Tone.AutoFilter('4n').toDestination().start();
    this.padSynth = new Tone.PolySynth(Tone.Synth, {
      oscillator: { type: 'sawtooth' },
      envelope: { attack: 2, decay: 1, sustain: 0.5, release: 3 }
    }).connect(this.autoFilter);
    this.padSynth.volume.value = -Infinity; // start silent
    this.padSynth.triggerAttack(['C3', 'E3', 'G3', 'B3']); // constant drone

    // Noise/Glitch setup
    this.dist = new Tone.Distortion(0.8).toDestination();
    this.noiseSynth = new Tone.NoiseSynth({
      noise: { type: 'pink' },
      envelope: { attack: 0.005, decay: 0.1, sustain: 0 }
    }).connect(this.dist);
    this.noiseSynth.volume.value = -Infinity;

    Tone.Transport.bpm.value = 60; // 60 BPM start
    Tone.Transport.start();
    this.heartbeatLoop.start(0);
  }

  updateScroll(progress: number) {
    if (!this.hasStarted) return;

    // Map progress (0-1) to phases and audio params
    // 0.0 - 0.25: Denial
    // 0.25 - 0.50: Intelligence
    // 0.50 - 0.80: Intervention
    // 0.80 - 1.0: Control

    let bpm = 60;
    let padVol = -Infinity;
    let distWet = 0;

    if (progress < 0.25) {
      bpm = 60 + (progress / 0.25) * 10; // 60 -> 70
      padVol = -Infinity;
    } else if (progress < 0.5) {
      const localProg = (progress - 0.25) / 0.25;
      bpm = 70 + localProg * 40; // 70 -> 110
      padVol = -40 + localProg * 28; // Fade in -40 -> -12
      distWet = localProg * 0.5;
    } else if (progress < 0.8) {
      const localProg = (progress - 0.5) / 0.3;
      bpm = 110 + localProg * 50; // 110 -> 160
      padVol = -12 + localProg * 6; // -12 -> -6
      distWet = 0.5 + localProg * 0.5; // up to 1.0
    } else {
      bpm = 160 - ((progress - 0.8) / 0.2) * 90; // Drops to 70
      padVol = -6 - ((progress - 0.8) / 0.2) * 50; // Fade out
      distWet = 1.0 - ((progress - 0.8) / 0.2) * 1.0;
    }

    Tone.Transport.bpm.rampTo(bpm, 0.1);
    if (this.padSynth) this.padSynth.volume.rampTo(padVol, 0.1);
    if (this.dist) this.dist.wet.rampTo(distWet, 0.1);
  }

  triggerGlitch() {
    if (this.hasStarted && this.noiseSynth) {
      if (this.noiseSynth.volume.value === -Infinity) {
        this.noiseSynth.volume.value = -10;
      }
      this.noiseSynth.triggerAttackRelease('16n');
    }
  }

  stop() {
    if (!this.hasStarted) return;
    this.heartbeatLoop?.stop();
    this.padSynth?.releaseAll();
    Tone.Transport.stop();
    this.hasStarted = false;
  }
}

export const AudioEngine = new AudioEngineManager();
