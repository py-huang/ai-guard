function spokenText(source: string) {
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

  const text = spokenText(source);
  if (!text) {
    return false;
  }

  stopSpeaking();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "zh-TW";
  utterance.rate = 0.95;
  const voices = window.speechSynthesis.getVoices();
  const voice = voices.find((item) => item.lang.startsWith("zh-TW")) || voices.find((item) => item.lang.startsWith("zh"));
  if (voice) {
    utterance.voice = voice;
  }
  window.speechSynthesis.speak(utterance);
  return true;
}
