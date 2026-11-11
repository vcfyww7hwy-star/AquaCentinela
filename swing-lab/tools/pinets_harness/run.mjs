// NOT RUN YET (see README.md). Runs a Pine script in PineTS on local daily bars and writes its plots as JSON.
//
//   node run.mjs <script.pine> <TICKER> [--tf D] [--inputs '{"Input title": value}'] [--alerts] [--out file.json]
//
// Bars come from ./bars/<TICKER>.json (export_bars.py). Other symbols a script requests (for
// example AMEX:SPY) are served from the same folder; the exchange prefix is ignored.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const entry = process.env.PINETS_ENTRY;
const { PineTS, BaseProvider, Indicator } = await import(entry ? pathToFileURL(entry).href : 'pinets');

const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const [scriptFile, ticker] = args;
const tf = opt('--tf', 'D');
const inputs = JSON.parse(opt('--inputs', '{}'));
const barsDir = opt('--bars', path.join(here, 'bars'));
const symbolOf = (tickerId) => String(tickerId).split(':').pop().split('|')[0];

class LocalBars extends BaseProvider {
    constructor() { super({ requiresApiKey: false, providerName: 'LocalBars' }); this.cache = new Map(); }
    getSupportedTimeframes() { return new Set(['D']); }
    load(tickerId) {
        const sym = symbolOf(tickerId);
        if (!this.cache.has(sym)) this.cache.set(sym, JSON.parse(fs.readFileSync(path.join(barsDir, `${sym}.json`), 'utf8')));
        return this.cache.get(sym);
    }
    async _getMarketDataNative(tickerId, timeframe, limit, sDate, eDate) {
        let rows = this.load(tickerId);
        if (sDate) rows = rows.filter((r) => r.openTime >= sDate);
        if (eDate) rows = rows.filter((r) => r.openTime <= eDate);
        if (limit && rows.length > limit) rows = rows.slice(rows.length - limit);
        return rows.map((r) => ({ ...r, quoteAssetVolume: 0, numberOfTrades: 0, takerBuyBaseAssetVolume: 0, takerBuyQuoteAssetVolume: 0, ignore: 0 }));
    }
    async getSymbolInfo(tickerId) {
        const sym = symbolOf(tickerId);
        const prefix = String(tickerId).includes(':') ? String(tickerId).split(':')[0] : 'NASDAQ';
        return { current_contract: '', description: sym, isin: '', main_tickerid: `${prefix}:${sym}`, prefix, root: sym, ticker: sym, tickerid: `${prefix}:${sym}`,
            type: 'stock', basecurrency: '', country: 'US', currency: 'USD', timezone: 'America/New_York', employees: 0, industry: '', sector: '',
            shareholders: 0, shares_outstanding_float: 0, shares_outstanding_total: 0, expiration_date: 0, session: '0930-1600', volumetype: 'base',
            mincontract: 1, minmove: 1, mintick: 0.01, pointvalue: 1, pricescale: 100, recommendations_buy: 0, recommendations_buy_strong: 0,
            recommendations_date: 0, recommendations_hold: 0, recommendations_sell: 0, recommendations_sell_strong: 0, recommendations_total: 0,
            target_price_average: 0, target_price_date: 0, target_price_estimates: 0, target_price_high: 0, target_price_low: 0, target_price_median: 0 };
    }
}

const pine = new PineTS(new LocalBars(), ticker, tf, 100000);
if (args.includes('--alerts')) pine.setAlertMode('all');
const ctx = await pine.run(new Indicator(fs.readFileSync(scriptFile, 'utf8'), inputs));
const out = { ticker, timeframe: tf, bars: ctx.marketData.length, time: ctx.marketData.map((b) => b.openTime), plots: {}, alerts: ctx.alerts ?? [],
    warnings: (ctx.warnings ?? []).slice(0, 20) };
for (const [name, p] of Object.entries(ctx.plots ?? {})) {
    if (p && Array.isArray(p.data)) out.plots[name] = p.data.map((d) => (d && typeof d.value === 'number' && Number.isFinite(d.value) ? d.value : null));
}
const text = JSON.stringify(out);
const outFile = opt('--out', null);
if (outFile) fs.writeFileSync(outFile, text); else process.stdout.write(text);
