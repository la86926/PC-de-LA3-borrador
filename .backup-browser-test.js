const { chromium } = require('playwright');
const fs = require('fs');
const assert = require('assert');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ serviceWorkers: 'block' });
  const page = await context.newPage();
  const base = 'http://127.0.0.1:8000/';

  async function open(path) {
    await page.goto(base + path, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => !!window.PCBackupTools, null, { timeout: 15000 });
  }

  await open('index1.html');

  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem('wp_ultimo', '7');
    localStorage.setItem('wp2_ultimo', '9');
    localStorage.setItem('wp_sound', '0');
    localStorage.setItem('wp2_sound', '0');
    localStorage.setItem('pc_modo', 'oscuro');
    localStorage.setItem('pc_tablero_1', 'lavanda');
    localStorage.setItem('pc_tablero_2', 'menta');
    localStorage.setItem('pc_favs', JSON.stringify(['lavanda', 'menta']));
    localStorage.setItem('wp_probe', 'alpha');
    localStorage.setItem('wp2_probe', 'beta');
    localStorage.setItem('pc_probe', 'gamma');
    sessionStorage.setItem('wp_session_probe', 'uno');
    sessionStorage.setItem('wp2_session_probe', 'dos');
    sessionStorage.setItem('pc_session_probe', 'tres');
    document.cookie = 'wp_cookie_probe=A; path=/';
    document.cookie = 'wp2_cookie_probe=B; path=/';
    document.cookie = 'pc_cookie_probe=C; path=/';
  });

  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => !!window.PCBackupTools, null, { timeout: 15000 });

  const initial = await page.evaluate(() => ({
    exercise: Number((document.querySelector('.exno')?.textContent.match(/\d+/) || ['0'])[0]),
    sound: document.getElementById('txt-sound')?.textContent,
    mode: document.documentElement.getAttribute('data-modo'),
    board: document.documentElement.getAttribute('data-tablero')
  }));
  assert.equal(initial.exercise, 7, 'index1 did not resume wp_ultimo=7');
  assert.equal(initial.sound, 'Silencio', 'index1 did not restore silence');
  assert.equal(initial.mode, 'oscuro', 'dark mode not applied');
  assert.equal(initial.board, 'lavanda', 'index1 board theme not applied');

  const backup = await page.evaluate(() => window.PCBackupTools.buildBackup());
  assert.equal(backup.magic, 'PC-de-LuisA3-backup');
  assert.equal(backup.payload.storage.local.wp_ultimo, '7');
  assert.equal(backup.payload.storage.local.wp2_ultimo, '9');
  assert.equal(backup.payload.storage.local.pc_modo, 'oscuro');
  assert.equal(backup.payload.storage.local.pc_favs, '["lavanda","menta"]');
  assert.equal(backup.payload.storage.local.wp_probe, 'alpha');
  assert.equal(backup.payload.storage.local.wp2_probe, 'beta');
  assert.equal(backup.payload.storage.local.pc_probe, 'gamma');
  assert.equal(backup.payload.storage.session.wp_session_probe, 'uno');
  assert.equal(backup.payload.storage.session.wp2_session_probe, 'dos');
  assert.equal(backup.payload.storage.session.pc_session_probe, 'tres');
  assert.equal(backup.payload.cookies.wp_cookie_probe, 'A');
  assert.equal(backup.payload.cookies.wp2_cookie_probe, 'B');
  assert.equal(backup.payload.cookies.pc_cookie_probe, 'C');
  assert.equal(backup.payload.currentPageState.lastExercise, 7);

  const namespaceChecks = await page.evaluate(() => ({
    wp: window.PCBackupTools.isAppKey('wp_hist_log'),
    wp2: window.PCBackupTools.isAppKey('wp2_daily_goal'),
    pc: window.PCBackupTools.isAppKey('pc_perso'),
    unrelated: window.PCBackupTools.isAppKey('other_app_key')
  }));
  assert.deepStrictEqual(namespaceChecks, { wp: true, wp2: true, pc: true, unrelated: false });

  const rejectsCorruption = await page.evaluate((env) => {
    const bad = JSON.parse(JSON.stringify(env));
    bad.payload.storage.local.wp_probe = 'alterado';
    try { window.PCBackupTools.validateEnvelope(bad); return false; }
    catch (e) { return true; }
  }, backup);
  assert.equal(rejectsCorruption, true, 'checksum did not reject a modified backup');

  fs.writeFileSync('/tmp/pc-backup.json', JSON.stringify(backup));

  await page.evaluate(() => {
    localStorage.setItem('wp_ultimo', '1');
    localStorage.setItem('wp2_ultimo', '1');
    localStorage.setItem('wp_sound', '1');
    localStorage.setItem('wp2_sound', '1');
    localStorage.setItem('pc_modo', 'claro');
    localStorage.setItem('pc_tablero_1', 'cielo');
    localStorage.setItem('pc_tablero_2', 'cielo');
    localStorage.setItem('pc_favs', '[]');
    localStorage.setItem('wp_probe', 'x');
    localStorage.setItem('wp2_probe', 'y');
    localStorage.setItem('pc_probe', 'z');
    sessionStorage.setItem('wp_session_probe', 'x');
    sessionStorage.setItem('wp2_session_probe', 'y');
    sessionStorage.setItem('pc_session_probe', 'z');
    document.cookie = 'wp_cookie_probe=X; path=/';
    document.cookie = 'wp2_cookie_probe=Y; path=/';
    document.cookie = 'pc_cookie_probe=Z; path=/';
    window.pedirConfirmacion = (_msg, cb) => cb();
  });

  const nav = page.waitForEvent('framenavigated');
  await page.locator('#pc-backup-file').setInputFiles('/tmp/pc-backup.json');
  await nav;
  await page.waitForFunction(() => !!window.PCBackupTools, null, { timeout: 15000 });

  const restored = await page.evaluate(() => ({
    wpUltimo: localStorage.getItem('wp_ultimo'),
    wp2Ultimo: localStorage.getItem('wp2_ultimo'),
    wpSound: localStorage.getItem('wp_sound'),
    wp2Sound: localStorage.getItem('wp2_sound'),
    modeStored: localStorage.getItem('pc_modo'),
    board1Stored: localStorage.getItem('pc_tablero_1'),
    board2Stored: localStorage.getItem('pc_tablero_2'),
    favs: localStorage.getItem('pc_favs'),
    wpProbe: localStorage.getItem('wp_probe'),
    wp2Probe: localStorage.getItem('wp2_probe'),
    pcProbe: localStorage.getItem('pc_probe'),
    s1: sessionStorage.getItem('wp_session_probe'),
    s2: sessionStorage.getItem('wp2_session_probe'),
    s3: sessionStorage.getItem('pc_session_probe'),
    cookies: document.cookie,
    exercise: Number((document.querySelector('.exno')?.textContent.match(/\d+/) || ['0'])[0]),
    sound: document.getElementById('txt-sound')?.textContent,
    mode: document.documentElement.getAttribute('data-modo'),
    board: document.documentElement.getAttribute('data-tablero')
  }));

  assert.equal(restored.wpUltimo, '7');
  assert.equal(restored.wp2Ultimo, '9');
  assert.equal(restored.wpSound, '0');
  assert.equal(restored.wp2Sound, '0');
  assert.equal(restored.modeStored, 'oscuro');
  assert.equal(restored.board1Stored, 'lavanda');
  assert.equal(restored.board2Stored, 'menta');
  assert.equal(restored.favs, '["lavanda","menta"]');
  assert.equal(restored.wpProbe, 'alpha');
  assert.equal(restored.wp2Probe, 'beta');
  assert.equal(restored.pcProbe, 'gamma');
  assert.equal(restored.s1, 'uno');
  assert.equal(restored.s2, 'dos');
  assert.equal(restored.s3, 'tres');
  assert(restored.cookies.includes('wp_cookie_probe=A'));
  assert(restored.cookies.includes('wp2_cookie_probe=B'));
  assert(restored.cookies.includes('pc_cookie_probe=C'));
  assert.equal(restored.exercise, 7);
  assert.equal(restored.sound, 'Silencio');
  assert.equal(restored.mode, 'oscuro');
  assert.equal(restored.board, 'lavanda');

  await open('index2.html');
  const second = await page.evaluate(() => ({
    exercise: Number((document.querySelector('.exno')?.textContent.match(/\d+/) || ['0'])[0]),
    sound: document.getElementById('txt-sound')?.textContent,
    mode: document.documentElement.getAttribute('data-modo'),
    board: document.documentElement.getAttribute('data-tablero'),
    wp2: localStorage.getItem('wp2_ultimo')
  }));
  assert.equal(second.exercise, 9, 'index2 did not resume wp2_ultimo=9 after import');
  assert.equal(second.wp2, '9');
  assert.equal(second.sound, 'Silencio');
  assert.equal(second.mode, 'oscuro');
  assert.equal(second.board, 'menta');

  await browser.close();
  console.log('BROWSER_BACKUP_INTEGRATION: OK');
})().catch(async (err) => {
  console.error(err && err.stack ? err.stack : err);
  process.exit(1);
});
