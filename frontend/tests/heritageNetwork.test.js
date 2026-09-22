import test from "node:test";
import assert from "node:assert/strict";
import { createNetworkExplorer } from "../src/components/heritageNetworkState.js";

const payload = (id) => ({ root: { document_id: id }, branches: [] });
const initial = { question: "경복궁" };

test("failed node retries that node and commits history only on success", async () => {
  const calls = [];
  let fail = true;
  const explorer = createNetworkExplorer(async (target) => {
    calls.push(target);
    if (target.document_id === "B" && fail) throw new Error("offline");
    return payload(target.document_id || "A");
  }, initial);
  await explorer.open();
  await explorer.select("B");
  assert.equal(explorer.getSnapshot().data.root.document_id, "A");
  assert.equal(explorer.getSnapshot().history.length, 0);
  fail = false;
  await explorer.retry();
  assert.deepEqual(calls.at(-1), { document_id: "B" });
  assert.equal(explorer.getSnapshot().data.root.document_id, "B");
  assert.deepEqual(explorer.getSnapshot().history, [initial]);
});

test("failed back preserves history and successful retry removes it once", async () => {
  let fail = false;
  const explorer = createNetworkExplorer(async (target) => {
    if (target.question && fail) throw new Error("offline");
    return payload(target.document_id || "A");
  }, initial);
  await explorer.open();
  await explorer.select("B");
  fail = true;
  await explorer.back();
  assert.deepEqual(explorer.getSnapshot().history, [initial]);
  assert.equal(explorer.getSnapshot().data.root.document_id, "B");
  fail = false;
  await explorer.retry();
  assert.equal(explorer.getSnapshot().history.length, 0);
  assert.equal(explorer.getSnapshot().data.root.document_id, "A");
});

test("late response cannot replace a newer selection", async () => {
  const pending = {};
  const explorer = createNetworkExplorer((target) => new Promise((resolve) => { pending[target.document_id] = resolve; }), initial);
  const first = explorer.select("B");
  const second = explorer.select("C");
  pending.C(payload("C"));
  await second;
  pending.B(payload("B"));
  await first;
  assert.equal(explorer.getSnapshot().data.root.document_id, "C");
});

test("unmounted answer ignores its pending response", async () => {
  let finish;
  const explorer = createNetworkExplorer(() => new Promise((resolve) => { finish = resolve; }), initial);
  const promise = explorer.open();
  explorer.cancel();
  finish(payload("old"));
  await promise;
  assert.equal(explorer.getSnapshot().data, null);
});

test("choice screen is preserved in back history", async () => {
  const choice = { requires_selection: true, candidates: [{ document_id: "A" }, { document_id: "B" }] };
  const explorer = createNetworkExplorer(async (target) => target.question ? choice : payload(target.document_id), initial);
  await explorer.open();
  await explorer.select("B");
  await explorer.back();
  assert.equal(explorer.getSnapshot().data.requires_selection, true);
  assert.equal(explorer.getSnapshot().history.length, 0);
});
