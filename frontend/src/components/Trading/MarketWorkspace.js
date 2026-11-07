import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiGet, apiPost, apiRequest, handleApiError } from '../../utils/apiUtils';
import SettledTradesView from './SettledTradesView';

const emptyForm = {premise: '', unit_value: '10', spread_bidding_open: '', spread_bidding_close_trading_open: '', trading_close: ''};
const dateInput = value => value ? new Date(value).toISOString() : '';

export default function MarketWorkspace() {
  const requestGeneration = useRef(0);
  const selection = useRef(null);
  const [markets, setMarkets] = useState([]);
  const [user, setUser] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [trades, setTrades] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(null);
  const [quote, setQuote] = useState({low: '', high: ''});
  const [outcome, setOutcome] = useState('');
  const [unit, setUnit] = useState('');
  const [deadline, setDeadline] = useState('');
  const [simulation, setSimulation] = useState(90);
  const [form, setForm] = useState(emptyForm);
  const selected = markets.find(m => m.id === selectedId);

  const refresh = useCallback(async (id) => {
    const generation = ++requestGeneration.current;
    const [ms, profile] = await Promise.all([apiGet('/api/market/'), apiGet('/api/auth/user-profile/')]);
    if (generation !== requestGeneration.current || id !== selection.current) return ms;
    setMarkets(ms); setUser(profile);
    if (id) {
      const activity = await apiGet(`/api/market/${id}/trades/`);
      if (generation === requestGeneration.current && id === selection.current) setTrades(activity.trades);
    }
    return ms;
  }, []);
  useEffect(() => { refresh(selectedId).catch(e => setError(handleApiError(e))); }, [refresh, selectedId]);
  useEffect(() => {
    if (!selectedId || !selected || !['CREATED', 'OPEN'].includes(selected.status)) return undefined;
    const timer = setInterval(() => refresh(selectedId).catch(e => setError(handleApiError(e))), 5000);
    return () => clearInterval(timer);
  }, [refresh, selectedId, selected?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  async function run(fn) { if (busy) return; setBusy(true); try { setError(''); await fn(); } catch (e) { setError(handleApiError(e)); } finally { setBusy(false); } }
  async function action(path, data = {}) {
    await apiPost(`/api/market/${selectedId}/${path}`, data);
    setPreview(null); await refresh(selectedId);
  }
  function selectMarket(m) {
    selection.current = m.id; requestGeneration.current += 1;
    setSelectedId(m.id); setUnit(String(m.unit_value)); setOutcome(m.settlement_price || '');
    setDeadline(''); setPreview(null); setTrades([]);
  }
  async function saveEdit(data) {
    await apiRequest('patch', `/api/market/${selectedId}/edit/`, data);
    setPreview(null); await refresh(selectedId);
  }
  const owner = selected && user && selected.created_by_username === user.username;
  const maker = selected && user && selected.market_maker_username === user.username;
  const buyers = trades.filter(t => t.position === 'BUY');
  const sellers = trades.filter(t => t.position === 'SELL');
  const pnl = selected ? trades.reduce((sum, t) => sum + (t.position === 'BUY' ? Number(t.price) - simulation : simulation - Number(t.price)) * Number(selected.unit_value), 0) : 0;

  return <main style={{maxWidth: 1000, margin: '2rem auto', padding: '0 1rem'}}>
    <h1>Market workspace</h1><Link to="/dashboard">Dashboard</Link>
    {user && <p>Signed in as {user.username} · Balance: {Number(user.balance).toFixed(2)} virtual dollars</p>}
    {error && <p role="alert">{error}</p>}
    <details><summary>Create a market</summary>
      <form onSubmit={e => {e.preventDefault(); run(async () => {
        const data = {...form};
        ['spread_bidding_open', 'spread_bidding_close_trading_open', 'trading_close'].forEach(k => {data[k] = dateInput(data[k]);});
        const m = await apiPost('/api/market/', data); await refresh(); selectMarket(m);
      });}}>
        <label>Question <input required value={form.premise} onChange={e => setForm({...form, premise: e.target.value})}/></label>
        <label> Unit value <input required type="number" min="0.01" step="0.01" value={form.unit_value} onChange={e => setForm({...form, unit_value: e.target.value})}/></label>
        {['spread_bidding_open', 'spread_bidding_close_trading_open', 'trading_close'].map((k, i) => <label key={k}> {['Bidding opens', 'Bidding closes', 'Trading closes'][i]} <input required type="datetime-local" value={form[k]} onChange={e => setForm({...form, [k]: e.target.value})}/></label>)} <button>Create</button>
      </form>
    </details>
    <h2>All markets</h2><ul>{markets.map(m => <li key={m.id}><button disabled={busy} onClick={() => selectMarket(m)}>{m.premise}</button> {m.status}</li>)}</ul>
    {selected && <section><fieldset disabled={busy}><h2>{selected.premise}</h2>
      <p>Status: {selected.status} · Unit value: {selected.unit_value} · Administrator: {selected.created_by_username} · Maker: {selected.market_maker_username || 'Not selected'}</p>
      {selected.status === 'CREATED' && <><h3>Current top quotes</h3><ol>{(selected.top_quotes || []).map(q => <li key={q.id}>{q.user_username}: {q.spread_low}–{q.spread_high}</li>)}</ol><p>Your rank: {selected.personal_rank || 'No quote'}</p>
        {!owner && <form onSubmit={e => {e.preventDefault(); run(() => action('place_spread_bid/', {spread_low: quote.low, spread_high: quote.high}));}}><label>Low <input type="number" min="1" required value={quote.low} onChange={e => setQuote({...quote, low: e.target.value})}/></label><label>High <input type="number" min="1" required value={quote.high} onChange={e => setQuote({...quote, high: e.target.value})}/></label><button>Save quote</button></form>}
        {owner && <button onClick={() => run(() => action('manual_activate/'))}>Select maker and open trading</button>}</>}
      {selected.status === 'OPEN' && <><p>Quote: {selected.final_spread_low}–{selected.final_spread_high}</p>
        {selected.user_trade && <p>Your position: {selected.user_trade.position === 'BUY' ? 'BUY' : 'SELL'} at {selected.user_trade.price}</p>}
        {!owner && !maker && <p><button onClick={() => run(() => action('place_trade/', {position: 'BUY'}))}>BUY</button> <button onClick={() => run(() => action('place_trade/', {position: 'SELL'}))}>SELL</button></p>}
        {[['BUYERS', buyers], ['SELLERS', sellers]].map(([name, items]) => <p key={name}>{name}: {items.length > 7 ? items.length : items.map(t => t.user_username).join(', ') || 'None'}</p>)}
        {maker && <div><label>Hypothetical outcome <input type="range" min="0" max="200" value={simulation} onChange={e => setSimulation(Number(e.target.value))}/><input aria-label="Hypothetical outcome value" type="number" value={simulation} onChange={e => setSimulation(Number(e.target.value))}/></label><p>Simulated maker P&amp;L: {pnl.toFixed(2)}</p></div>}
        {owner && <button onClick={() => run(() => action('close-trading/'))}>Close trading</button>}</>}
      {selected.status === 'SETTLED' && <><p>Final outcome: {selected.settlement_price}</p><SettledTradesView marketId={selected.id}/></>}
      {owner && selected.status !== 'SETTLED' && <div><h3>Market settings</h3><label>Unit value <input type="number" min="0.01" step="0.01" value={unit} onChange={e => {setUnit(e.target.value); setPreview(null);}}/></label><button onClick={() => run(() => saveEdit({unit_value: unit}))}>Save unit value</button>
        {selected.status !== 'CLOSED' && <><label> Trading deadline <input type="datetime-local" value={deadline} onChange={e => setDeadline(e.target.value)}/></label><button disabled={!deadline} onClick={() => run(() => saveEdit({trading_close: dateInput(deadline)}))}>Save deadline</button></>}
        {selected.status === 'CREATED' && <p>For bidding deadline changes use a time before the trading deadline: <label>Bidding deadline <input type="datetime-local" value={deadline} onChange={e => setDeadline(e.target.value)}/></label><button disabled={!deadline} onClick={() => run(() => saveEdit({spread_bidding_close_trading_open: dateInput(deadline)}))}>Save bidding deadline</button></p>}
        {selected.status === 'CLOSED' && !selected.settlement_price && <><label>Reopen until <input type="datetime-local" value={deadline} onChange={e => setDeadline(e.target.value)}/></label><button disabled={!deadline} onClick={() => run(() => action('reopen-trading/', {new_trading_close: dateInput(deadline)}))}>Reopen trading</button></>}
      </div>}
      {owner && selected.status === 'CLOSED' && <><h3>Settlement</h3><label>Outcome <input type="number" min="0.01" max="999999.99" step="0.01" value={outcome} onChange={e => {setOutcome(e.target.value); setPreview(null);}}/></label><button onClick={() => run(() => action('set-settlement-price/', {price: outcome}))}>Save outcome</button>
        <button onClick={() => run(async () => setPreview(await apiGet(`/api/market/${selectedId}/settlement-preview/`)))}>Preview</button>
        {preview && <div><h4>Settlement preview</h4><p>Outcome: {preview.settlement_price} · Unit value: {selected.unit_value}</p><table><thead><tr><th>Participant</th><th>Position</th><th>Entry</th><th>P&amp;L</th></tr></thead><tbody>{preview.trades.map(t => <tr key={t.trade_id}><td>{t.username}</td><td>{t.position === 'BUY' ? 'BUY' : 'SELL'}</td><td>{t.trade_price}</td><td>{Number(t.profit_loss).toFixed(2)}</td></tr>)}</tbody></table><p>Maker {preview.market_maker.username}: {Number(preview.market_maker_impact).toFixed(2)}</p><button onClick={() => run(() => action('execute-settlement/', {confirmed: true, preview_version: preview.preview_version}))}>Confirm settlement</button></div>}</>}
    </fieldset></section>}
  </main>;
}
