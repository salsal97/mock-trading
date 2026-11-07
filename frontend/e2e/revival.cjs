// Requires a disposable revival_local_settings database and local servers; never targets .env databases.
const { chromium, request } = require('../../.browser-test-deps/node_modules/playwright-core');
const assert = require('node:assert/strict');
const base = 'http://localhost:3100';
const api = 'http://127.0.0.1:8765';
const password = 'LocalTestPass42!';
const suffix = String(Date.now());
const names = ['owner', 'maker', 'trader'].map(n => `rv_${n}_${suffix}`);
const question = `Browser lifecycle ${suffix}`;
const failures = [];
const localDate = offset => {
  const date = new Date(Date.now() + offset * 60000);
  const pad = n => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};
(async () => {
  const http = await request.newContext();
  const identity = await http.get(`${api}/__revival_test__/identity/`);
  assert.equal(identity.status(), 200, 'The isolated local test server is required');
  assert.deepEqual(await identity.json(), {environment:'revival-local-sqlite-only'});
  for (const username of names) {
    const result = await http.post(`${api}/api/auth/register/`, {data:{username, password, password2:password}});
    assert.equal(result.status(), 201, `registration ${username}: ${await result.text()}`);
  }
  await http.dispose();
  const browser = await chromium.launch({headless:true, executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  try {
    const pages = [];
    for (const name of names) {
      const context = await browser.newContext();
      const page = await context.newPage();
      page.on('response', response => { if (response.url().includes('/api/') && response.status() >= 400) failures.push(`${response.status()} ${response.url()}`); });
      page.on('pageerror', error => failures.push(error.message));
      await page.goto(`${base}/auth`);
      await page.locator('#username').fill(name);
      await page.locator('#password').fill(password);
      await page.locator('form').getByRole('button', {name:/sign in to platform/i}).click();
      await page.waitForURL('**/dashboard');
      await page.goto(`${base}/markets`);
      await page.getByText(`Signed in as ${name}`).waitFor();
      pages.push(page);
    }
    const [owner,maker,trader] = pages;
    await owner.getByText('Create a market').click();
    await owner.getByLabel('Question').fill(question);
    await owner.getByLabel('Unit value', {exact:true}).first().fill('10');
    await owner.getByLabel('Bidding opens').fill(localDate(-5));
    await owner.getByLabel('Bidding closes').fill(localDate(60));
    await owner.getByLabel('Trading closes').fill(localDate(120));
    await owner.getByRole('button',{name:'Create',exact:true}).click();
    await owner.getByRole('button',{name:'Select maker and open trading'}).waitFor();
    await maker.reload(); await maker.getByRole('button',{name:question}).click();
    await maker.getByLabel('Low',{exact:true}).fill('80'); await maker.getByLabel('High',{exact:true}).fill('90');
    await maker.getByRole('button',{name:'Save quote'}).click();
    await maker.getByText(`${names[1]}: 80–90`).waitFor();
    await owner.getByRole('button',{name:'Select maker and open trading'}).click();
    await owner.getByText('Quote: 80–90').waitFor();
    await trader.reload(); await trader.getByRole('button',{name:question}).click();
    await trader.getByRole('button',{name:'BUY',exact:true}).click();
    await trader.getByText('Your position: BUY at 90').waitFor();
    await trader.getByRole('button',{name:'SELL',exact:true}).click();
    await trader.getByText('Your position: SELL at 80').waitFor();
    await trader.getByRole('button',{name:'BUY',exact:true}).click();
    await trader.getByText('Your position: BUY at 90').waitFor();
    await maker.reload(); await maker.getByRole('button',{name:question}).click();
    await maker.getByLabel('Hypothetical outcome value').fill('93');
    await maker.getByText('Simulated maker P&L: -30.00').waitFor();
    await owner.getByRole('button',{name:'Close trading'}).click();
    await owner.getByRole('heading',{name:'Settlement',exact:true}).waitFor();
    await owner.getByLabel('Unit value',{exact:true}).last().fill('20');
    await owner.getByRole('button',{name:'Save unit value'}).click();
    await owner.getByText(/Unit value: 20/).waitFor();
    await owner.getByLabel('Outcome',{exact:true}).fill('93');
    await owner.getByRole('button',{name:'Save outcome'}).click();
    await owner.getByRole('button',{name:'Preview',exact:true}).click();
    await owner.getByRole('table').getByText('60.00').waitFor();
    await owner.getByText(`Maker ${names[1]}: -60.00`).waitFor();
    await owner.getByRole('button',{name:'Confirm settlement'}).click();
    await owner.getByText('Final outcome: 93.00').waitFor();
    await trader.reload(); await trader.getByText('Balance: 1060.00 virtual dollars').waitFor();
    await maker.reload(); await maker.getByText('Balance: 940.00 virtual dollars').waitFor();
    assert.deepEqual(failures, [], `Unexpected browser/API errors: ${failures.join('; ')}`);
    console.log('PASS: create, quote, activate, switch position, maker simulation, preview, settle and balances');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
