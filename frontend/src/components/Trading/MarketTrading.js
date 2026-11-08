import React, { useState } from 'react';

export default function Trading({ selected, owner, maker, trades, run, action }) {
  const [simulation, setSimulation] = useState(90);
  if (!selected || selected.status !== 'OPEN') return null;
  const buyers = trades.filter(trade => trade.position === 'BUY');
  const sellers = trades.filter(trade => trade.position === 'SELL');
  // The maker takes the opposite side of every participant's position.
  const pnl = trades.reduce((sum, trade) => sum + (
    trade.position === 'BUY' ? Number(trade.price) - simulation : simulation - Number(trade.price)
  ) * Number(selected.unit_value), 0);

  return <>
    <p>Quote: {selected.final_spread_low}–{selected.final_spread_high}</p>
    {selected.user_trade && <p>Your position: {selected.user_trade.position === 'BUY' ? 'BUY' : 'SELL'} at {selected.user_trade.price}</p>}
    {!owner && !maker && <p>
      <button onClick={() => run(() => action('place_trade/', { position: 'BUY' }))}>BUY</button>{' '}
      <button onClick={() => run(() => action('place_trade/', { position: 'SELL' }))}>SELL</button>
    </p>}
    {[[ 'BUYERS', buyers ], [ 'SELLERS', sellers ]].map(([name, items]) => (
      <p key={name}>{name}: {items.length > 7 ? items.length : items.map(t => t.user_username).join(', ') || 'None'}</p>
    ))}
    {maker && <div>
      <label>Hypothetical outcome
        <input type="range" min="0" max="200" value={simulation} onChange={e => setSimulation(Number(e.target.value))} />
        <input aria-label="Hypothetical outcome value" type="number" value={simulation} onChange={e => setSimulation(Number(e.target.value))} />
      </label>
      <p>Simulated maker P&amp;L: {pnl.toFixed(2)}</p>
    </div>}
    {owner && <button onClick={() => run(() => action('close-trading/'))}>Close trading</button>}
  </>;
}

