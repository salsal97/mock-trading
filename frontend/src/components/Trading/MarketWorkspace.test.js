import React from 'react';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MarketWorkspace from './MarketWorkspace';
import { apiGet, apiPost, apiRequest } from '../../utils/apiUtils';

jest.mock('../../utils/apiUtils', () => ({
  apiGet: jest.fn(), apiPost: jest.fn(), apiRequest: jest.fn(),
  handleApiError: e => e.message,
}));

const click = async element => { await act(async () => { fireEvent.click(element); }); };

it('supports a market lifecycle across administrator, maker and participant screens', async () => {
  let username = 'owner';
  let market = null;
  let trades = [];
  let quote = null;
  const currentMarket = () => ({...market, top_quotes: quote ? [quote] : [], personal_rank: quote && username === 'maker' ? 1 : null,
    user_trade: trades.find(t => t.user_username === username) || null});
  apiGet.mockImplementation(async url => {
    if (url === '/api/market/') return market ? [currentMarket()] : [];
    if (url === '/api/auth/user-profile/') return {username, balance: 1000};
    if (url.endsWith('/trades/')) return {trades: [...trades]};
    if (url.endsWith('/settlement-preview/')) return {settlement_price: '93.00', preview_version: 'reviewed-version', market_maker: {username:'maker'}, market_maker_impact:'-30.00', trades:[{trade_id:1, username:'trader', position:'BUY', trade_price:'90', profit_loss:'30.00'}]};
    if (url.endsWith('/settled-trades/')) return {trades: []};
    throw new Error(`Unexpected GET ${url}`);
  });
  apiPost.mockImplementation(async (url, data) => {
    if (url === '/api/market/') { market = {id:1, premise:data.premise, unit_value:10, created_by_username:'owner', status:'CREATED'}; return currentMarket(); }
    if (url.endsWith('/place_spread_bid/')) { quote = {id:1, user_username:'maker', spread_low:data.spread_low, spread_high:data.spread_high}; return {}; }
    if (url.endsWith('/manual_activate/')) { market = {...market, status:'OPEN', market_maker_username:'maker', final_spread_low:80, final_spread_high:90}; return {}; }
    if (url.endsWith('/place_trade/')) { trades = [{id:1, user_username:'trader', position:data.position === 'BUY' ? 'BUY' : 'SELL', price:data.position === 'BUY' ? 90 : 80}]; return {}; }
    if (url.endsWith('/close-trading/')) { market = {...market,status:'CLOSED'}; return {}; }
    if (url.endsWith('/set-settlement-price/')) { market = {...market,settlement_price:data.price}; return {}; }
    if (url.endsWith('/execute-settlement/')) { if (data.preview_version !== 'reviewed-version' || data.confirmed !== true) throw new Error('Wrong preview'); market = {...market,status:'SETTLED'}; return {}; }
    throw new Error(`Unexpected POST ${url}`);
  });
  apiRequest.mockImplementation(async (method,url,data) => { if (method !== 'patch' || !url.endsWith('/edit/')) throw new Error('Unexpected edit'); market = {...market,unit_value:data.unit_value}; });
  const mount = async name => { username=name; const view=render(<MemoryRouter future={{v7_startTransition: true, v7_relativeSplatPath: true}}><MarketWorkspace /></MemoryRouter>); await screen.findByText(`Signed in as ${name}`, {exact:false}); return view; };
  let view = await mount('owner');
  await click(screen.getByText('Create a market'));
  fireEvent.change(screen.getByLabelText('Question'), {target:{value:'Final score?'}});
  fireEvent.change(screen.getByLabelText('Bidding opens'), {target:{value:'2026-11-07T09:00'}});
  fireEvent.change(screen.getByLabelText('Bidding closes'), {target:{value:'2026-11-07T10:00'}});
  fireEvent.change(screen.getByLabelText('Trading closes'), {target:{value:'2026-11-07T11:00'}});
  await click(screen.getByRole('button',{name:'Create'}));
  await screen.findByText('Select maker and open trading'); view.unmount();
  view = await mount('maker'); await click(screen.getByRole('button',{name:'Final score?'}));
  fireEvent.change(screen.getByLabelText('Low'), {target:{value:'80'}}); fireEvent.change(screen.getByLabelText('High'), {target:{value:'90'}}); await click(screen.getByRole('button',{name:'Save quote'}));
  await screen.findByText('maker: 80–90'); expect(screen.getByText('Your rank: 1')).toBeInTheDocument(); view.unmount();
  view = await mount('owner'); await click(screen.getByRole('button',{name:'Final score?'})); await click(await screen.findByRole('button',{name:'Select maker and open trading'}));
  await screen.findByText('Quote: 80–90'); view.unmount();
  view = await mount('trader'); await click(screen.getByRole('button',{name:'Final score?'})); await click(await screen.findByRole('button',{name:'BUY'}));
  await screen.findByText('Your position: BUY at 90'); await click(screen.getByRole('button',{name:'SELL'})); await screen.findByText('Your position: SELL at 80');
  await click(screen.getByRole('button',{name:'BUY'})); await screen.findByText('Your position: BUY at 90'); view.unmount();
  view = await mount('maker'); await click(screen.getByRole('button',{name:'Final score?'}));
  fireEvent.change(await screen.findByLabelText('Hypothetical outcome value'), {target:{value:'93'}});
  await screen.findByText('Simulated maker P&L: -30.00'); view.unmount();
  view = await mount('owner'); await click(screen.getByRole('button',{name:'Final score?'})); await click(await screen.findByRole('button',{name:'Close trading'}));
  await screen.findByText('Settlement'); fireEvent.change(screen.getByLabelText('Outcome'), {target:{value:'93'}}); await click(screen.getByRole('button',{name:'Save outcome'}));
  await waitFor(() => expect(apiPost).toHaveBeenCalledWith('/api/market/1/set-settlement-price/', {price:'93'}));
  await waitFor(() => expect(screen.getByRole('button',{name:'Preview'})).toBeEnabled());
  await click(screen.getByRole('button',{name:'Preview'})); const table = await screen.findByRole('table'); expect(within(table).getByText('30.00')).toBeInTheDocument();
  expect(screen.getByText('Maker maker: -30.00')).toBeInTheDocument(); await waitFor(() => expect(screen.getByRole('button',{name:'Confirm settlement'})).toBeEnabled()); await click(screen.getByRole('button',{name:'Confirm settlement'}));
  await screen.findByText('Final outcome: 93'); expect(apiPost).toHaveBeenCalledWith('/api/market/1/execute-settlement/', {confirmed:true, preview_version:'reviewed-version'});
  expect(screen.queryByRole('alert')).not.toBeInTheDocument(); view.unmount();
});

it('shows participant names through seven and aggregates both sides at eight', async () => {
  let count = 7;
  const makeTrades = () => ['BUY', 'SELL'].flatMap((position) => Array.from({length:count}, (_, i) => ({id:`${position}${i}`, user_username:`${position}${i}`, position, price:position === 'BUY' ? 90 : 80})));
  apiGet.mockImplementation(async url => {
    if (url === '/api/market/') return [{id:2, premise:'Crowded', status:'OPEN', unit_value:10, created_by_username:'owner', market_maker_username:'maker', final_spread_low:80, final_spread_high:90}];
    if (url === '/api/auth/user-profile/') return {username:'viewer', balance:1000};
    if (url.endsWith('/trades/')) return {trades:makeTrades()};
    throw new Error(`Unexpected GET ${url}`);
  });
  let view = render(<MemoryRouter future={{v7_startTransition: true, v7_relativeSplatPath: true}}><MarketWorkspace /></MemoryRouter>);
  await click(await screen.findByRole('button', {name:'Crowded'}));
  await screen.findByText(/BUYERS: BUY0, BUY1/);
  expect(screen.getByText(/SELLERS: SELL0, SELL1/)).toHaveTextContent('SELL6');
  expect(screen.getByText(/BUYERS: BUY0, BUY1/)).toHaveTextContent('BUY6');
  view.unmount(); count = 8;
  view = render(<MemoryRouter future={{v7_startTransition: true, v7_relativeSplatPath: true}}><MarketWorkspace /></MemoryRouter>);
  await click(await screen.findByRole('button', {name:'Crowded'}));
  await screen.findByText('BUYERS: 8'); expect(screen.getByText('SELLERS: 8')).toBeInTheDocument();
  expect(screen.queryByText(/BUY0/)).not.toBeInTheDocument();
  expect(screen.queryByText(/SELL0/)).not.toBeInTheDocument();
  view.unmount();
});

it('ignores a delayed activity response after switching markets', async () => {
  let resolveOld;
  apiGet.mockImplementation(async url => {
    if (url === '/api/market/') return [
      {id:11, premise:'Old market', status:'OPEN', unit_value:10, created_by_username:'owner', market_maker_username:'viewer', final_spread_low:80, final_spread_high:90},
      {id:12, premise:'New market', status:'OPEN', unit_value:10, created_by_username:'owner', market_maker_username:'viewer', final_spread_low:30, final_spread_high:40},
    ];
    if (url === '/api/auth/user-profile/') return {username:'viewer',balance:1000};
    if (url === '/api/market/11/trades/') return new Promise(resolve => {resolveOld=resolve;});
    if (url === '/api/market/12/trades/') return {trades:[{id:2, user_username:'new_trader', position:'BUY', price:40}]};
    throw new Error(`Unexpected GET ${url}`);
  });
  const view = render(<MemoryRouter future={{v7_startTransition: true, v7_relativeSplatPath: true}}><MarketWorkspace /></MemoryRouter>);
  await click(await screen.findByRole('button',{name:'Old market'}));
  await waitFor(() => expect(resolveOld).toBeDefined());
  await click(screen.getByRole('button',{name:'New market'}));
  await screen.findByText('BUYERS: new_trader');
  await act(async () => { resolveOld({trades:[{id:1,user_username:'stale_trader',position:'BUY',price:90}]}); });
  expect(screen.getByText('BUYERS: new_trader')).toBeInTheDocument();
  expect(screen.queryByText(/stale_trader/)).not.toBeInTheDocument();
  view.unmount();
});
