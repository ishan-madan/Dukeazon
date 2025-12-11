-- Migration: add shipping address fields directly on Orders.
-- Run with: psql $DB_NAME -f db/migrations/ms5_shipping_address.sql
-- Safe to run multiple times.

BEGIN;

ALTER TABLE Orders
    ADD COLUMN IF NOT EXISTS shipping_street VARCHAR(255);

ALTER TABLE Orders
    ADD COLUMN IF NOT EXISTS shipping_city VARCHAR(255);

ALTER TABLE Orders
    ADD COLUMN IF NOT EXISTS shipping_state VARCHAR(64);

ALTER TABLE Orders
    ADD COLUMN IF NOT EXISTS shipping_zip VARCHAR(32);

ALTER TABLE Orders
    ADD COLUMN IF NOT EXISTS shipping_apt VARCHAR(255);

-- Backfill legacy orders with the profile address so sellers can still
-- see something meaningful in fulfillment views.
UPDATE Orders o
SET shipping_street = COALESCE(o.shipping_street, u.address)
FROM Users u
WHERE o.user_id = u.id
  AND o.shipping_street IS NULL;

COMMIT;
