import { handleApiError } from './apiUtils';

describe('API validation errors', () => {
  let log;

  beforeEach(() => { log = jest.spyOn(console, 'error').mockImplementation(() => {}); });
  afterEach(() => { log.mockRestore(); });

  test('shows the server explanation for market-wide validation', () => {
    const message = 'Spread bidding close & trading open must be after spread bidding open';
    expect(handleApiError({ response: { status: 400, data: { non_field_errors: [message] } } })).toBe(message);
  });

  test('shows field validation errors', () => {
    const response = { status: 400, data: { unit_value: ['Ensure this value is greater than or equal to 0.01.'] } };
    expect(handleApiError({ response })).toBe('Ensure this value is greater than or equal to 0.01.');
  });
});
