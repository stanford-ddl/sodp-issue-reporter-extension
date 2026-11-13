(() => {
"use strict";
const REPORTABLE_ROW_SELECTOR = "table.transcript tbody tr";
const HEARABILITY_OPTIONS = ["Fine", "Badly", "Nothing", "Unsure", "Other"];
let currentTarget = null;
let toolbar = null;
let toolbarAnchor = null;
let helperName = "";
let settingsReady = false;
chrome.storage.sync.get("settings").then(({ settings = {} }) => {
  helperName = cleanText(settings.helperName);
  settingsReady = true;
  if (toolbar && !toolbar.querySelector('[name="helperName"]').value) toolbar.querySelector('[name="helperName"]').value = helperName;
}).catch(() => { settingsReady = true; });
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "sync" || !changes.settings) return;
  helperName = cleanText(changes.settings.newValue?.helperName);
  if (toolbar && document.activeElement !== toolbar.querySelector('[name="helperName"]')) {
    toolbar.querySelector('[name="helperName"]').value = helperName;
  }
});
installLiveRoomButton();
setTimeout(installLiveRoomButton, 1000);
setTimeout(installLiveRoomButton, 3000);
document.addEventListener("click", (event) => {
  if (event.target.closest?.(".ddl-report-toolbar, .ddl-live-room-button")) return;
  // Preserve the page's links, media controls, and ordinary text selection/copy.
  if (event.target.closest?.("a, button, input, select, textarea, audio, video")) return;
  if (window.getSelection()?.toString()) return;
  const row = event.target.closest?.(REPORTABLE_ROW_SELECTOR);
  if (!row) { hideToolbar(); return; }
  if (row === currentTarget && toolbar) return;
  hideToolbar();
  currentTarget = row;
  row.classList.add("ddl-report-target");
  showToolbar();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") hideToolbar();
});
document.addEventListener("scroll", (event) => {
  // Editing/scrolling our own panel must never move its viewport anchor.
  if (toolbar?.contains(event.target)) return;
  repositionToolbar();
}, true);
window.addEventListener("resize", repositionToolbar);

function showToolbar() {
  installLiveRoomButton();
  toolbar = document.createElement("div");
  toolbar.className = "ddl-report-toolbar";
  toolbar.setAttribute("role", "region");
  toolbar.setAttribute("aria-label", "Copy transcript row for spreadsheet");
  toolbar.innerHTML = `<div class="ddl-report-heading"><strong>Copy row for sheet</strong><button type="button" class="ddl-close" aria-label="Close">×</button></div>
    <label>Reporter<input name="helperName" autocomplete="name" placeholder="Your name" maxlength="200"></label>
    <label>Hearability <span>(optional)</span><select name="hearability"><option value="">Leave blank</option>${HEARABILITY_OPTIONS.map(x => `<option>${x}</option>`).join("")}</select></label>
    <label class="ddl-other" hidden>Other hearability<input name="hearabilityOther" maxlength="200" placeholder="Describe what you heard"></label>
    <label>Error / transcript <span>(column G · editable)</span><textarea name="errorText" rows="3"></textarea></label>
    <button type="button" class="ddl-copy">Copy A–H</button>
    <p class="ddl-status" role="status">Paste into column A of the sheet.</p>`;
  toolbar.querySelector('[name="helperName"]').value = helperName;
  const extracted = extractLineParts(currentTarget);
  // Set text as a value, never HTML; reset only when opening a different row.
  toolbar.querySelector('[name="errorText"]').value = detectAutoError(extracted.transcriptText, currentTarget) || extracted.transcriptText;
  toolbar.querySelector(".ddl-close").addEventListener("click", hideToolbar);
  toolbar.querySelector('[name="hearability"]').addEventListener("change", () => {
    toolbar.querySelector(".ddl-other").hidden = toolbar.querySelector('[name="hearability"]').value !== "Other";
  });
  toolbar.querySelector(".ddl-copy").addEventListener("click", copySelectedRow);
  document.documentElement.append(toolbar);
  repositionToolbar();
}

function repositionToolbar() {
  if (!currentTarget || !toolbar) return;
  if (!currentTarget.isConnected) { hideToolbar(); return; }
  const rect = currentTarget.getBoundingClientRect();
  const margin = 8;
  if (!toolbarAnchor) {
    // Choose a side once per row. Content height changes must not flip sides,
    // reclamp the top, or move the controls out from under the pointer.
    const width = toolbar.offsetWidth;
    const height = toolbar.offsetHeight;
    const beside = rect.right + width + margin * 2 <= window.innerWidth;
    const left = beside ? rect.right + margin : Math.max(margin, Math.min(window.innerWidth - width - margin, rect.right - width));
    const above = rect.top - height - margin;
    const top = Math.max(margin, Math.min(window.innerHeight - height - margin, beside ? rect.top : (above >= margin ? above : rect.bottom + margin)));
    toolbarAnchor = { leftOffset: left - rect.right, topOffset: top - rect.top, height };
  }
  // Follow the row on page/ancestor scroll, but retain the original placement.
  // Use the opening height, not changing form content, to clamp the anchor.
  const left = Math.max(margin, Math.min(window.innerWidth - toolbar.offsetWidth - margin, rect.right + toolbarAnchor.leftOffset));
  const top = Math.max(margin, Math.min(window.innerHeight - toolbarAnchor.height - margin, rect.top + toolbarAnchor.topOffset));
  toolbar.style.left = `${left}px`;
  toolbar.style.top = `${top}px`;
  // Grow down from the stable top. Scroll inside the panel when space runs out.
  toolbar.style.maxHeight = `${Math.max(0, window.innerHeight - top - margin)}px`;
}

function hideToolbar() {
  currentTarget?.classList.remove("ddl-report-target");
  currentTarget = null;
  toolbar?.remove();
  toolbar = null;
  toolbarAnchor = null;
}

async function copySelectedRow() {
  const panel = toolbar;
  const row = currentTarget;
  if (!panel || !row?.isConnected) { hideToolbar(); return; }
  const status = panel.querySelector(".ddl-status");
  const name = cleanText(panel.querySelector('[name="helperName"]').value);
  if (!settingsReady) { status.textContent = "Loading reporter settings. Try again."; return; }
  if (!name) {
    status.textContent = "Add your name, then copy.";
    panel.querySelector('[name="helperName"]').focus();
    return;
  }
  const choice = panel.querySelector('[name="hearability"]').value;
  const hearability = choice === "Other" ? cleanText(panel.querySelector('[name="hearabilityOther"]').value) || "Other" : choice;
  const extracted = extractLineParts(row);
  const tsv = DDLClipboard.toTSV([
    location.href, name, cleanText(row.innerText || row.textContent), hearability,
    extracted.screenName, extracted.relativeTime,
    panel.querySelector('[name="errorText"]').value,
    getLiveRoomUrl()
  ]);
  const button = panel.querySelector(".ddl-copy");
  button.disabled = true;
  try {
    // Start the native clipboard write during this click's user activation.
    await navigator.clipboard.writeText(tsv);
    status.textContent = "Copied A–H. Paste into column A of the sheet.";
    helperName = name;
    try {
      const { settings = {} } = await chrome.storage.sync.get("settings");
      await chrome.storage.sync.set({ settings: { ...settings, helperName: name } });
    } catch (_) {
      status.textContent = "Copied A–H, but could not save your name for next time.";
    }
  } catch (_) {
    status.textContent = "Clipboard was blocked. Click Copy A–H to try again.";
  } finally {
    button.disabled = false;
  }
}

function installLiveRoomButton() {
  const liveRoomUrl = getLiveRoomUrl();
  const existing = document.querySelector(".ddl-live-room-button");
  if (!liveRoomUrl) { existing?.remove(); return; }
  if (existing) { existing.title = liveRoomUrl; return; }
  const button = document.createElement("button");
  button.type = "button";
  button.className = "ddl-live-room-button";
  button.setAttribute("aria-label", "Open live room in a new tab");
  const dot = document.createElement("span");
  dot.className = "ddl-live-room-dot";
  dot.setAttribute("aria-hidden", "true");
  const label = document.createElement("span");
  label.textContent = "Live room";
  const arrow = document.createElement("span");
  arrow.className = "ddl-live-room-arrow";
  arrow.setAttribute("aria-hidden", "true");
  arrow.textContent = "↗";
  button.append(dot, label, arrow);
  button.title = liveRoomUrl;
  button.addEventListener("click", () => {
    const currentUrl = getLiveRoomUrl();
    if (currentUrl) window.open(currentUrl, "_blank", "noopener");
    else button.remove();
  });
  document.documentElement.append(button);
}

function getLiveRoomUrl() {
  // Only trust the explicit room slug in the viz heading, never transcript/body text.
  const heading = document.querySelector("h3");
  if (!heading || heading.closest("table.transcript")) return "";
  const slug = DDLClipboard.roomSlugFromHeading(heading.innerText || heading.textContent);
  return slug ? `${location.origin}/${slug}` : "";
}

function extractLineParts(rowElement) {
  const cells = Array.from(rowElement.children);
  const textCell = cells[1];
  const speakerLabel = cleanText(textCell?.querySelector("b")?.textContent || "").replace(/:\s*$/, "");
  const screenName = speakerLabel.replace(/\s+\(Interrupting\)$/i, "");
  return {
    relativeTime: cleanText(cells[0]?.innerText || cells[0]?.textContent || ""),
    speakerLabel,
    screenName,
    transcriptText: extractTranscriptText(textCell, speakerLabel),
    confidence: cleanMetric(cells[2]),
    toxicity: cleanMetric(cells[3]),
    relevance: cleanMetric(cells[4])
  };
}

function extractTranscriptText(textCell, speakerLabel) {
  if (!textCell) return "";
  const clone = textCell.cloneNode(true);
  clone.querySelector("b")?.remove();
  clone.querySelectorAll("img").forEach((element) => element.remove());
  const text = cleanText(clone.textContent || "");
  if (text) return text;
  return speakerLabel || cleanText(textCell.textContent || "");
}

function detectAutoError(transcriptText, rowElement) {
  const text = `${transcriptText} ${rowElement.innerText || rowElement.textContent || ""}`;
  if (/\[Transcript Missing\]/i.test(text)) return "[Transcript Missing]";
  if (/\[Audio Corrupted\]?/i.test(text)) return "[Audio Corrupted]";
  return "";
}

function cleanMetric(cell) {
  return cleanText(cell?.innerText || cell?.textContent || "").replace(/[()]/g, "");
}

function cleanText(text) {
  return String(text ?? "").replace(/\s+/g, " ").trim();
}
})();
