import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { apiPost, handleApiError } from '../../utils/apiUtils';
import SettledTradesView from './SettledTradesView';
import useMarketData from './useMarketData';
import MarketCreation from './MarketCreation';
import MarketBidding from './MarketBidding';
import MarketTrading from './MarketTrading';
import MarketAdministration from './MarketAdministration';

export default function MarketWorkspace() {
  const [error, setError] = useState('');
  const { markets, user, selectedId, selected, trades, refresh, select } = useMarketData(setError);
  const [busy, setBusy] = useState(false);
  const [selectionVersion, setSelectionVersion] = useState(0);

  async function run(operation) {
    if (busy) return;
    setBusy(true);
    try {
      setError('');
      await operation();
    } catch (error) {
      setError(handleApiError(error));
    } finally {
      setBusy(false);
    }
  }

  async function action(path, data = {}) {
    await apiPost(`/api/market/${selectedId}/${path}`, data);
    await refresh(selectedId);
  }

  function selectMarket(market) {
    select(market.id);
    // Reset the administrator's inputs and preview, even when reselecting a market.
    setSelectionVersion(version => version + 1);
  }
  const owner = selected && user && selected.created_by_username === user.username;
  const maker = selected && user && selected.market_maker_username === user.username;


  return <main style={{ maxWidth: 1000, margin: '2rem auto', padding: '0 1rem' }}>
    <h1>Market workspace</h1>
    <Link to="/dashboard">Dashboard</Link>
    {user && <p>Signed in as {user.username} · Balance: {Number(user.balance).toFixed(2)} virtual dollars</p>}
    {error && <p role="alert">{error}</p>}
    <MarketCreation run={run} refresh={refresh} selectMarket={selectMarket} />
    <h2>All markets</h2>
    <ul>{markets.map(market => <li key={market.id}>
      <button disabled={busy} onClick={() => selectMarket(market)}>{market.premise}</button> {market.status}
    </li>)}</ul>
    {selected && <section><fieldset disabled={busy}>
      <h2>{selected.premise}</h2>
      <p>Status: {selected.status} · Unit value: {selected.unit_value} · Administrator: {selected.created_by_username} · Maker: {selected.market_maker_username || 'Not selected'}</p>
      <MarketBidding selected={selected} owner={owner} run={run} action={action} />
      <MarketTrading selected={selected} owner={owner} maker={maker} trades={trades} run={run} action={action} />
      {selected.status === 'SETTLED' && <><p>Final outcome: {selected.settlement_price}</p><SettledTradesView marketId={selected.id}/></>}
      {owner && <MarketAdministration key={selectionVersion} selected={selected} run={run} refresh={refresh} />}
    </fieldset></section>}
  </main>;
}
