import React, { useState } from 'react';
import { apiGet, apiPost, apiRequest } from '../../utils/apiUtils';

const dateInput = value => value ? new Date(value).toISOString() : '';

function AdministratorControls({ selected, unit, setUnit, deadline, setDeadline, setPreview, run, saveEdit, action }) {
  if (selected.status === 'SETTLED') return null;
  return <div>
    <h3>Market settings</h3>
    <label>Unit value <input type="number" min="0.01" step="0.01" value={unit} onChange={e => { setUnit(e.target.value); setPreview(null); }} /></label>
    <button onClick={() => run(() => saveEdit({ unit_value: unit }))}>Save unit value</button>
    {selected.status !== 'CLOSED' && <>
      <label> Trading deadline <input type="datetime-local" value={deadline} onChange={e => setDeadline(e.target.value)} /></label>
      <button disabled={!deadline} onClick={() => run(() => saveEdit({ trading_close: dateInput(deadline) }))}>Save deadline</button>
    </>}
    {selected.status === 'CREATED' && <p>For bidding deadline changes use a time before the trading deadline:
      <label>Bidding deadline <input type="datetime-local" value={deadline} onChange={e => setDeadline(e.target.value)} /></label>
      <button disabled={!deadline} onClick={() => run(() => saveEdit({ spread_bidding_close_trading_open: dateInput(deadline) }))}>Save bidding deadline</button>
    </p>}
    {selected.status === 'CLOSED' && !selected.settlement_price && <>
      <label>Reopen until <input type="datetime-local" value={deadline} onChange={e => setDeadline(e.target.value)} /></label>
      <button disabled={!deadline} onClick={() => run(() => action('reopen-trading/', { new_trading_close: dateInput(deadline) }))}>Reopen trading</button>
    </>}
  </div>;
}

function Settlement({ selected, selectedId, outcome, setOutcome, preview, setPreview, run, action }) {
  if (selected.status !== 'CLOSED') return null;
  return <>
    <h3>Settlement</h3>
    <label>Outcome <input type="number" min="0.01" max="999999.99" step="0.01" value={outcome} onChange={e => { setOutcome(e.target.value); setPreview(null); }} /></label>
    <button onClick={() => run(() => action('set-settlement-price/', { price: outcome }))}>Save outcome</button>
    <button onClick={() => run(async () => setPreview(await apiGet(`/api/market/${selectedId}/settlement-preview/`)))}>Preview</button>
    {preview && <div>
      <h4>Settlement preview</h4>
      <p>Outcome: {preview.settlement_price} · Unit value: {selected.unit_value}</p>
      <table>
        <thead><tr><th>Participant</th><th>Position</th><th>Entry</th><th>P&amp;L</th></tr></thead>
        <tbody>{preview.trades.map(t => <tr key={t.trade_id}>
          <td>{t.username}</td><td>{t.position === 'BUY' ? 'BUY' : 'SELL'}</td><td>{t.trade_price}</td><td>{Number(t.profit_loss).toFixed(2)}</td>
        </tr>)}</tbody>
      </table>
      <p>Maker {preview.market_maker.username}: {Number(preview.market_maker_impact).toFixed(2)}</p>
      <button onClick={() => run(() => action('execute-settlement/', { confirmed: true, preview_version: preview.preview_version }))}>Confirm settlement</button>
    </div>}
  </>;
}

export default function MarketAdministration({ selected, run, refresh }) {
  const [preview, setPreview] = useState(null);
  const [outcome, setOutcome] = useState(selected.settlement_price || '');
  const [unit, setUnit] = useState(String(selected.unit_value));
  const [deadline, setDeadline] = useState('');

  async function adminAction(path, data) {
    await apiPost(`/api/market/${selected.id}/${path}`, data || {});
    // Any successful administration action requires a fresh settlement preview.
    setPreview(null);
    await refresh(selected.id);
  }

  async function saveEdit(data) {
    await apiRequest('patch', `/api/market/${selected.id}/edit/`, data);
    setPreview(null);
    await refresh(selected.id);
  }

  return <>
    <AdministratorControls selected={selected} unit={unit} setUnit={setUnit} deadline={deadline} setDeadline={setDeadline} setPreview={setPreview} run={run} saveEdit={saveEdit} action={adminAction} />
    <Settlement selected={selected} selectedId={selected.id} outcome={outcome} setOutcome={setOutcome} preview={preview} setPreview={setPreview} run={run} action={adminAction} />
  </>;
}

