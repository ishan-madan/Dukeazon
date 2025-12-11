# $\textsf{\color{skyblue} Dukeazon}$

## $\textsf{\color{lightgreen} Description}$
Mini Amazon (internally nicknamed **Dukeazon**) is a full-stack e-commerce platform that connects buyers and multiple sellers in a single marketplace. Users can browse products, manage carts, and place orders, while sellers can list items, track inventory, and view analytics. The platform includes social features such as product and seller reviews, subscription options for recurring deliveries, and a personalized account dashboard, providing a complete end-to-end shopping experience.

## $\textsf{\color{lightgreen} Demo Videos}$
- [Main Demo Video](https://youtu.be/bpOfXUBts10)
- [Additional Unmentioned Features Video](https://youtu.be/Ntojhm-CF6A)

## $\textsf{\color{lightgreen} Key Features}$

### $\textsf{\color{yellow} Users}$
**Overview:** Manages authentication, account information, balances, and user interactions.
<br/><br/>
**Key Features:**
- Register a new account or log in with email and password.
- Each user has a unique system-assigned ID; can update profile information except ID.
- Users have a balance that can be topped up or withdrawn.
- Browse purchase history, with summaries and links to detailed order pages.
- Public user view with account info and seller reviews if applicable.
- Search/filter purchase history by item.
- Quick pop-up preview for buyers or sellers.
- Email token verification required to log in after sign-up.

### $\textsf{\color{yellow} Products}$
**Overview:** Supports catalog browsing, product creation, and detailed views.
<br/><br/>
**Key Features:**
- Predefined categories; each product has a name, description, image, and price.
- Browse/search/filter products by category, keywords, and sort by price.
- Detailed product pages show all seller listings, available quantities, and reviews.
- Product creation/editing for sellers.
- Trusted seller filter with rating threshold badge.
- Suggested product section for similar items.
- Live preview for new product listings.

### $\textsf{\color{yellow} Carts}$
**Overview:** Handles adding products to carts, checkout, and order submission.
<br/><br/>
**Key Features:**
- Each user has a cart with line items for a specific product and seller.
- Update quantities, remove items, and submit orders.
- Inventory and balances checked during order submission; cart empties after checkout.
- Persistent cart contents.
- Detailed order pages showing fulfillment status.
- Save-for-later feature for items not yet added to the cart.
- Subscription options for select products (e.g., Frozen Treats) with frequency selection.
- Subscription management in the user account page.
- Dedicated payment and shipping step before finalizing orders.

### $\textsf{\color{yellow} Sellers}$
**Overview:** Manages seller inventory, order fulfillment, and analytics.
<br/><br/>
**Key Features:**
- Inventory page for adding, editing, or removing products.
- Browse and search order history for fulfilled or pending orders.
- Seller analytics dashboard with product stats, total revenue, and 30-day summaries.
- Filter orders by status or order ID.

### $\textsf{\color{yellow} Social}$
**Overview:** Provides product and seller review systems with voting and ranking.
<br/><br/>
**Key Features:**
- Submit a single rating/review per product or seller; edit/remove existing reviews.
- View all authored reviews in reverse chronological order.
- Display summary ratings and review counts for products and sellers.
- Upvote/remove votes on reviews; prioritize top helpful reviews automatically.
- Enhanced browsing features: sort by helpfulness/recency, filter by star rating, pagination for long lists.
- Product browse cards show additional indicators including top seller badge based on ratings.
- Sellers can view personalized reviews submitted by users about them.

# $\textsf{\color{skyblue} Dukeazon Program Walkthrough}$
## $\textsf{\color{lightgreen} First-Time Setup}$

```bash
git clone <your-fork-url>
cd mini-amazon-skeleton
./install.sh
db/setup.sh
```

`install.sh` performs three critical steps:
1. Generates `.flaskenv` with Flask configuration, a random `SECRET_KEY`, and database credentials pulled from your shell environment.
2. Configures Poetry to create an in-repo virtual environment (`.venv/`) and installs all dependencies listed in `pyproject.toml`.
3. Rebuilds the `amazon` PostgreSQL database by invoking `db/setup.sh`, which runs `db/create.sql` followed by `db/load.sql` against the seed data in `db/data/`.

Re-run `./install.sh` (or `db/setup.sh`) whenever you want a clean database.

---

## $\textsf{\color{lightgreen} Running the Application}$

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

Browse via `http://localhost:8080/`. Stop the server with `Ctrl+C`. Exit the Poetry shell with `exit`.

---

## $\textsf{\color{lightgreen} Database Management}$

- `db/create.sql` defines the authoritative schema: Users, Categories, Products, ProductSeller listings, Cart, SavedItems, Orders, OrderItems, Purchases, Subscriptions, and the social tables (`product_reviews`, `seller_reviews`, `review_votes`).
- `db/load.sql` seeds the tables using CSVs in `db/data/`. A larger dataset exists under `db/generated/`; pass that folder to `db/setup.sh generated`.
- `db/setup.sh` drops and recreates the database referenced in `.flaskenv`, then runs `create.sql` + `load.sql`.
- `db/migrations/ms4_schema_upgrade.sql` upgrades pre-MS4 databases.
- `db/migrations/ms5_shipping_address.sql` upgrades pre-final version databases.
- CSV password fields store **hashed** passwords. See `db/data/generated/gen.py` for the hashing pattern if adding new rows.

Connect directly with `psql` for debugging:

```bash
poetry run psql $DB_NAME        # uses credentials from .flaskenv via environment export
```

When editing the schema, modify `db/create.sql` and `db/load.sql`, then re-run `db/setup.sh`.

---

## $\textsf{\color{lightgreen} Using the Program}$

1. **User Registration & Authentication**
   - Register with email and password.
   - Verify account via emailed token (demo: printed in terminal).
   - Login using email and password.

2. **Browsing & Searching Products**
   - Browse products by category.
   - Search by keywords in product name or description.
   - Sort products by price or filter by seller rating.
   - View product details including seller listings and reviews.

3. **Cart & Orders**
   - Add products to cart from detailed product pages.
   - Update quantities, remove items, or save for later.
   - Checkout with payment and shipping information.
   - Order submission updates inventories and user/seller balances.
   - View order history with fulfillment status.

4. **Sellers**
   - Add products to inventory and manage stock.
   - Track sales through order history.
   - View seller analytics including total revenue and recent stats.
   - Filter orders by fulfillment status.

5. **Social Features**
   - Submit product and seller reviews (one per user).
   - Edit or delete your reviews.
   - View review summaries including average rating and helpful votes.
   - Upvote helpful reviews and prioritize top helpful reviews.
   - Enhanced browsing: filter by rating, sort by helpfulness or recency.

6. **Subscriptions**
   - Subscribe to recurring product deliveries (Frozen Treats).
   - Manage subscriptions via My Account page.
   - Cancel or modify subscriptions at any time.

7. **User Account & History**
   - View purchase history and order details.
   - Public user profile view for buyers and sellers.
   - Quick pop-up previews for buyer/seller info.
   - Search/filter purchase history by item.

---

## $\textsf{\color{lightgreen} Notes}$

- Use `db/setup.sh` to reset the database anytime.
- Server runs on port defined in `.flaskenv`.
- Poetry handles virtual environment management and dependency installation.
- All sensitive credentials are stored in `.flaskenv`.
- The system supports multiple sellers per product and tracks per-seller inventory.
- Social and subscription features add enhanced user engagement beyond basic e-commerce.
