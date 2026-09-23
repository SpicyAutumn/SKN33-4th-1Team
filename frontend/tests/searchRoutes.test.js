import test from "node:test";
import assert from "node:assert/strict";
import { readSearchRoute, pushPath } from "../src/searchRoutes.js";
const id = "de5631ab-c5d4-48f7-8cf9-1ba9e0123456";
test("private and public routes resolve to separate endpoints", () => {
  assert.equal(readSearchRoute(`/search/${id}`).endpoint, `searches/${id}`);
  assert.equal(readSearchRoute(`/share/${id}/`).endpoint, `shared-searches/${id}`);
  for (const path of ["/", "/admin", "/search/bad", `/search/${id}/other`]) assert.equal(readSearchRoute(path), null);
});
test("navigation preserves history without duplicate entries and clears query/hash", () => {
  const calls = [];
  const browser = { location: { pathname: `/search/${id}`, search: "", hash: "" }, history: { pushState: (...args) => calls.push(args) } };
  pushPath(`/search/${id}`, browser);
  assert.equal(calls.length, 0);
  pushPath("/", browser);
  assert.deepEqual(calls[0], [{}, "", "/"]);
  browser.location.hash = "#top";
  pushPath(`/search/${id}`, browser);
  assert.equal(calls.length, 2);
});
