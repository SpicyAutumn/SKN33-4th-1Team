import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const component = async (name) => readFile(new URL(`../src/components/${name}`, import.meta.url), "utf8");

test("user report board renders all category labels and selected quote text", async () => {
  const source = await component("ErrorReportBoard.jsx");
  assert.match(source, /reportCategories\(report\)\.map/);
  assert.match(source, /report\.selected_quotes\?\.length\s*>\s*0/);
  assert.match(source, /“\{quote\.text\}”/);
});

test("admin report board renders all category labels and selected quote text", async () => {
  const source = await component("AdminErrorReportBoard.jsx");
  assert.match(source, /reportCategories\(report\)\.map/);
  assert.match(source, /report\.selected_quotes\?\.length\s*>\s*0/);
  assert.match(source, /“\{quote\.text\}”/);
});
