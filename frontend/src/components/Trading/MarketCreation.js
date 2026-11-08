import React, { useState } from 'react';
import { apiPost } from '../../utils/apiUtils';

const initialForm = {
  premise: '',
  unit_value: '10',
  spread_bidding_open: '',
  spread_bidding_close_trading_open: '',
  trading_close: '',
};

const dates = [
  ['spread_bidding_open', 'Bidding opens'],
  ['spread_bidding_close_trading_open', 'Bidding closes'],
  ['trading_close', 'Trading closes'],
];

export default function MarketCreation({ run, refresh, selectMarket }) {
  const [form, setForm] = useState(initialForm);
  const update = event => setForm({ ...form, [event.target.name]: event.target.value });

  function submit(event) {
    event.preventDefault();
    run(async () => {
      const data = { ...form };
      dates.forEach(([key]) => { data[key] = data[key] ? new Date(data[key]).toISOString() : ''; });
      const market = await apiPost('/api/market/', data);
      await refresh();
      selectMarket(market);
    });
  }

  return (
    <details>
      <summary>Create a market</summary>
      <form onSubmit={submit}>
        <label>Question <input name="premise" required value={form.premise} onChange={update} /></label>
        <label> Unit value <input name="unit_value" required type="number" min="0.01" step="0.01" value={form.unit_value} onChange={update} /></label>
        <p>Bidding must open before it closes. Trading closes after bidding closes.</p>
        {dates.map(([key, label]) => (
          <label key={key}> {label} <input name={key} required type="datetime-local" value={form[key]} onChange={update} /></label>
        ))} <button>Create</button>
      </form>
    </details>
  );
}
