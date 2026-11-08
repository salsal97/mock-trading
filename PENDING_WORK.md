# Pending Work

- Review migration 0009 and historical market data before applying changes to any existing database. The existing schema still stores `unit_price`, `initial_spread`, LONG/SHORT and quantity for compatibility; the API exposes `unit_value` and BUY/SELL, and new positions are one unit. Legacy balances and multi-unit positions have not been reconciled. A future data migration needs an explicit policy and a backup.
- Define cancellation, outcome evidence, disputes, and an audited correction/reversal procedure after settlement. Administrator material-change audit history is not yet implemented.
- Configure and monitor lifecycle maintenance in the intended environment. The default local suite uses SQLite and skips the two PostgreSQL-only tests; CI runs them against an isolated PostgreSQL service.
- Before any relaunch, review deployment settings and security, provision administrators deliberately, review retained server logs for sensitive registration data, and address the tracked publish-settings credentials with the owner through a separate authorized credential-rotation and repository-history process. No credentials were rotated here.
Always ensure code is concise and well commented
