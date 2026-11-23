// Next.js calls register() once when a server instance starts, before it takes requests.
export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") {
    return;
  }
  const { startVoiceRecordServices } = await import("@/lib/server/voice-startup");
  await startVoiceRecordServices();
}
