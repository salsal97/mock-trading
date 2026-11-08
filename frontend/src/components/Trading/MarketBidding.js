import React, { useState } from 'react';

export default function Bidding({ selected, owner, run, action }) {
  const [quote, setQuote] = useState({ low: '', high: '' });
  if (!selected || selected.status !== 'CREATED') return null;

  function submit(event) {
    event.preventDefault();
    run(() => action('place_spread_bid/', { spread_low: quote.low, spread_high: quote.high }));
  }

  return <>
    <h3>Current top quotes</h3>
    <ol>{(selected.top_quotes || []).map(q => (
      <li key={q.id}>{q.user_username}: {q.spread_low}–{q.spread_high}</li>
    ))}</ol>
    <p>Your rank: {selected.personal_rank || 'No quote'}</p>
    {!owner && <form onSubmit={submit}>
      <label>Low <input type="number" min="1" required value={quote.low} onChange={e => setQuote({ ...quote, low: e.target.value })} /></label>
      <label>High <input type="number" min="1" required value={quote.high} onChange={e => setQuote({ ...quote, high: e.target.value })} /></label>
      <button>Save quote</button>
    </form>}
    {owner && <button onClick={() => run(() => action('manual_activate/'))}>Select maker and open trading</button>}
  </>;
}

