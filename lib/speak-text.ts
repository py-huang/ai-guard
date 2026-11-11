export function toSpokenLine(source: string) {
  return source
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`[^`]+`/g, " ")
    .replace(/[#*_>~\[\]]/g, " ")
    .replace(/https?:\/\/\S+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function stopSpeaking() {
  if (typeof window === "undefined" || !window.speechSynthesis) {
    return;
  }
  window.speechSynthesis.cancel();
}

export function speakText(source: string) {
  if (typeof window === "undefined" || !window.speechSynthesis) {
    return false;
  }

  const text = toSpokenLine(source);
  if (!text) {
    return false;
  }

  stopSpeaking();
  window.speechSynthesis.speak(createUtterance(text));
  return true;
}

export function speakTextAsync(source: string, onEnergy?: (energy: number) => void) {
  return new Promise<boolean>((resolve) => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      resolve(false);
      return;
    }

    const text = toSpokenLine(source);
    if (!text) {
      resolve(false);
      return;
    }

    let started = false;
    const start = () => {
      if (started) {
        return;
      }
      started = true;
      window.speechSynthesis.removeEventListener("voiceschanged", start);
      stopSpeaking();
      const utterance = createUtterance(text);
      let energy = 0;
      let raf = 0;
      let settled = false;
      let boundarySeen = false;
      const keepAlive = window.setInterval(() => {
        if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume();
        }
      }, 4000);
      const finish = (ok: boolean) => {
        if (settled) {
          return;
        }
        settled = true;
        window.clearInterval(keepAlive);
        window.cancelAnimationFrame(raf);
        onEnergy?.(0);
        resolve(ok);
      };
      const pump = () => {
        if (boundarySeen) {
          energy *= 0.84;
        } else {
          energy = 0.32 + 0.68 * Math.abs(Math.sin(performance.now() / 150));
        }
        onEnergy?.(energy);
        raf = window.requestAnimationFrame(pump);
      };
      utterance.onstart = () => {
        energy = 0.7;
        raf = window.requestAnimationFrame(pump);
      };
      utterance.onboundary = () => {
        boundarySeen = true;
        energy = 1;
      };
      utterance.onend = () => finish(true);
      utterance.onerror = () => finish(false);
      window.speechSynthesis.speak(utterance);
      window.speechSynthesis.resume();
    };

    if (window.speechSynthesis.getVoices().length > 0) {
      start();
      return;
    }
    window.speechSynthesis.addEventListener("voiceschanged", start);
    window.setTimeout(start, 300);
  });
}

function createUtterance(text: string) {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-TW";
  utterance.rate = 0.95;
  const voices = window.speechSynthesis.getVoices();
  const voice = voices.find((item) => item.lang.startsWith("zh-TW")) || voices.find((item) => item.lang.startsWith("zh"));
  if (voice) {
    utterance.voice = voice;
  }
  return utterance;
}
