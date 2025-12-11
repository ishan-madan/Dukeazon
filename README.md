# Mini Amazon Skeleton

Mini Amazon (internally nicknamed **Dukeazon**) is the reference implementation for the CompSci 316/516 course project.  It is a Flask + PostgreSQL web app that demonstrates how to combine SQL-heavy models, a server-side rendered UI, and transactional business logic for a multi-seller e-commerce site.  This document replaces the legacy README and is the authoritative guide for cloning, running, and extending the project.

---

## Highlights
- Flask 2.3 app factory (`app/__init__.py`) with blueprints for the home page, catalog, seller tooling, cart/checkout, auth, and social features.
- SQLAlchemy Core (`app/db.py`) executes raw SQL so that schema and query tuning stay visible to students.
- PostgreSQL schema under `db/create.sql` with repeatable seeds in `db/load.sql` and `db/data/`.
- Modern UX expectations: multi-seller inventory, full cart + saved items workflow, shipping + payment capture, product and seller reviews with helpful votes, and opt-in reorder subscriptions.
- Tooling built for containers: Poetry manages the virtualenv, `.flaskenv` stores secrets, and helper scripts (`install.sh`, `db/setup.sh`) bootstrap everything in one command.

---

## Repository Layout

| Path | Description |
| --- | --- |
| `amazon.py` | WSGI entry point that instantiates the Flask app factory. |
| `app/` | All application code: configuration, blueprints, models, templates, static assets. |
| `app/models/` | Thin data-access objects with SQL helpers for products, cart, orders, reviews, subscriptions, etc. |
| `app/templates/` | Jinja2 templates (cards, product detail, cart, checkout, social feed, etc.). |
| `app/static/` | CSS, JS, and imagery shared by the templates. |
| `db/` | Schema (`create.sql`), sample loaders (`load.sql`, `data/`), migrations, generators, and `setup.sh`. |
| `sql/` | Standalone SQL utilities such as `get_recent_feedback.sql` (used by `app/social.py`). |
| `install.sh` | Bootstraps `.flaskenv`, installs dependencies with Poetry, and seeds the database. |
| `FAQ.md`, `TUTORIAL.md` | Supplemental class documents that answer common workflow questions. |

---

## Prerequisites
1. **Python 3.11** (Poetry enforces this version).
2. **Poetry** for dependency and virtualenv management.
3. **PostgreSQL client + server**.  In the Duke container images these are pre-installed; otherwise ensure that `psql`, `createdb`, and a reachable database server exist.
4. **A shell with access to the repository** (SSH into your container or run locally).

If your organization manages the database credentials (e.g., Duke containers), make sure the `PGUSER`, `PGPASSWORD`, `PGHOST`, and `PGPORT` environment variables are set before running `install.sh`.  Those values are copied into `.flaskenv`.

---

## First-Time Setup

```bash
git clone <your-fork-url>
cd mini-amazon-skeleton
./install.sh
```

`install.sh` performs three critical steps:
1. Generates `.flaskenv` with Flask configuration, a random `SECRET_KEY`, and database credentials pulled from your shell environment.
2. Configures Poetry to create an in-repo virtual environment (`.venv/`) and installs all dependencies listed in `pyproject.toml`.
3. Rebuilds the `amazon` PostgreSQL database by invoking `db/setup.sh`, which in turn runs `db/create.sql` followed by `db/load.sql` against the seed data in `db/data/`.

Re-run `./install.sh` (or `db/setup.sh`) whenever you want a clean database.

---

## Running the Application

```bash
poetry shell          # activates the virtualenv
flask run             # defaults to http://0.0.0.0:8080 per .flaskenv
```

Alternatively, skip the subshell:

```bash
poetry run flask run
```

Key environment variables are stored in `.flaskenv` and automatically loaded by Flask:
- `FLASK_APP=amazon.py`
- `FLASK_DEBUG=True` (disable or toggle for production-style runs)
- `FLASK_RUN_HOST` / `FLASK_RUN_PORT`
- Database credentials: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

When the server starts you can browse via `http://localhost:8080/` (or the forwarded port described in your container dashboard).

Stop the server with `Ctrl+C`.  Exit the Poetry shell with `exit`.

---

## Database Management

- `db/create.sql` defines the authoritative schema: Users, Categories, Products, ProductSeller listings, Cart, SavedItems, Orders, OrderItems, Purchases, Subscriptions, and the social tables (`product_reviews`, `seller_reviews`, `review_votes`).
- `db/load.sql` seeds the tables using CSVs in `db/data/`.  A larger dataset exists under `db/generated/`; pass that folder to `db/setup.sh generated`.
- `db/setup.sh` drops and recreates the database referenced in `.flaskenv`, then runs `create.sql` + `load.sql`.
- `db/migrations/ms4_schema_upgrade.sql` upgrades pre-MS4 databases.
- `db/migrations/ms5_shipping_address.sql` upgrades pre-final version databases.
- CSV password fields store **hashed** passwords.  See `db/data/generated/gen.py` for the hashing pattern if you need to craft additional rows.

Connect directly with `psql` for debugging:

```bash
poetry run psql $DB_NAME        # uses credentials from .flaskenv via environment export
```

When editing the schema, modify `db/create.sql` and `db/load.sql`, then re-run `db/setup.sh`.

---

## Application Architecture

- **App factory**: `app/__init__.py` wires together Flask, the custom `DB` helper (`app/db.py`), Flask-Login, template filters, and registers every blueprint.
- **Blueprints**
  - `index` (`app/index.py`): home page, category filtering, product search, rating summaries, and personalized order history.
  - `products` (`app/products.py`): catalog browsing, detail page with reviews, seller listings, subscriptions for eligible categories, and product creation/editing.
  - `product_seller` (`app/product_seller.py`): sellers manage listings, price/quantity, and order fulfillment.
  - `cart` (`app/cart.py`): cart CRUD, saved items, checkout, payment + shipping capture, and order detail pages.
  - `users` (`app/users.py`): authentication, registration (buyer or seller), profile updates, email verification, subscriptions dashboard, and review authoring for sellers.
  - `social` (`app/social.py`): seller review hub, helpful votes via `review_votes`, and the user’s combined feedback feed (powered by `sql/get_recent_feedback.sql`).
- **Models**: Instead of ORMs, each class in `app/models/` executes SQL via `app.db.execute()` or explicit SQLAlchemy `text()` blocks.  This keeps SQL visible and encourages reasoning about transactions.  Examples include `Cart.checkout()` (ensures serializable isolation), `Order.fulfill_item()`, and `Subscription.create_or_update()`.
- **Templates**: Stored under `app/templates/`.  Many templates share components (product cards, review modals).  Static files live under `app/static/`.
- **Emails**: `app/users.py` can send verification emails through SMTP.  Configure `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_USE_TLS`, and `MAIL_FROM` in `.flaskenv` (or the shell) to enable real delivery; otherwise messages are logged to the Flask logger.

---

## Feature Overview
- **Dual-role accounts**: Users can register as buyers or sellers.  Sellers get access to the listing + fulfillment tools.
- **Product catalog**: Browse by category, keyword search, and rating filters.  Detail pages include seller listings, review pagination, rating breakdowns, related-product suggestions, and subscription options for eligible goods.
- **Cart & checkout**: Add from any seller listing, update quantities inline, save for later, and capture shipping + payment details before placing a transactional order.  Checkout enforces inventory, user balance, and serializable consistency.
- **Orders**: Purchases appear in the buyer dashboard while sellers can fulfill their outstanding order items (mark fulfilled, update statuses, etc.).
- **Reviews & social feedback**: Buyers can post one product review per purchase and review sellers.  Helpful votes surface the most useful reviews and feed the `/social` experience.
- **Subscriptions**: Certain categories (e.g., frozen treats) allow recurring delivery opt-ins stored in the `Subscriptions` table.  Buyers can manage these from their profile.
- **Email verification**: New accounts must verify their email before signing in.  Tokens are issued via `User.issue_verification_token()` and processed under `/verify/<token>`.

---

## Common Workflows

1. **Reset the environment**
   ```bash
   git pull
   poetry install      # keeps dependencies current
   db/setup.sh         # rebuilds the amazon database using .flaskenv credentials
   ```

2. **Run locally without Poetry shell**
   ```bash
   poetry run flask run --reload --port 8080
   ```

3. **Inspect the database**
   ```bash
   poetry run psql $DB_NAME -c "SELECT COUNT(*) FROM Products;"
   ```

4. **Add a new feature**
   - Define / update tables in `db/create.sql`.
   - Build data-access helpers in `app/models/`.
   - Extend or create a blueprint in `app/`.
   - Create templates under `app/templates/` and optional static assets under `app/static/`.
   - Update `FAQ.md` or `this read.md` if the workflow impacts end users.

---

## Configuration & Secrets

`.flaskenv` is ignored by Git and should contain anything sensitive:

```
FLASK_APP=amazon.py
FLASK_DEBUG=True
SECRET_KEY=...
DB_NAME=amazon
DB_USER=...
DB_PASSWORD=...
MAIL_SERVER=smtp.example.com
MAIL_USERNAME=apikey
MAIL_PASSWORD=...
```

Load additional environment variables in your shell before `flask run` if you need to override values temporarily.  Never commit `.flaskenv`.

---

## Troubleshooting

- **Flask cannot connect to the database**: confirm that `.flaskenv` has the correct host/user/password and that `pg_isready -h $DB_HOST -p $DB_PORT` succeeds.
- **`psycopg2` build issues**: make sure PostgreSQL headers are installed (already available in Duke containers).  On macOS you may need `brew install postgresql`.
- **`poetry install` fails**: remove `.venv/` and retry (`rm -rf .venv && poetry install`).  Ensure you are on Python 3.11.
- **Email verification stuck**: set your `MAIL_*` variables or run with the defaults so emails log to the console; then copy/paste the verification URL manually.
- **Database drift**: rerun `db/setup.sh`.  Remember that running it wipes the existing `amazon` database.

---

## Additional Documentation
- `FAQ.md`: Logistics, environment quirks, and course-specific conventions.
- `TUTORIAL.md`: Step-by-step walkthrough for the MS requirements and UI flows.
- `LICENSE`: Licensing for derived work.

If you improve the skeleton (new docs, features, scripts), update this `read.md` alongside your code so new collaborators always have the latest instructions.

---

## Key Decisions
- **Blueprint boundaries**: Each blueprint owns the flows that most closely align with its audience; order history, fulfillment, and payments live with the `cart` blueprint so every order-related route stays co-located.
- **Single-role accounts**: A user is either a buyer or a seller (`Users.is_seller`). Sellers cannot shop, which simplifies authorization logic and prevents hybrid states during grading.
- **Listing-driven availability**: Product pricing and availability track the active `ProductSeller` listings. When the last seller of a product runs out, the catalog hides the product so users never see unpurchasable items.
- **Saved items as first-class rows**: Keeping `SavedItems` separate from `Cart` preserves clear semantics—saved-for-later entries can be cleared independently without touching cart contents or inventory math.
- **Timezone standardization**: All timestamps render via the `friendly_datetime` helper in Eastern Time, keeping demos and screenshots consistent with the EST-based teaching staff.
