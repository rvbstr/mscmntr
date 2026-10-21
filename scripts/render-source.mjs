import { chromium } from 'playwright';
import { lookup } from 'node:dns/promises';
import net from 'node:net';
import fs from 'node:fs';
import { X509Certificate, createHash } from 'node:crypto';

const target = new URL(process.argv[2]);
const budget = Math.min(Number(process.argv[3]) || 20000, 30000);
const known = new Map();
function publicIP(ip) {
  if (net.isIP(ip) === 4) {
    const [a,b] = ip.split('.').map(Number);
    return !(a>=224 || [0,10,127,169].includes(a) || (a===172 && b>=16 && b<=31) || (a===192 && b===168) || (a===100 && b>=64 && b<=127) || (a===198 && [18,19,51].includes(b)) || (a===192 && [0,88].includes(b)) || (a===203 && b===0));
  }
  return net.isIP(ip)===6 && !/^(::|fc|fd|fe[89ab]|ff|2001:db8|2002:)/i.test(ip);
}
async function allowed(raw) {
  let url;
  try { url=new URL(raw); } catch { return false; }
  if (!['http:','https:'].includes(url.protocol) || url.username || url.password || (url.port && !['80','443'].includes(url.port))) return false;
  if (['localhost','metadata.google.internal'].includes(url.hostname)) return false;
  if (!known.has(url.hostname)) {
    try { known.set(url.hostname,(await lookup(url.hostname,{all:true})).every(r=>publicIP(r.address))); }
    catch { known.set(url.hostname,url.hostname===target.hostname); }
  }
  return known.get(url.hostname);
}
if (!await allowed(target.href)) throw new Error('Non-public target');
const executable = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || (fs.existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined);
const browserArgs=['--no-sandbox','--disable-dev-shm-usage'];
// Trust only the execution environment's explicitly configured CA, as Node and
// Requests already do. Do not disable certificate checks for arbitrary servers.
if (process.env.NODE_EXTRA_CA_CERTS && fs.existsSync(process.env.NODE_EXTRA_CA_CERTS)) {
  const certs=fs.readFileSync(process.env.NODE_EXTRA_CA_CERTS,'utf8').match(/-----BEGIN CERTIFICATE-----[\s\S]+?-----END CERTIFICATE-----/g)||[];
  const pins=certs.map(pem=>createHash('sha256').update(new X509Certificate(pem).publicKey.export({type:'spki',format:'der'})).digest('base64'));
  if (pins.length) browserArgs.push(`--ignore-certificate-errors-spki-list=${pins.join(',')}`);
}
const browser=await chromium.launch({executablePath:executable,headless:true,args:browserArgs});
try {
  const context=await browser.newContext({locale:'ru-RU',timezoneId:'Europe/Moscow',acceptDownloads:false,serviceWorkers:'block'});
  await context.route('**/*',async route=>{
    const request=route.request();
    if (/google-analytics|googletagmanager|mc\.yandex|facebook\.net|doubleclick/i.test(request.url())) return route.abort();
    if (['image','media','font'].includes(request.resourceType()) || !await allowed(request.url())) return route.abort();
    if (!['GET','HEAD'].includes(request.method())) {
      if (process.env.SOURCE_DEBUG==='1') process.stderr.write(JSON.stringify({method:request.method(),url:request.url().split('?')[0],keys:Object.keys(request.postDataJSON()||{})})+'\n');
      return route.abort();
    }
    return route.continue();
  });
  const page=await context.newPage();
  const response=await page.goto(target.href,{waitUntil:'commit',timeout:budget});
  if (response && response.status()>=400) throw new Error(`HTTP ${response.status()}`);
  await page.waitForLoadState('domcontentloaded',{timeout:Math.min(budget/2,10000)}).catch(()=>{});
  await page.waitForLoadState('networkidle',{timeout:3000}).catch(()=>{});
  await page.locator('body').waitFor({timeout:3000});
  const state=await page.evaluate(()=>{
    try { return JSON.stringify({nuxt:window.__NUXT__||null,next:window.__NEXT_DATA__||null,initial:window.__INITIAL_STATE__||null}); }
    catch { return '{}'; }
  });
  let html=await page.content();
  if (state && state.length<1800000) html+=`<script id="source-state-json" type="application/json">${state.replaceAll('<','\\u003c')}</script>`;
  if (Buffer.byteLength(html)>3000000) throw new Error('Rendered document too large');
  process.stdout.write(JSON.stringify({html,url:page.url(),method:'playwright_chromium'}));
} finally { await browser.close(); }
