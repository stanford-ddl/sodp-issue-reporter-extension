const statusEl = document.querySelector("#status");
const input = document.querySelector("#helperName");
const save = document.querySelector("#save");
chrome.storage.sync.get("settings").then(({ settings = {} }) => {
  input.value = settings.helperName || "";
  statusEl.textContent = input.value ? `Reporting as ${input.value}.` : "Add your name once, here or on the viz page.";
  save.disabled = false;
}).catch(() => { statusEl.textContent = "Could not load settings. Reopen the popup to retry."; });
save.addEventListener("click", async () => {
  const helperName = input.value.replace(/\s+/g, " ").trim();
  if (!helperName) { statusEl.textContent = "Enter your name first."; input.focus(); return; }
  save.disabled = true;
  try {
    const { settings = {} } = await chrome.storage.sync.get("settings");
    await chrome.storage.sync.set({ settings: { ...settings, helperName } });
    statusEl.textContent = `Reporting as ${helperName}.`;
  } catch (_) { statusEl.textContent = "Could not save. Try again."; }
  finally { save.disabled = false; }
});
