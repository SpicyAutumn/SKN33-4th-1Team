import test from "node:test";
import assert from "node:assert/strict";
import { copyText } from "../src/components/copyText.js";

function fallbackDocument(copied = true) {
  const field = { style: {}, setAttribute() {}, select() {}, remove() { this.removed = true; } };
  return { body: { appendChild(item) { this.item = item; } }, createElement() { return field; }, execCommand(command) { this.command = command; return copied; }, field };
}

test("uses the browser clipboard when it is available", async () => {
  let value = "";
  await copyText("공유 링크", { clipboard: { writeText: async (text) => { value = text; } }, document: fallbackDocument() });
  assert.equal(value, "공유 링크");
});

test("falls back to a temporary text field when clipboard access is blocked", async () => {
  const document = fallbackDocument();
  await copyText("http://preview.example/share/1", { clipboard: { writeText: async () => { throw new Error("insecure"); } }, document });
  assert.equal(document.command, "copy");
  assert.equal(document.field.value, "http://preview.example/share/1");
  assert.equal(document.field.removed, true);
});
