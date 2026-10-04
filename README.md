# picnic-api

Unofficial Python client for the API of the [Picnic](https://picnic.app) online supermarket. A Python port of
[MRVDH/picnic-api](https://github.com/MRVDH/picnic-api) (v4.10.0). Not affiliated with Picnic.

Requires Python 3.14. The client is async (built on `httpx.AsyncClient`). Responses are parsed into
[Pydantic](https://docs.pydantic.dev) models.

## Installation

```bash
uv add git+https://github.com/JulesHuisman/picnic-api
```

## Quick start

All options are optional.

```python
from picnic_api import PicnicClient

client = PicnicClient(
    country_code="NL",  # "NL" (default), "DE" or "FR"
    auth_key="...",  # an existing auth key, to skip logging in
    api_version="15",  # default "15"
    url="...",  # default https://storefront-prod.<country>.picnicinternational.com/api/<api_version>
    device_id="...",  # x-picnic-did header, default "3C417201548B2E3B"
    agent="...",  # x-picnic-agent header, default "30100;1.246.1-15599;"
)
```

`PicnicClient` is an async context manager (`async with PicnicClient() as client:`) that closes its HTTP session on
exit. Pass `session=httpx.AsyncClient(...)` to
configure timeouts, proxies or a mock transport.

### Authentication

`auth.login()` stores the auth key on the client for later requests. When the result says
`second_factor_authentication_required`, request and verify a 2FA code:

```python
result = await client.auth.login(username="email", password="password")
if result.second_factor_authentication_required:
    await client.auth.generate_2fa_code(channel="SMS")
    await client.auth.verify_2fa_code(code="123456")
```

Login and 2FA failures with HTTP 401 raise `PicnicAuthError`, as does any request made with an expired or revoked
auth key, so callers can ask the user to log in again:

```python
from picnic_api import PicnicAuthError

try:
    cart = await client.cart.get_cart()
except PicnicAuthError:
    ...  # the auth key is no longer valid
```

### Usage examples

```python
from picnic_api.domains.cart.models import AddProductsItem

results = await client.catalog.search(query="Affligem blond")
await client.cart.add_product_to_cart(product_id="s1001524", count=2)
await client.cart.add_products_to_cart(
    products=[
        AddProductsItem(product_id="s11295810", quantity=2),
        AddProductsItem(product_id="s10000123", quantity=1),
    ]
)
slots = await client.cart.get_delivery_slots()
delivery = await client.delivery.get_delivery(delivery_id="delivery-id")
```

### Checkout issues

`cart.start_checkout()` raises `CheckoutIssueError` when the cart cannot proceed, for example for the alcohol age
check, which is resolved by retrying with its `resolve_key`:

```python
from picnic_api import CheckoutIssueError

cart = await client.cart.get_cart()
try:
    checkout = await client.cart.start_checkout(mts=cart.mts)
except CheckoutIssueError as issue:
    if not issue.is_age_verification_issue():
        raise
    checkout = await client.cart.start_checkout(mts=cart.mts, resolve_key=issue.resolve_key)
```

### Pages (Fusion and RSC)

Most pages are Fusion pages, fetched with `app.get_page(page_id)`. Some pages are served as a
[React Server Components](https://react.dev/reference/rsc/server-components) payload instead, depending on the page
and the `agent` version. Fetch those with `app.get_rsc_page(page_id)`, which splits the payload into its JSON rows.
Each method raises `UnexpectedPageFormatError` for the other format:

```python
from picnic_api import UnexpectedPageFormatError

try:
    page = await client.app.get_page(page_id="home_page_root")
except UnexpectedPageFormatError as error:
    rsc_page = await client.app.get_rsc_page(page_id=error.page_id)
```

Known RSC pages: `category-tree-root`, `profile-root` and `promo-group-deep-dive?promo_group_id=<id>`.

PML component trees inside pages change with every app release, so they are kept as raw JSON (`dict`). The page
envelope and all other responses are Pydantic models that keep unknown fields, so new API fields never break parsing;
`model.raw()` returns the data as the API sent it.

### Custom requests

For endpoints not covered by a service, use `send_request` directly. It returns the parsed JSON (or the raw text of
an RSC payload) and raises `PicnicError` on failures (`PicnicAuthError` for HTTP 401):

```python
await client.send_request(method="GET", path="/unknown/route")
await client.send_request(method="POST", path="/invite/friend", data={"email": "friend@example.com"})
```

## Services

| Service | Accessor | Description |
| --- | --- | --- |
| **App** | `client.app` | Bootstrap data, pages and deeplink resolution. |
| **Auth** | `client.auth` | Login, logout, 2FA and phone verification. |
| **Cart** | `client.cart` | Cart management, delivery slots and checkout. |
| **Catalog** | `client.catalog` | Product search, suggestions, details and images. |
| **Consent** | `client.consent` | Consent settings and GDPR declarations. |
| **Content** | `client.content` | Static content pages (FAQ, search empty state). |
| **Customer Service** | `client.customer_service` | Contact info, messages, reminders and parcels. |
| **Delivery** | `client.delivery` | Delivery history, live position, ratings and invoices. |
| **Payment** | `client.payment` | Payment profile and wallet transactions. |
| **Recipe** | `client.recipe` | Recipes and saving them, plus your own recipes: name, portions, ingredients, note, image. |
| **User** | `client.user` | User details, profile, suggestions and push tokens. |
| **User Onboarding** | `client.user_onboarding` | Household/business details and push subscriptions. |

Models live next to each service in `src/picnic_api/domains/<service>/models.py`.

Catalog and user-defined recipes share `RecipeSummary`, `RecipeDetails` and `RecipeIngredient`:

```python
saved = await client.recipe.get_saved_recipes()
own = await client.recipe.get_user_defined_recipes()
if saved:
    recipe = await client.recipe.get_recipe(recipe_id=saved[0].id, portions=2)
```

Omit `portions` to use the stored default. Pass `resolve_ingredient_names=True` to look up names missing from the
recipe tiles on the product pages, concurrently.

## Development

```bash
uv sync
uv run pytest
uv run ruff format && uv run ruff check
```

The unit tests mock the HTTP transport. The integration tests call the live API read-only and are skipped unless
`PICNIC_AUTH_KEY` is set (see `.env.example`):

```bash
uv run --env-file .env pytest -m integration --no-cov
```
