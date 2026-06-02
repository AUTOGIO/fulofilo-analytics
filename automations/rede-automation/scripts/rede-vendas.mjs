#!/usr/bin/env node

import { chromium } from 'playwright';
import { execFileSync } from 'node:child_process';
import { createInterface } from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = process.env.REDE_AUTOMATION_ROOT
  ? path.resolve(process.env.REDE_AUTOMATION_ROOT)
  : path.resolve(SCRIPT_DIR, '..');
const DOWNLOAD_DIR = process.env.REDE_DOWNLOAD_DIR
  ? path.resolve(process.env.REDE_DOWNLOAD_DIR)
  : path.join(os.homedir(), 'Downloads', 'Rede');
const PROFILE_DIR = path.join(ROOT, '.browser-profile');
const LOG_DIR = path.join(ROOT, 'logs');
const DEBUG_DIR = path.join(LOG_DIR, 'debug');
const LOG_FILE = path.join(LOG_DIR, 'rede-vendas.log');
const LOGIN_URL = 'https://meu.userede.com.br/?redirect=%2Fhome';
const SALES_URL = 'https://meu.userede.com.br/relatorio/vendas';
const SUPPORTED_FORMATS = new Set(['csv', 'excel', 'pdf']);

const FORMAT_CONFIG = {
  csv: { button: 'CSV', extension: '.csv' },
  excel: { button: 'Excel', extension: '.xlsx' },
  pdf: { button: 'PDF', extension: '.pdf' }
};

class UserSafeError extends Error {
  constructor(message, logMessage = message) {
    super(message);
    this.logMessage = logMessage;
  }
}

async function main() {
  await ensureDirectories();
  const options = parseArgs(process.argv.slice(2));
  await log('start', { requestedDate: options.date, requestedFormats: options.formats });

  const credentials = getCredentialsOrExit();
  let browser;
  try {
    browser = await chromium.launchPersistentContext(PROFILE_DIR, {
      acceptDownloads: true,
      downloadsPath: DOWNLOAD_DIR,
      headless: false,
      viewport: { width: 1440, height: 950 },
      locale: 'pt-BR'
    });
  } catch (error) {
    if (/existing browser session|already in use|profile is already/i.test(error.message)) {
      throw new UserSafeError(
        'Another Rede automation browser is already running. Close the other Chromium window (or the previous automation), then run this command again.',
        error.message
      );
    }
    throw error;
  }

  const page = browser.pages()[0] ?? await browser.newPage();
  page.setDefaultTimeout(20_000);
  page.setDefaultNavigationTimeout(45_000);

  try {
    await page.goto(LOGIN_URL, { waitUntil: 'domcontentloaded' });
    await maybeLogin(page, credentials);
    await maybePauseForSecurity(page);
    await navigateToSalesReport(page);
    await selectReportDate(page, options.date);

    for (const format of options.formats) {
      await exportReport(page, options.date, format);
    }

    await log('done', { requestedDate: options.date, requestedFormats: options.formats });
  } catch (error) {
    await log('error', { message: error.message, stack: error.stack });
    console.error(`Rede automation failed: ${error.message}`);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
}

function parseArgs(args) {
  let dateValue = null;
  let formatsValue = 'csv';

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === '--today') {
      dateValue = todayISO();
    } else if (arg === '--yesterday') {
      dateValue = addDaysISO(todayISO(), -1);
    } else if (arg === '--date') {
      dateValue = args[index + 1];
      index += 1;
    } else if (arg === '--formats') {
      formatsValue = args[index + 1];
      index += 1;
    } else if (arg === '--help' || arg === '-h') {
      printUsage();
      process.exit(0);
    } else {
      throw new UserSafeError(`Unknown argument: ${arg}`);
    }
  }

  const date = dateValue ?? todayISO();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(new Date(`${date}T12:00:00`).getTime())) {
    throw new UserSafeError(`Invalid date. Use YYYY-MM-DD, got: ${date}`);
  }

  const formats = formatsValue.split(',').map((format) => format.trim().toLowerCase()).filter(Boolean);
  const invalidFormats = formats.filter((format) => !SUPPORTED_FORMATS.has(format));
  if (formats.length === 0 || invalidFormats.length > 0) {
    throw new UserSafeError(`Invalid formats. Use one or more of: csv,excel,pdf`);
  }

  return { date, formats: [...new Set(formats)] };
}

function printUsage() {
  console.log(`Usage:
  node scripts/rede-vendas.mjs --today
  node scripts/rede-vendas.mjs --yesterday
  node scripts/rede-vendas.mjs --date 2026-05-23
  node scripts/rede-vendas.mjs --date 2026-05-23 --formats csv
  node scripts/rede-vendas.mjs --date 2026-05-23 --formats csv,excel,pdf`);
}

async function ensureDirectories() {
  await fs.mkdir(DOWNLOAD_DIR, { recursive: true });
  await fs.mkdir(LOG_DIR, { recursive: true });
  await fs.mkdir(DEBUG_DIR, { recursive: true });
  await fs.mkdir(PROFILE_DIR, { recursive: true });
}

function getCredentialsOrExit() {
  try {
    const email = readKeychainSecret('rede-automation-email');
    const password = readKeychainSecret('rede-automation-password');
    return { email, password };
  } catch {
    throw new UserSafeError(`Rede credentials were not found in macOS Keychain.

Run these setup commands, then rerun the automation:

security add-generic-password -a "rede-email" -s "rede-automation-email" -w "YOUR_EMAIL_HERE" -U
security add-generic-password -a "rede-password" -s "rede-automation-password" -w "YOUR_PASSWORD_HERE" -U`, 'Rede credentials were not found in macOS Keychain.');
  }
}

function readKeychainSecret(service) {
  return execFileSync('/usr/bin/security', ['find-generic-password', '-s', service, '-w'], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'ignore']
  }).trim();
}

async function maybeLogin(page, credentials) {
  await log('login.check');

  if (await looksLoggedIn(page)) {
    await log('login.state', { state: 'already_logged_in' });
    return;
  }

  await dismissCookieBanner(page);
  await clickLoginEntry(page);
  await page.waitForLoadState('domcontentloaded').catch(() => {});
  await page.waitForTimeout(1_000);
  await dismissCookieBanner(page);

  if (await looksLoggedIn(page)) {
    await log('login.state', { state: 'already_logged_in_after_entry' });
    return;
  }

  const emailInput = await findVisibleLocatorInFrames(page, [
    'input[type="email"]',
    'input[autocomplete="username"]',
    'input[inputmode="email"]',
    'input[name*="email" i]',
    'input[id*="email" i]',
    'input[placeholder*="email" i]',
    'input[aria-label*="email" i]',
    'input[name*="usuario" i]',
    'input[id*="usuario" i]',
    'input[placeholder*="usuario" i]',
    'input[aria-label*="usuario" i]',
    'input[type="text"]:not([readonly]):not([disabled])',
    'input:not([type]):not([readonly]):not([disabled])'
  ], 'email input', 25_000);
  if (!emailInput) return;

  const passwordInput = await findVisibleLocatorInFrames(page, [
    'input[type="password"]',
    'input[autocomplete="current-password"]',
    'input[name*="senha" i]',
    'input[id*="senha" i]',
    'input[placeholder*="senha" i]',
    'input[aria-label*="senha" i]',
    'input[name*="password" i]',
    'input[id*="password" i]'
  ], 'password input', 15_000);
  if (!passwordInput) return;

  await emailInput.fill(credentials.email);
  await passwordInput.fill(credentials.password);

  await log('login.submit', { state: 'credentials_filled_without_logging_values' });
  await clickLoginSubmit(page);
  await page.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {});

  await maybePauseForSecurity(page);
  if (!(await looksLoggedIn(page))) {
    await page.waitForURL(/meu\.userede\.com\.br\/(home|relatorio|dashboard|extrato)/i, { timeout: 30_000 }).catch(() => {});
  }

  await log('login.state', { state: (await looksLoggedIn(page)) ? 'logged_in' : 'unknown_after_submit' });
}

async function dismissCookieBanner(page) {
  const candidates = [
    page.getByRole('button', { name: /aceitar|aceito|ok|entendi|continuar/i }).first(),
    page.getByText(/aceitar cookies|aceito|entendi/i).first()
  ];

  for (const candidate of candidates) {
    if (await candidate.isVisible({ timeout: 1_000 }).catch(() => false)) {
      await candidate.click().catch(() => {});
      await log('cookie.dismissed').catch(() => {});
      return;
    }
  }
}

async function dismissBlockingOverlays(page) {
  let dismissedAny = false;
  for (let round = 0; round < 4; round += 1) {
    await dismissCookieBanner(page);

    const modal = page.locator('core-modal, [role="dialog"], .modal, .cdk-overlay-pane').filter({
      hasText: /novidades|portal|onboarding|entendi|fechar|continuar|começar|comecar|pular|alto falante/i
    }).first();

    if (!(await modal.isVisible({ timeout: 1_000 }).catch(() => false))) {
      break;
    }

    await log('overlay.visible', { url: page.url(), round });
    const closeCandidates = [
      modal.getByRole('button', { name: /fechar|entendi|ok|continuar|começar|comecar|pular|agora não|agora nao/i }).first(),
      modal.locator('button[aria-label*="fechar" i], button[aria-label*="close" i]').first(),
      modal.locator('[class*="close" i], [class*="fechar" i]').first(),
      page.getByRole('button', { name: /fechar|entendi|ok|continuar|começar|comecar|pular|agora não|agora nao/i }).first(),
      page.getByText(/fechar|entendi|continuar|pular|agora não|agora nao/i).first()
    ];

    let closed = false;
    for (const candidate of closeCandidates) {
      if (await candidate.isVisible({ timeout: 1_000 }).catch(() => false)) {
        await candidate.click().catch(() => {});
        await page.waitForTimeout(750);
        closed = true;
        dismissedAny = true;
        break;
      }
    }

    if (!closed) {
      await page.keyboard.press('Escape').catch(() => {});
      await page.waitForTimeout(750);
    }

    if (!(await modal.isVisible({ timeout: 800 }).catch(() => false))) {
      await log('overlay.dismissed', { round });
      dismissedAny = true;
      continue;
    }
    await log('overlay.still_visible', { round });
  }
  return dismissedAny;
}

async function clickLoginEntry(page) {
  const candidates = [
    page.getByRole('button', { name: /acessar conta/i }).first(),
    page.getByRole('link', { name: /acessar conta/i }).first(),
    page.getByText(/acessar conta/i).first()
  ];

  for (const candidate of candidates) {
    if (await candidate.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await log('click', { label: 'login entry' });
      await candidate.click();
      return true;
    }
  }

  await log('login.entry_not_visible', { url: page.url() });
  return false;
}

async function clickLoginSubmit(page) {
  const candidates = [
    page.getByRole('button', { name: /^acessar$/i }).first(),
    page.getByRole('button', { name: /entrar/i }).first(),
    page.getByText(/^acessar$/i).first(),
    page.locator('button[type="submit"]').first(),
    page.locator('input[type="submit"]').first()
  ];

  for (const candidate of candidates) {
    if (await candidate.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await Promise.all([
        page.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {}),
        candidate.click()
      ]);
      return;
    }
  }

  throw new Error('Could not find the Rede login submit button.');
}

async function findVisibleLocatorInFrames(page, selectors, label, timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    for (const frame of page.frames()) {
      for (const selector of selectors) {
        const locator = frame.locator(selector).first();
        if (await locator.isVisible({ timeout: 250 }).catch(() => false)) {
          await log('locator.found', {
            label,
            selector,
            frameUrl: safeFrameUrl(frame.url())
          });
          return locator;
        }
      }
    }
    await page.waitForTimeout(500);
  }

  await logVisibleInputs(page);
  if (label === 'email input') {
    await captureDebug(page, `missing-${label.replace(/\s+/g, '-')}`).catch(() => {});
  }
  console.log(`Could not find the Rede ${label} automatically.`);
  console.log('Manual login required. Complete login in the browser, then press ENTER in Terminal.');
  const rl = createInterface({ input, output });
  await rl.question('');
  rl.close();
  await page.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {});

  if (await looksLoggedIn(page)) {
    await log('login.state', { state: 'manual_login_completed' });
    console.log('Manual login completed. Rerun the command so the automation can continue from a clean logged-in session.');
    return null;
  }

  throw new Error(`Could not find the Rede ${label}. A screenshot and HTML snapshot were saved under ${DEBUG_DIR}.`);
}

async function logVisibleInputs(page) {
  const frames = [];
  for (const frame of page.frames()) {
    const inputs = await frame.locator('input').evaluateAll((nodes) => nodes.map((node) => ({
      type: node.getAttribute('type') || '',
      name: node.getAttribute('name') || '',
      id: node.getAttribute('id') || '',
      placeholder: node.getAttribute('placeholder') || '',
      ariaLabel: node.getAttribute('aria-label') || '',
      autocomplete: node.getAttribute('autocomplete') || '',
      visible: Boolean(node.offsetParent || node.getClientRects().length)
    }))).catch(() => []);
    frames.push({ frameUrl: safeFrameUrl(frame.url()), inputs });
  }
  await log('login.visible_inputs', { frames });
}

async function captureDebug(page, label) {
  await fs.mkdir(DEBUG_DIR, { recursive: true });
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14);
  const safeLabel = label.replace(/[^a-z0-9-]/gi, '-').toLowerCase();
  const screenshotPath = path.join(DEBUG_DIR, `${stamp}-${safeLabel}.png`);
  const htmlPath = path.join(DEBUG_DIR, `${stamp}-${safeLabel}.html`);

  await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
  await fs.writeFile(htmlPath, await page.content(), 'utf8').catch(() => {});
  await log('debug.capture', { label, screenshotPath, htmlPath, url: page.url() });
}

function safeFrameUrl(url) {
  try {
    const parsed = new URL(url);
    return `${parsed.origin}${parsed.pathname}`;
  } catch {
    return url;
  }
}

async function looksLoggedIn(page) {
  const url = page.url();
  if (/\/home|\/relatorio|\/extrato|\/dashboard/.test(url)) return true;
  if (await page.getByText(/extratos|vendas|exportar relatório/i).first().isVisible().catch(() => false)) return true;
  return false;
}

async function maybePauseForSecurity(page) {
  const challenge = page.getByText(/captcha|token|código|codigo|verificação|verificacao|autenticação|autenticacao|2fa|segurança|seguranca/i).first();
  if (await challenge.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await log('security.manual_required');
    console.log('Manual security step required. Complete it in the browser, then press ENTER in Terminal.');
    const rl = createInterface({ input, output });
    await rl.question('');
    rl.close();
    await page.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {});
  }
}

async function navigateToSalesReport(page) {
  await page.goto(SALES_URL, { waitUntil: 'domcontentloaded' });
  await maybePauseForSecurity(page);
  await dismissBlockingOverlays(page);
  await retry('wait for sales report page', async () => {
    await page.waitForURL(/\/relatorio\/vendas/i, { timeout: 20_000 }).catch(() => {});
    await page.getByText(/exportar relatório|exportar relatorio/i).first().waitFor({ state: 'visible', timeout: 20_000 });
  });
  await log('navigation.sales_report_ready', { url: page.url() });
}

function isDateRangeAriaLabel(aria) {
  if (!aria) return false;
  return /até|ate\b|período|periodo/i.test(aria) || /^de\s+\d{1,2}\s+de\s+.+\s+até/i.test(aria);
}

function isCalendarDayAriaLabel(aria, target) {
  if (!aria || isDateRangeAriaLabel(aria)) return false;
  const monthNames = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  const month = monthNames[target.month - 1];
  const dayPatterns = [
    new RegExp(`\\b${target.day}\\b.*\\b${month}\\b.*\\b${target.year}\\b`, 'i'),
    new RegExp(`,\\s*${String(target.day).padStart(2, '0')}\\s+de\\s+${month}`, 'i'),
    new RegExp(`\\b${String(target.day).padStart(2, '0')}\\s+de\\s+${month}`, 'i')
  ];
  return dayPatterns.some((pattern) => pattern.test(aria));
}

async function ensureCalendarMonth(page, target) {
  const monthNames = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  const monthShort = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  const monthLabel = monthNames[target.month - 1];
  const shortLabel = monthShort[target.month - 1];
  const year = String(target.year);

  for (let attempt = 0; attempt < 24; attempt += 1) {
    const headerVisible = await page.locator('button, [role="button"], div, span').filter({
      hasText: new RegExp(`${monthLabel}\\s*${year}|${shortLabel}\\s*/\\s*${year.slice(2)}|${shortLabel}\\s+${year.slice(2)}`, 'i')
    }).first().isVisible({ timeout: 800 }).catch(() => false);

    const dayVisible = await page.evaluate(({ day, month, year: y }) => {
      const monthNamesPt = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
      const want = `${day} de ${monthNamesPt[month - 1]} de ${y}`;
      return Array.from(document.querySelectorAll('button, [role="button"], span, td')).some((node) => {
        const aria = (node.getAttribute('aria-label') || '').toLowerCase();
        return aria.includes(want) && !aria.includes('até') && !aria.includes('ate ');
      });
    }, { day: target.day, month: target.month, year: target.year }).catch(() => false);

    if (headerVisible || dayVisible) {
      await log('date.calendar_month_ready', { month: target.month, year: target.year, attempt });
      return;
    }

    const currentIndex = await page.evaluate(() => {
      const monthNamesPt = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
      const text = (document.body.innerText || '').toLowerCase();
      for (let i = 0; i < monthNamesPt.length; i += 1) {
        if (text.includes(monthNamesPt[i])) return i + 1;
      }
      return null;
    }).catch(() => null);

    const goForward = currentIndex !== null && currentIndex < target.month;
    const navCandidates = goForward
      ? [
          page.getByRole('button', { name: /próximo mês|proximo mes|próximo|proximo|seguinte|next/i }).first(),
          page.locator('[aria-label*="próximo" i], [aria-label*="proximo" i], [aria-label*="seguinte" i], [aria-label*="next" i]').first(),
          page.locator('button[class*="next" i], button[class*="right" i], [class*="chevron-right"]').first()
        ]
      : [
          page.getByRole('button', { name: /mês anterior|mes anterior|anterior|voltar|previous/i }).first(),
          page.locator('[aria-label*="mês anterior" i], [aria-label*="mes anterior" i], [aria-label*="anterior" i], [aria-label*="previous" i]').first(),
          page.locator('button[class*="prev" i], button[class*="left" i], [class*="chevron-left"]').first()
        ];

    let navigated = false;
    for (const nav of navCandidates) {
      if (await nav.isVisible({ timeout: 800 }).catch(() => false)) {
        await nav.click({ timeout: 5_000 }).catch(() => {});
        navigated = true;
        break;
      }
    }
    if (!navigated) break;
    await page.waitForTimeout(450);
  }
}

async function selectReportDate(page, isoDate) {
  await log('date.select.start', { date: isoDate });
  const target = parseISODate(isoDate);
  await dismissBlockingOverlays(page);

  await openDateFilter(page);

  await page.getByText(/limpar|aplicar/i).first().waitFor({ state: 'visible', timeout: 15_000 });
  await ensureCalendarMonth(page, target);
  await dismissBlockingOverlays(page);
  await clickDateInPicker(page, target);

  await dismissBlockingOverlays(page);
  await clickDateApply(page);
  await page.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {});
  await page.waitForTimeout(1_500);
  await log('date.select.done', { date: isoDate });
}

async function openDateFilter(page) {
  const rangePattern = /\d{1,2}\s+(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s+\d{4}\s*-\s*\d{1,2}\s+(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s+\d{4}/i;
  const candidates = [
    page.getByRole('button', { name: rangePattern }).first(),
    page.locator('[role="button"]').filter({ hasText: rangePattern }).first(),
    page.locator('input').filter({ hasText: rangePattern }).first(),
    page.locator('button, a').filter({ hasText: rangePattern }).first(),
    page.getByRole('button', { name: /período|periodo/i }).first()
  ];

  for (const candidate of candidates) {
    if (await candidate.isVisible({ timeout: 4_000 }).catch(() => false)) {
      await dismissBlockingOverlays(page);
      await candidate.click({ timeout: 8_000 });
      await log('date.filter.opened');
      return;
    }
  }

  const textCandidate = page.getByText(rangePattern).first();
  if (await textCandidate.isVisible({ timeout: 4_000 }).catch(() => false)) {
    await dismissBlockingOverlays(page);
    await textCandidate.click({ timeout: 8_000 });
    await log('date.filter.opened', { method: 'text' });
    return;
  }

  await captureDebug(page, 'missing-date-filter').catch(() => {});
  throw new Error(`Could not find the Rede date filter. A screenshot and HTML snapshot were saved under ${DEBUG_DIR}.`);
}

async function clickDateInPicker(page, target) {
  const labels = buildDateLabelRegexes(target);
  for (const label of labels) {
    const locator = page.getByLabel(label).first();
    if (await locator.isVisible({ timeout: 2_000 }).catch(() => false)) {
      const aria = await locator.getAttribute('aria-label').catch(() => '') || '';
      if (!isCalendarDayAriaLabel(aria, target)) {
        continue;
      }
      await locator.scrollIntoViewIfNeeded().catch(() => {});
      await locator.click({ timeout: 8_000 }).catch(async () => {
        await locator.click({ timeout: 8_000, force: true });
      });
      await log('date.day.clicked', { selector: await describeLocator(locator), method: 'aria-label' });
      return;
    }
  }

  const dayHandle = await page.evaluateHandle(({ day, month, year }) => {
    const monthNamesPt = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
    const want = `${day} de ${monthNamesPt[month - 1]} de ${year}`;
    const visible = (node) => {
      const rect = node.getBoundingClientRect();
      const style = window.getComputedStyle(node);
      return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
    };
    for (const node of document.querySelectorAll('button, [role="button"], span, td')) {
      const aria = (node.getAttribute('aria-label') || '').toLowerCase();
      if (!aria.includes(want) || aria.includes('até') || aria.includes('ate ')) continue;
      if (!visible(node)) continue;
      return node;
    }
    return null;
  }, { day: target.day, month: target.month, year: target.year });
  const dayElement = dayHandle.asElement();
  if (dayElement) {
    await dayElement.scrollIntoViewIfNeeded().catch(() => {});
    await dayElement.click({ timeout: 8_000 }).catch(async () => {
      await dayElement.click({ timeout: 8_000, force: true });
    });
    await log('date.day.clicked', { selector: await describeLocator(dayElement), method: 'aria-day-scan' });
    return;
  }

  if (await clickDateByGeometry(page, target)) {
    return;
  }

  const exactDay = String(target.day);
  const dayCandidates = page.locator('button:not([disabled]), [role="button"]:not([aria-disabled="true"]), td, span').filter({ hasText: new RegExp(`^\s*${exactDay}\s*$`) });
  const count = await dayCandidates.count();
  for (let index = 0; index < count; index += 1) {
    const candidate = dayCandidates.nth(index);
    const aria = await candidate.getAttribute('aria-label').catch(() => '') || '';
    const text = (await candidate.textContent().catch(() => '') || '').trim();
    if (isDateRangeAriaLabel(aria) || (/\d{1,2}\s*(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)|\d{4}\s*-\s*\d{4}/i.test(aria) && text !== exactDay)) {
      continue;
    }
    if (await candidate.isVisible().catch(() => false)) {
      await candidate.scrollIntoViewIfNeeded().catch(() => {});
      await candidate.click({ timeout: 8_000 }).catch(async () => {
        await candidate.click({ timeout: 8_000, force: true });
      });
      await log('date.day.clicked', { selector: await describeLocator(candidate), method: 'day-number', index });
      return;
    }
  }

  await captureDebug(page, `missing-day-${target.year}-${String(target.month).padStart(2, '0')}-${String(target.day).padStart(2, '0')}`).catch(() => {});
  throw new Error(`Could not select day ${exactDay} in the date picker. The calendar may be showing a different month.`);
}

async function clickDateByGeometry(page, target) {
  const exactDay = String(target.day);
  const monthShort = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'][target.month - 1];
  const year2 = String(target.year).slice(2);

  const handle = await page.evaluateHandle(({ exactDay, monthShort, year2 }) => {
    const visible = (node) => {
      const rect = node.getBoundingClientRect();
      const style = window.getComputedStyle(node);
      return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
    };
    const textOf = (node) => (node.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
    const all = Array.from(document.querySelectorAll('button, [role="button"], td, span, input, div'));
    const headers = all
      .filter((node) => visible(node))
      .map((node) => ({ node, text: textOf(node), rect: node.getBoundingClientRect() }))
      .filter((item) => item.text.includes(`${monthShort}/${year2}`));
    const header = headers.sort((a, b) => (a.rect.width * a.rect.height) - (b.rect.width * b.rect.height))[0];
    if (!header) return null;

    const candidates = all
      .filter((node) => visible(node))
      .map((node) => ({ node, text: textOf(node), rect: node.getBoundingClientRect(), aria: (node.getAttribute('aria-label') || '').toLowerCase() }))
      .filter((item) => item.text === exactDay)
      .filter((item) => !item.aria.includes('período') && !item.aria.includes('periodo') && !item.aria.includes('até') && !item.aria.includes('ate '))
      .filter((item) => item.rect.top > header.rect.bottom && Math.abs((item.rect.left + item.rect.right) / 2 - (header.rect.left + header.rect.right) / 2) < 160);

    candidates.sort((a, b) => {
      const ax = Math.abs((a.rect.left + a.rect.right) / 2 - (header.rect.left + header.rect.right) / 2);
      const bx = Math.abs((b.rect.left + b.rect.right) / 2 - (header.rect.left + header.rect.right) / 2);
      return ax - bx;
    });
    return candidates[0]?.node || null;
  }, { exactDay, monthShort, year2 });

  const element = handle.asElement();
  if (!element) return false;
  await element.scrollIntoViewIfNeeded().catch(() => {});
  await element.click({ timeout: 8_000 }).catch(async () => {
    await element.click({ timeout: 8_000, force: true });
  });
  await log('date.day.clicked', { selector: await describeLocator(element), method: 'geometry' });
  return true;
}

async function clickDateApply(page) {
  await dismissBlockingOverlays(page);

  const candidates = [
    page.locator('#applyButton').first(),
    page.locator('div#applyButton[role="button"]').first(),
    page.getByRole('button', { name: /^aplicar$/i }).first(),
    page.locator('button, [role="button"]').filter({ hasText: /^\s*aplicar\s*$/i }).first(),
    page.locator('[role="button"]').filter({ hasText: /^\s*aplicar\s*$/i }).first(),
    page.getByText(/^\s*aplicar\s*$/i).first()
  ];

  for (const candidate of candidates) {
    if (await candidate.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await candidate.scrollIntoViewIfNeeded().catch(() => {});
      await candidate.click({ timeout: 8_000 }).catch(async (error) => {
        await log('date.apply.normal_click_failed', { error: error.message, selector: await describeLocator(candidate) });
        await candidate.click({ timeout: 8_000, force: true });
      });
      await log('date.apply.clicked', { selector: await describeLocator(candidate) });
      return;
    }
  }

  await page.keyboard.press('Enter').catch(() => {});
  await page.waitForTimeout(1_000);
  if (!(await page.getByText(/limpar|aplicar/i).first().isVisible({ timeout: 1_000 }).catch(() => false))) {
    await log('date.apply.clicked', { method: 'enter' });
    return;
  }

  await captureDebug(page, 'missing-date-apply').catch(() => {});
  throw new Error(`Could not find or click the Rede date Apply button. A screenshot and HTML snapshot were saved under ${DEBUG_DIR}.`);
}

function buildDateLabelRegexes(target) {
  const monthNames = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  const monthShort = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  return [
    new RegExp(`${target.day}.*${monthNames[target.month - 1]}.*${target.year}`, 'i'),
    new RegExp(`${target.day}.*${monthShort[target.month - 1]}.*${target.year}`, 'i'),
    new RegExp(`${String(target.day).padStart(2, '0')}.*${monthNames[target.month - 1]}.*${target.year}`, 'i')
  ];
}

async function exportReport(page, isoDate, format) {
  const config = FORMAT_CONFIG[format];
  await log('export.start', { format, date: isoDate });
  const beforeFiles = await listDownloadFiles();

  await dismissBlockingOverlays(page);
  await retry(`click export report for ${format}`, async () => {
    const exportButton = page.getByRole('button', { name: /exportar relatório|exportar relatorio/i }).first();
    if (await exportButton.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await exportButton.click();
      return;
    }
    await page.getByText(/exportar relatório|exportar relatorio/i).first().click();
  });

  await clickExportFormat(page, config.button);
  await log('export.format_clicked', { format });

  await waitForDownloadReady(page);
  await openDownloadDrawer(page);

  const downloadPromise = page.waitForEvent('download', { timeout: 60_000 }).catch((error) => {
    log('download.event_timeout', { format, error: error.message }).catch(() => {});
    return null;
  });
  await clickDownloadStart(page);

  const download = await downloadPromise;
  let suggested = '';
  let finalPath = '';

  if (download) {
    suggested = download.suggestedFilename();
    const extension = inferExtension(suggested, config.extension, format);
    finalPath = await uniqueReportPath(isoDate, extension);
    await download.saveAs(finalPath);
  } else {
    const detectedPath = await waitForNewDownloadedFile(beforeFiles, config.extension, 90_000);
    finalPath = await normalizeDownloadedFile(detectedPath, isoDate, config.extension, format);
    suggested = path.basename(detectedPath);
  }

  await log('download.saved', { format, suggestedFilename: suggested, finalPath });
  console.log(`Saved ${format.toUpperCase()} report: ${finalPath}`);
}

async function waitForDownloadReady(page) {
  await retry('wait for download ready drawer', async () => {
    await page.locator('#download-progress, #rc-downloader').filter({
      hasText: /seu arquivo está pronto|seu arquivo esta pronto|seus arquivos estão prontos|seus arquivos estao prontos|100%\s*Completo/i
    }).first().waitFor({
      state: 'visible',
      timeout: 90_000
    });
  }, 3);
}

async function openDownloadDrawer(page) {
  const drawer = page.locator('#rc-downloader').first();
  await drawer.waitFor({ state: 'visible', timeout: 30_000 });

  if (await page.locator('#download-start').first().isVisible({ timeout: 1_000 }).catch(() => false)) {
    return;
  }

  const toggles = [
    page.locator('#download-progress').first(),
    page.locator('#rc-downloader .header').first(),
    drawer.getByRole('button').first()
  ];

  for (const toggle of toggles) {
    if (await toggle.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await toggle.click({ timeout: 8_000 }).catch(async () => {
        await toggle.click({ timeout: 8_000, force: true });
      });
      await log('download.drawer_open_clicked', { selector: await describeLocator(toggle) });
      break;
    }
  }

  await page.waitForFunction(() => {
    const downloader = document.querySelector('#rc-downloader');
    if (!downloader) return false;
    const text = downloader.textContent || '';
    return document.querySelector('#download-start') || /baixar|excluir|Rede_Rel|Rel_Vendas/i.test(text);
  }, null, { timeout: 20_000 }).catch(() => {});
}

async function waitForDownloadStartEnabled(page, timeoutMs = 90_000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    await dismissBlockingOverlays(page).catch(() => {});
    const primary = page.locator('#download-start').first();
    if (await primary.isVisible({ timeout: 1_000 }).catch(() => false)) {
      const disabled = await primary.isDisabled().catch(() => true);
      if (!disabled) return primary;
    }
    await page.waitForTimeout(500);
  }
  return null;
}

async function clickDownloadStart(page) {
  const enabledStart = await waitForDownloadStartEnabled(page);
  if (enabledStart) {
    await enabledStart.scrollIntoViewIfNeeded().catch(() => {});
    await enabledStart.click({ timeout: 8_000 }).catch(async (error) => {
      await log('download.normal_click_failed', { error: error.message });
      await enabledStart.click({ timeout: 8_000, force: true });
    });
    await log('download.click', { selector: await describeLocator(enabledStart) });
    return;
  }

  const candidates = [
    page.locator('#rc-downloader a, #rc-downloader button, #rc-downloader [role="button"]').filter({ hasText: /^\s*baixar\s*$/i }).first(),
    page.locator('#rc-downloader [aria-label*="baixar" i], #rc-downloader [title*="baixar" i]').first(),
    page.locator('#rc-downloader .body a, #rc-downloader .body button').filter({ hasText: /^\s*baixar\s*$/i }).first(),
    page.getByRole('button', { name: /^baixar$/i }).first()
  ];

  for (const candidate of candidates) {
    if (await candidate.isVisible({ timeout: 3_000 }).catch(() => false)) {
      if (await candidate.isDisabled().catch(() => false)) continue;
      await candidate.scrollIntoViewIfNeeded().catch(() => {});
      await candidate.click({ timeout: 8_000 }).catch(async (error) => {
        await log('download.normal_click_failed', { error: error.message });
        await candidate.click({ timeout: 8_000, force: true });
      });
      await log('download.click', { selector: await describeLocator(candidate) });
      return;
    }
  }

  await captureDebug(page, 'missing-download-start').catch(() => {});
  throw new Error(`Could not find #download-start or baixar button. A screenshot and HTML snapshot were saved under ${DEBUG_DIR}.`);
}

async function describeLocator(locator) {
  return await locator.evaluate((node) => {
    const id = node.id ? `#${node.id}` : '';
    const role = node.getAttribute('role') ? `[role="${node.getAttribute('role')}"]` : '';
    const label = node.getAttribute('aria-label') ? `[aria-label="${node.getAttribute('aria-label')}"]` : '';
    const text = (node.textContent || '').trim().slice(0, 40);
    return `${node.tagName.toLowerCase()}${id}${role}${label}${text ? ` ${text}` : ''}`;
  }).catch(() => 'unknown');
}

async function clickExportFormat(page, label) {
  const exactLabel = new RegExp(`^\s*${label}\s*$`, 'i');
  const labelLower = label.toLowerCase();
  const candidates = [
    page.locator(`download-options a[aria-label="${labelLower}"]`).first(),
    page.locator(`download-options a.description.-${label}`).first(),
    page.locator(`download-options [role="button"][aria-label="${labelLower}"]`).first(),
    page.locator('download-options a, download-options [role="button"]').filter({ hasText: exactLabel }).first(),
    page.getByRole('button', { name: exactLabel }).first(),
    page.getByRole('menuitem', { name: exactLabel }).first(),
    page.locator('button, [role="button"], [role="menuitem"], a').filter({ hasText: exactLabel }).first(),
    page.locator(`body > userede-root > app-root > div > main > div > report-sales > rede-tab > div > rede-tab-item > div:nth-child(2) > div > div > div > div > rc-row > div > div > div.report-summary-header.ng-star-inserted > div > div > download-options > div > div > div.options > div:nth-child(${labelLower === 'excel' ? 1 : labelLower === 'csv' ? 2 : 3}) > a`).first()
  ];

  for (const candidate of candidates) {
    if (await candidate.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await candidate.scrollIntoViewIfNeeded().catch(() => {});
      await candidate.click({ timeout: 10_000 });
      await log('export.format_locator_clicked', { label });
      return;
    }
  }

  await captureDebug(page, `missing-export-${label}`).catch(() => {});
  throw new Error(`Could not find export format button: ${label}`);
}

async function listDownloadFiles() {
  await fs.mkdir(DOWNLOAD_DIR, { recursive: true });
  const entries = await fs.readdir(DOWNLOAD_DIR, { withFileTypes: true });
  const files = new Map();
  for (const entry of entries) {
    if (!entry.isFile()) continue;
    const filePath = path.join(DOWNLOAD_DIR, entry.name);
    const stat = await fs.stat(filePath).catch(() => null);
    if (stat) files.set(filePath, { size: stat.size, mtimeMs: stat.mtimeMs });
  }
  return files;
}

async function waitForNewDownloadedFile(beforeFiles, extension, timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const currentFiles = await listDownloadFiles();
    const candidates = [];
    for (const [filePath, stat] of currentFiles.entries()) {
      const before = beforeFiles.get(filePath);
      const ext = path.extname(filePath).toLowerCase();
      const isExpectedType = ext === extension || (extension === '.xlsx' && ext === '.xls');
      const isTemporary = /\.(crdownload|download|tmp)$/i.test(filePath);
      if (!isTemporary && isExpectedType && (!before || before.size !== stat.size || before.mtimeMs !== stat.mtimeMs)) {
        candidates.push({ filePath, stat });
      }
    }

    if (candidates.length > 0) {
      candidates.sort((a, b) => b.stat.mtimeMs - a.stat.mtimeMs);
      await waitForFileStable(candidates[0].filePath);
      return candidates[0].filePath;
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  throw new Error(`Download did not appear in ${DOWNLOAD_DIR} within ${Math.round(timeoutMs / 1000)} seconds.`);
}

async function waitForFileStable(filePath) {
  let previousSize = -1;
  for (let attempt = 0; attempt < 10; attempt += 1) {
    const stat = await fs.stat(filePath).catch(() => null);
    if (stat && stat.size > 0 && stat.size === previousSize) return;
    previousSize = stat?.size ?? -1;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
}

async function normalizeDownloadedFile(filePath, isoDate, fallbackExtension, format) {
  const extension = inferExtension(path.basename(filePath), fallbackExtension, format);
  const finalPath = await uniqueReportPath(isoDate, extension);
  if (path.resolve(filePath) === path.resolve(finalPath)) return finalPath;
  await fs.rename(filePath, finalPath);
  return finalPath;
}

async function clickIfVisible(page, locator, label) {
  if (await locator.first().isVisible({ timeout: 5_000 }).catch(() => false)) {
    await log('click', { label });
    await locator.first().click();
    return true;
  }
  return false;
}

async function retry(label, action, attempts = 3) {
  let lastError;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await action();
    } catch (error) {
      lastError = error;
      await log('retry', { label, attempt, error: error.message });
      if (attempt < attempts) await new Promise((resolve) => setTimeout(resolve, attempt * 1500));
    }
  }
  throw new Error(`${label} failed after ${attempts} attempts: ${lastError.message}`);
}

function inferExtension(filename, fallback, format) {
  const ext = path.extname(filename || '').toLowerCase();
  if (format === 'excel' && ['.xlsx', '.xls'].includes(ext)) return ext;
  if (format === 'csv' && ext === '.csv') return ext;
  if (format === 'pdf' && ext === '.pdf') return ext;
  return fallback;
}

async function uniqueReportPath(isoDate, extension) {
  const base = path.join(DOWNLOAD_DIR, `Rede_Rel_Vendas_${isoDate}${extension}`);
  if (!(await exists(base))) return base;
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14);
  return path.join(DOWNLOAD_DIR, `Rede_Rel_Vendas_${isoDate}_${stamp}${extension}`);
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

function todayISO() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

function addDaysISO(isoDate, days) {
  const date = new Date(`${isoDate}T12:00:00`);
  date.setDate(date.getDate() + days);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function parseISODate(isoDate) {
  const [year, month, day] = isoDate.split('-').map(Number);
  return { year, month, day };
}

async function log(event, data = {}) {
  const line = JSON.stringify({
    timestamp: new Date().toISOString(),
    event,
    ...redact(data)
  });
  await fs.mkdir(LOG_DIR, { recursive: true });
  await fs.appendFile(LOG_FILE, `${line}\n`, 'utf8');
}

function redact(value) {
  if (Array.isArray(value)) return value.map(redact);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.entries(value).map(([key, item]) => {
    if (/email|password|senha|credential|secret/i.test(key)) return [key, '[redacted]'];
    return [key, redact(item)];
  }));
}

main().catch(async (error) => {
  const message = error instanceof UserSafeError ? error.message : `Unexpected startup failure: ${error.message}`;
  const logMessage = error instanceof UserSafeError ? error.logMessage : message;
  const logData = error instanceof UserSafeError ? { message: logMessage } : { message: logMessage, stack: error.stack };
  await log('fatal', logData).catch(() => {});
  console.error(message);
  process.exit(error instanceof UserSafeError ? 2 : 1);
});
