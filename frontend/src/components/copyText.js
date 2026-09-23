export async function copyText(value, { clipboard = globalThis.navigator?.clipboard, document = globalThis.document } = {}) {
  try {
    if (clipboard?.writeText) {
      await clipboard.writeText(value);
      return;
    }
  } catch {
    // HTTP previews and browser permission policies can block this API.
  }

  if (!document?.body || typeof document.execCommand !== "function") {
    throw new Error("Clipboard is unavailable");
  }
  const field = document.createElement("textarea");
  field.value = value;
  field.setAttribute("readonly", "");
  field.style.position = "fixed";
  field.style.opacity = "0";
  document.body.appendChild(field);
  field.select();
  const copied = document.execCommand("copy");
  field.remove();
  if (!copied) throw new Error("Clipboard copy failed");
}
