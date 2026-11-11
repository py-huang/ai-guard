import { pcmToWav } from "@/lib/audio-wav";

export const WATCH_WAVE_BARS = 23;

type WatchMic = {
  readLevels: () => number[];
  rms: () => number;
  capture: () => Blob;
  close: () => void;
};

export async function openWatchMic(): Promise<WatchMic> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
  });
  const AudioContextCtor = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  const context = new AudioContextCtor();
  if (context.state === "suspended") {
    await context.resume();
  }

  const source = context.createMediaStreamSource(stream);
  const analyser = context.createAnalyser();
  analyser.fftSize = 512;
  analyser.smoothingTimeConstant = 0.45;
  const processor = context.createScriptProcessor(4096, 1, 1);
  const silent = context.createGain();
  silent.gain.value = 0;
  const chunks: Float32Array[] = [];
  let lastRms = 0;

  processor.onaudioprocess = (event) => {
    const channel = event.inputBuffer.getChannelData(0);
    chunks.push(new Float32Array(channel));
    let sum = 0;
    for (let index = 0; index < channel.length; index += 1) {
      const sample = channel[index] ?? 0;
      sum += sample * sample;
    }
    lastRms = Math.sqrt(sum / channel.length);
  };

  source.connect(analyser);
  source.connect(processor);
  processor.connect(silent);
  silent.connect(context.destination);

  const freq = new Uint8Array(analyser.frequencyBinCount);
  let closed = false;

  return {
    rms: () => lastRms,
    readLevels: () => {
      analyser.getByteFrequencyData(freq);
      const start = 2;
      const end = Math.min(freq.length, 96);
      const width = (end - start) / WATCH_WAVE_BARS;
      const levels: number[] = [];
      for (let bar = 0; bar < WATCH_WAVE_BARS; bar += 1) {
        const from = Math.floor(start + bar * width);
        const to = Math.max(from + 1, Math.floor(start + (bar + 1) * width));
        let sum = 0;
        for (let bin = from; bin < to; bin += 1) {
          sum += freq[bin] ?? 0;
        }
        const raw = sum / (to - from) / 255;
        levels.push(Math.min(1, Math.pow(raw, 0.65) * 1.45));
      }
      return levels;
    },
    capture: () => {
      const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
      const merged = new Float32Array(total);
      let offset = 0;
      for (const chunk of chunks) {
        merged.set(chunk, offset);
        offset += chunk.length;
      }
      return pcmToWav(merged, context.sampleRate);
    },
    close: () => {
      if (closed) {
        return;
      }
      closed = true;
      processor.onaudioprocess = null;
      processor.disconnect();
      analyser.disconnect();
      source.disconnect();
      silent.disconnect();
      stream.getTracks().forEach((track) => track.stop());
      void context.close();
    },
  };
}
