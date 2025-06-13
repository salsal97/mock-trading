# Market App

The Market app handles the creation and management of trading markets in the mock trading application using Django REST Framework ViewSets.

## Model: Market

### Fields
- `premise` (CharField): The market premise or question (max 500 chars)
- `unit_price` (FloatField): Base unit price for trading
- `spread_low` (IntegerField): Lower bound of the spread
- `spread_high` (IntegerField): Upper bound of the spread
- `created_by` (ForeignKey): User who created this market
- `status` (CharField): Current status with choices:
  - `CREATED`: Market created but not yet open
  - `OPEN`: Market is open for trading
  - `CLOSED`: Market closed, no more trading
  - `SETTLED`: Market settled with final outcome
- `spread_bidding_open` (DateTimeField): When spread bidding opens
- `spread_bidding_close` (DateTimeField): When spread bidding closes
- `trading_open` (DateTimeField): When trading opens
- `trading_close` (DateTimeField): When trading closes
- `outcome` (IntegerField): Final outcome (set when settled)
- `created_at` (DateTimeField): Auto-generated creation timestamp
- `updated_at` (DateTimeField): Auto-generated update timestamp

### Properties
- `is_spread_bidding_active`: Boolean indicating if spread bidding is currently active
- `is_trading_active`: Boolean indicating if trading is currently active
- `can_be_settled`: Boolean indicating if market can be settled

## API Endpoints (ViewSet-based)

### MarketViewSet - `/api/market/`

**Permissions:**
- **GET operations**: Available to all authenticated users
- **POST/PUT/PATCH/DELETE operations**: Admin users only (staff or superuser)

**Standard ViewSet Endpoints:**
- `GET /api/market/` - List all markets with optional filtering
  - Query parameters:
    - `status`: Filter by market status
    - `active_only=true`: Show only actively trading markets
- `POST /api/market/` - Create new market (admin only)
- `GET /api/market/{id}/` - Get specific market details
- `PUT /api/market/{id}/` - Update entire market (admin only)
- `PATCH /api/market/{id}/` - Partial update market (admin only)
- `DELETE /api/market/{id}/` - Delete market (admin only, only if CREATED status)

**Custom Actions:**
- `POST /api/market/{id}/settle/` - Settle market with outcome (admin only)
- `GET /api/market/stats/` - Get market statistics (admin only)

## Permissions

### IsAdminOrReadOnly (Custom Permission)
- **Read permissions**: Any authenticated user
- **Write permissions**: Only admin users (staff or superuser)

## Serializers

### MarketSerializer
Full market serialization with read-only computed fields for list/detail views.

### MarketCreateSerializer
For creating new markets with validation:
- Ensures proper timing sequence
- Validates spread ranges
- Excludes read-only fields

### MarketUpdateSerializer
For updating market status with validation:
- Enforces valid status transitions
- Requires outcome when settling
- Only allows status and outcome updates

## Status Transitions

Valid status transitions:
- `CREATED` → `OPEN`
- `OPEN` → `CLOSED`
- `CLOSED` → `SETTLED`
- `SETTLED` → (no further transitions)

## Admin Interface

The Market model is registered in Django admin with:
- List view showing key information
- Filtering by status, creator, and dates
- Search by premise and creator username
- Organized fieldsets for easy editing
- Read-only computed fields

## Testing

Comprehensive tests covering:
- Model functionality and properties
- ViewSet permissions (admin vs regular users)
- API endpoint functionality
- Authentication requirements
- Market creation and management

## Usage Examples

### Listing Markets (Any authenticated user)
```bash
GET /api/market/
Authorization: Bearer <jwt_token>
```

### Creating a Market (Admin only)
```bash
POST /api/market/
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json

{
    "premise": "Will the stock market close higher today?",
    "unit_price": 1.0,
    "spread_low": 45,
    "spread_high": 55,
    "spread_bidding_open": "2025-06-13T09:00:00Z",
    "spread_bidding_close": "2025-06-13T10:00:00Z",
    "trading_open": "2025-06-13T10:30:00Z",
    "trading_close": "2025-06-13T16:00:00Z"
}
```

### Settling a Market (Admin only)
```bash
POST /api/market/{id}/settle/
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json

{
    "outcome": 52
}
```

### Getting Market Statistics (Admin only)
```bash
GET /api/market/stats/
Authorization: Bearer <admin_jwt_token>
```

## URL Structure

The market app uses Django REST Framework's DefaultRouter, which automatically generates:
- Standard CRUD endpoints
- Custom action endpoints
- Proper URL naming conventions (market-list, market-detail, etc.)

All endpoints are accessible under `/api/market/` as requested. 