import assert from "node:assert/strict";
import { test } from "node:test";

process.env.NODE_ENV = "development";
process.env.GEMINI_API_KEY = "test-key";
process.env.GEMINI_MODEL = "test-model";
process.env.GEMINI_FALLBACK_MODELS = "";
process.env.SAFETY_GATEWAY_URL = "http://127.0.0.1:8765";

const original = "我的電話是 0912345678";
const sanitized = "我的電話是 <PHONE_NUMBER_1>";
let modelRequests = [];

globalThis.fetch = async (input, init) => {
  const url = String(input);
  const body = JSON.parse(init.body);
  if (url.endsWith("/api/sanitize")) {
    const blocked = body.text.includes("危險內容");
    return Response.json({
      blocked,
      child_message: blocked ? "已攔截" : null,
      processed_text: body.text.replaceAll("0912345678", "<PHONE_NUMBER_1>"),
      entities: [],
    });
  }
  if (url.endsWith("/api/moderate-output")) {
    return Response.json({ blocked: false, child_message: null, processed_text: body.text, entities: [] });
  }
  if (url.includes("generativelanguage.googleapis.com")) {
    modelRequests.push(body);
    return Response.json({ candidates: [{ content: { role: "model", parts: [{ text: "收到" }] } }] });
  }
  throw new Error(`Unexpected request: ${url}`);
};

const { POST } = await import("../app/api/chat/completions/route.ts");

async function chat(messages, extra = {}) {
  modelRequests = [];
  return POST(new Request("http://localhost/api/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId: "test-session", messages, googleSearch: false, ...extra }),
  }));
}

if (process.env.PARENT_APPROVAL_DEMO === "false") {
  test("disabled demo rejects requests to send original PII", async () => {
    const response = await chat([{ role: "user", content: original }], { parentApprovedDemo: true });
    assert.equal(response.status, 403);
    assert.equal(modelRequests.length, 0);
  });
} else {
  test("only the approved latest turn reaches the model without PII masking", async () => {
    const response = await chat([
      { role: "user", content: original },
      { role: "assistant", content: "你好" },
      { role: "user", content: original },
    ], { parentApprovedDemo: true });
    assert.equal(response.status, 200);
    assert.deepEqual(modelRequests[0].contents.map((turn) => turn.parts[0].text), [sanitized, "你好", original]);
  });

  test("unapproved messages still reach the model masked", async () => {
    const response = await chat([{ role: "user", content: original }]);
    assert.equal(response.status, 200);
    assert.equal(modelRequests[0].contents[0].parts[0].text, sanitized);
  });

  test("approval does not bypass content safety", async () => {
    const response = await chat([{ role: "user", content: `${original} 危險內容` }], { parentApprovedDemo: true });
    assert.equal(response.status, 200);
    assert.equal((await response.json()).choices[0].message.content, "已攔截");
    assert.equal(modelRequests.length, 0);
  });

  test("approval is not available to the writing profile", async () => {
    const response = await chat([{ role: "user", content: original }], { parentApprovedDemo: true, profile: "writing" });
    assert.equal(response.status, 403);
    assert.equal(modelRequests.length, 0);
  });
}
