const assert = require('node:assert/strict');
const { buildSync } = require('esbuild');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const compiled = buildSync({ absWorkingDir: root, entryPoints: ['src/components/HeritageLoading.jsx'], bundle: true, write: false, platform: 'node', format: 'cjs', jsx: 'automatic', loader: { '.css': 'empty' }, external: ['react', 'react/jsx-runtime'] }).outputFiles[0].text;
const mod = { exports: {} };
new Function('require', 'module', 'exports', compiled)(require, mod, mod.exports);
const html = renderToStaticMarkup(React.createElement(mod.exports.default));
assert.equal((html.match(/<path /g) || []).length, 28);
assert.equal((html.match(/class="selected-province"/g) || []).length, 1);
assert.match(html, /Natural Earth/);
assert.match(html, /사진 출처/);
assert.doesNotMatch(html, /<iframe/);
const photos = require('../src/data/heritagePhotos.json');
const regions = require('../src/data/heritagePreviewRegions.json');
const paths = require('../src/data/heritageProvincePaths.json');
for (const photo of photos) {
  const key = photo.id.replace('-nature', '');
  assert.ok(regions[key], key);
  assert.ok(paths.some(p => p.region === key), key);
}
console.log('PASS: production loader render, 28 boundaries, selected province, credits, all photo regions');