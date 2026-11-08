import { useCallback, useEffect, useRef, useState } from 'react';
import { apiGet, handleApiError } from '../../utils/apiUtils';

export default function useMarketData(setError) {
  const requestGeneration = useRef(0);
  const selection = useRef(null);
  const [markets, setMarkets] = useState([]);
  const [user, setUser] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [trades, setTrades] = useState([]);
  const selected = markets.find(market => market.id === selectedId);

  const refresh = useCallback(async id => {
    // Ignore both old refreshes and responses for a market the user has left.
    const generation = ++requestGeneration.current;
    const [list, profile] = await Promise.all([
      apiGet('/api/market/'),
      apiGet('/api/auth/user-profile/'),
    ]);
    if (generation !== requestGeneration.current || id !== selection.current) return list;
    setMarkets(list);
    setUser(profile);
    if (id) {
      const activity = await apiGet(`/api/market/${id}/trades/`);
      if (generation === requestGeneration.current && id === selection.current) {
        setTrades(activity.trades);
      }
    }
    return list;
  }, []);

  useEffect(() => {
    refresh(selectedId).catch(error => setError(handleApiError(error)));
  }, [refresh, selectedId, setError]);

  const status = selected?.status;
  useEffect(() => {
    // Finished markets do not need polling; opening another market restarts it.
    if (!selectedId || !['CREATED', 'OPEN'].includes(status)) return undefined;
    const timer = setInterval(() => {
      refresh(selectedId).catch(error => setError(handleApiError(error)));
    }, 5000);
    return () => clearInterval(timer);
  }, [refresh, selectedId, setError, status]);

  function select(id) {
    selection.current = id;
    requestGeneration.current += 1;
    setSelectedId(id);
    setTrades([]);
  }

  return { markets, user, selectedId, selected, trades, refresh, select };
}
