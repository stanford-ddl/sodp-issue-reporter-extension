# SODP Issue Reporter

A small Chrome extension for reporting transcript issues from Stanford Deliberate visualization pages. Select a transcript row, optionally add hearability or edit the error message, then copy a spreadsheet-ready row.

No LLM, backend, or automatic spreadsheet submission. This version works on admin visualization pages, not live-room video grids.

## Install

1. Open the [latest release](https://github.com/stanford-ddl/sodp-issue-reporter-extension/releases/latest) and download **sodp-issue-reporter-extension.zip** from **Assets**. Choose this packaged ZIP, not GitHub’s automatic “Source code” downloads.
2. Unzip it and keep the extracted folder somewhere permanent.
3. Open `chrome://extensions` in Chrome and turn on the **Developer mode** toggle in the upper-right corner.
4. Choose **Load unpacked**, then select the folder containing `manifest.json`.
5. Open or refresh a Stanford Deliberate visualization page. You need your usual platform access; the extension does not provide access to rooms.

Chrome lists the extension as **SODP Issue Reporter**.

## Use

1. Click a transcript row on a page such as `https://stanforddeliberate.org/admin/rooms/<id>/viz`.
2. Enter your reporter name once, either in the row popover or the extension’s toolbar popup.
3. Optionally choose **Hearability**. It starts blank for each newly selected row; **Other** allows a short description.
4. Review **Error / transcript**. It is prefilled with the parsed transcript or a detected error marker. You can replace it with a custom message or clear it.
5. Click **Copy A–H**.
6. Select column A of an empty destination row in your reporting sheet and paste. The eight cells fill columns A through H, so check the destination before pasting.

| Column | Value |
| --- | --- |
| A | Current visualization URL |
| B | Reporter name |
| C | Full selected transcript row, with whitespace normalized |
| D | Hearability, blank unless selected |
| E | Speaker screen name, without the “(Interrupting)” suffix |
| F | Relative timestamp from the transcript |
| G | Editable error or transcript text |
| H | Live-room URL from the visualization page’s heading; blank if unavailable or ambiguous |

Column G defaults to `[Transcript Missing]` or `[Audio Corrupted]` when that marker is present; otherwise it uses the transcript text. Clearing the field leaves G blank. Selecting a different row resets both G and hearability to that row’s defaults.

The popover stays anchored while you edit, change hearability, or copy. If its contents outgrow the available space, scroll inside it. It follows the selected row when the page scrolls and stays within the viewport when the window resizes.

Copy one transcript row at a time. **Close** or **Escape** dismisses the popover. Links and ordinary text selection remain available. If the visualization page includes a room slug such as `(/demo-en-a)`, a **Live room** button appears in the **upper-right of the viz page**. Clicking it opens that room’s page in a new tab. The button stays hidden if no room slug is found. The button and column H use the same explicit `(/room-slug)` in the visualization page’s first `h3` heading. If the heading contains no valid slug or conflicting slugs, H stays blank and the button is hidden. The extension does not search transcript/body text, guess from the numeric room ID, or check a lookup sheet. It constructs the room URL on the same website; it does not verify that the destination exists. Hover over the button to check its URL before opening it.

## Update

Unpacked extensions do not update automatically from GitHub.

Download **sodp-issue-reporter-extension.zip** from the [latest release](https://github.com/stanford-ddl/sodp-issue-reporter-extension/releases/latest) and unzip the new version. Replace the files in the same installed folder, then click **Reload** on the extension’s card at `chrome://extensions`. Refresh any open visualization tabs afterward. Keeping the same installed folder helps preserve the extension’s identity and saved settings.

## Privacy and permissions

- **Storage:** remembers your reporter name in Chrome’s sync storage. Chrome may sync it across browsers signed into the same account, depending on your sync settings.
- **Clipboard access:** writes the eight-cell row when you click **Copy A–H**. The extension does not read your clipboard.
- **Page access:** the content script runs only on Stanford Deliberate admin visualization URLs.

The extension does not send reports to a server or write to a spreadsheet. Reports leave the page through your clipboard and wherever you choose to paste them. Clipboard history or sync features on your device may retain copied content; follow your organization’s rules for participant information.

The copied URL includes its current query string and fragment. Review copied content before sharing it outside the intended reporting sheet.

## Formatting and limits

Tabs and line breaks within cells are flattened to spaces so each copy stays on one spreadsheet row. Quotes use TSV escaping. Values that look like spreadsheet formulas are prefixed with an apostrophe to treat them as text; some destinations may display that apostrophe.

Hearability is a human judgment, not inferred from the transcript. The parser depends on the platform’s transcript table structure, so platform changes may require an extension update. Check the selected speaker, time, and message before reporting.

## Development and tests

The release ZIP contains only the extension’s runtime files and this README. Development tests remain in the source repository.

No build step is required to run the source. Load the repository folder directly as an unpacked extension. To create the minimal release ZIP, run `python3 scripts/package_release.py`; it writes `dist/sodp-issue-reporter-extension.zip`.

Run the JavaScript checks with Node.js:

```sh
node --check content.js
node --check clipboard.js
node --check popup.js
node --test tests/clipboard.test.cjs
```

`tests/browser_smoke.py` and `tests/positioning_smoke.py` require Python, Playwright, and a compatible Chromium installation. Run them with your configured Python environment. Set `CHROMIUM_EXECUTABLE` to an existing Chrome for Testing binary if Playwright’s default browser is unavailable.

The browser test loads the real unpacked extension in a disposable profile and intercepts page requests with synthetic transcript HTML. It covers native clipboard writing and pasting, editable G, optional hearability, successive row selection, reporter-name persistence, TSV safety, and basic UI behavior. It does not access an actual room or spreadsheet. The test uses the system clipboard and overwrites its current contents with synthetic test data.

`tests/positioning_smoke.py` checks that repeated Other changes, textarea resizing, internal scrolling, and validation keep the popover in place. It also covers page scrolling, window resizing, short/narrow viewports, and closing/reopening or selecting a new row. It uses synthetic pages and does not touch the clipboard.

The earlier A–G clipboard workflow has also been manually tested on the live platform. The new column H is covered by fixture tests and still needs a live check. Automated tests use fixtures, so recheck the live page after platform or extension changes.
