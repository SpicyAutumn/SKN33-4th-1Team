const UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
const resultRoute = new RegExp(`^/(search|share)/(${UUID})/?$`, "i");

export function readSearchRoute(pathname) {
  const match = pathname.match(resultRoute);
  if (!match) return null;
  const [, kind, id] = match;
  return { kind: kind.toLowerCase(), id,
    endpoint: `${kind.toLowerCase() === "share" ? "shared-searches" : "searches"}/${id}` };
}

export function pushPath(path, browser = window) {
  if (browser.location.pathname + browser.location.search + browser.location.hash !== path) {
    browser.history.pushState({}, "", path);
  }
}
