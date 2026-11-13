// Exactly one TSV row. Flatten embedded separators; quote literal quote marks.
// Treat untrusted transcript/reporter text as text, never spreadsheet formulas.
(function (root) {
  "use strict";
  function cell(value) {
    let text = String(value ?? "").replace(/\s+/g, " ").trim();
    if (/^[=+@-]/.test(text)) text = "'" + text;
    return text.includes('"') ? '"' + text.replaceAll('"', '""') + '"' : text;
  }
  function toTSV(values) {
    if (!Array.isArray(values) || values.length !== 8) throw new Error("Expected eight A–H cells");
    return values.map(cell).join("\t");
  }
  function roomSlugFromHeading(text) {
    const slugs = [...String(text ?? "").matchAll(/\(\/([a-z0-9][a-z0-9-]*)\)/gi)].map(match => match[1]);
    const unique = [...new Set(slugs)];
    return unique.length === 1 ? unique[0] : "";
  }
  const api = { cell, toTSV, roomSlugFromHeading };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.DDLClipboard = api;
})(globalThis);
