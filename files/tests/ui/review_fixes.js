// Run with node; set NODE_PATH to the Playwright installation when needed.
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const { chromium } = require('playwright');
const html = fs.readFileSync(path.join(__dirname, '../../src/frontend.html'), 'utf8');
function extract(start, end) {
  const a = html.indexOf(start), b = html.indexOf(end, a + start.length);
  assert(a >= 0 && b > a, `source markers missing: ${start}`);
  return html.slice(a, b);
}
(async () => {
  const browser = await chromium.launch({headless: true,
    ...(process.env.CP_BROWSER ? {executablePath: process.env.CP_BROWSER} : {channel: 'msedge'})});
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.setContent('<ul id="project-list"></ul>');
    await page.evaluate(() => {
      window.API = '/api'; window.currentProject = 'normal';
      window._sortProjectsByOrder = p => p;
      window._saveCurrentListOrder = () => {};
      window.fetch = async () => ({json: async () => [
        {name: "O'Brien", description: ''},
        {name: 'normal', description: '<img src="data:,bad" onerror="window.markupExecuted=true">'}
      ]});
      window.deleteProject = name => { window.deletedName = name; };
      window.deleteProjectAndFiles = name => { window.filesDeletedName = name; };
      window.loadProject = name => { window.loadedName = name; };
    });
    await page.addScriptTag({content: extract('        async function loadProjects()', '        async function loadProject(name)')});
    await page.evaluate(() => loadProjects());
    await page.locator('.proj-item-del').nth(0).click();
    await page.locator('.proj-item-del').nth(1).click();
    assert.deepEqual(await page.evaluate(() => ({
      removed: window.deletedName, deleted: window.filesDeletedName,
      markup: window.markupExecuted === true,
      imageCount: document.querySelectorAll('#project-list img').length,
      inlineHandler: document.querySelector('.proj-item-del').getAttribute('onclick'),
      selected: window.loadedName || null
    })), {removed: "O'Brien", deleted: "O'Brien", markup: false, imageCount: 0, inlineHandler: null, selected: null});
    assert((await page.locator('#project-list').innerText()).includes('<img src='));
    await page.locator('.proj-item-name').first().click();
    assert.equal(await page.evaluate(() => window.loadedName), "O'Brien");
    console.log('PASS literal project text and apostrophe-safe action callbacks');

    const ids = ['xs-sgnum','xs-unitcell','xs-output','xs-res-lo','xs-res-hi','xs-shells','xs-nbatch','xs-reidx','xs-refdata'];
    await page.setContent(ids.map(id => `<input id="${id}">`).join('') +
      '<div id="xs-input-files"><div class="param-row"><input class="xs-input-file"></div></div>');
    await page.evaluate(() => {
      window.toggleState = {}; window._xsStrictAbs = false; window._xsFriedel = true; window._xsMerge = false;
      window._xsSetStrictAbs = v => window._xsStrictAbs = v;
      window._xsSetFriedel = v => window._xsFriedel = v;
      window._xsSetMerge = v => window._xsMerge = v;
      window._setToggleBtn = (k, v) => window.toggleState[k] = v;
      window.xsAddInputFile = () => document.getElementById('xs-input-files').insertAdjacentHTML(
        'beforeend', '<div class="param-row"><input class="xs-input-file"></div>');
    });
    await page.addScriptTag({content: extract('        let _xsInputBaseline', '        async function xsUpdateParams()') +
      extract('        function xsParseIntoParams(content)', '        async function xsAutoDetect()')});
    const params = await page.evaluate(() => {
      xsParseIntoParams('OUTPUT_FILE= merged.ahkl\nINPUT_FILE= a.hkl\nINCLUDE_RESOLUTION_RANGE= 50 2\nNBATCH= 4\nINPUT_FILE= b.hkl\nINCLUDE_RESOLUTION_RANGE= 50 3\nNBATCH= 8\n');
      const unchanged = xsCollectParamsDict();
      const fresh = xsCollectParamsDict(false);
      document.getElementById('xs-res-hi').value = '2.5';
      const edited = xsCollectParamsDict();
      return {unchanged, fresh, edited};
    });
    assert.deepEqual(params.unchanged.INPUT_FILE, ['a.hkl', 'b.hkl']);
    assert(!('INCLUDE_RESOLUTION_RANGE' in params.unchanged));
    assert(!('NBATCH' in params.unchanged));
    assert.equal(params.fresh.INCLUDE_RESOLUTION_RANGE, '50 3');
    assert.equal(params.fresh.NBATCH, '8');
    assert.equal(params.edited.INCLUDE_RESOLUTION_RANGE, '50 2.5');
    assert(!('NBATCH' in params.edited));
    assert.deepEqual(errors, []);
    console.log('PASS XSCALE saves preserve loaded per-dataset values and submit explicit edits');
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
