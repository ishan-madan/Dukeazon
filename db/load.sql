\COPY Users (id, email, password, firstname, lastname, address, balance) FROM 'Users.csv' WITH DELIMITER ',' NULL '' CSV
-- since id is auto-generated; we need the next command to adjust the counter
-- for auto-generation so next INSERT will not clash with ids loaded above:
SELECT pg_catalog.setval('public.users_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM Users), 1),
                         false);

\COPY Categories (id, name) FROM 'Categories.csv' WITH DELIMITER ',' NULL '' CSV
SELECT pg_catalog.setval('public.categories_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM Categories), 1),
                         false);

\COPY Products (id, category_id, category_name, name, description, price, available, image_link) FROM 'Products.csv' WITH DELIMITER ',' NULL '' CSV
SELECT pg_catalog.setval('public.products_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM Products), 1),
                         false);

\COPY Purchases (id, uid, pid, time_purchased) FROM 'Purchases.csv' WITH DELIMITER ',' NULL '' CSV
SELECT pg_catalog.setval('public.purchases_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM Purchases), 1),
                         false);

\COPY ProductSeller (seller_id, product_id, price, quantity, is_active) FROM 'ProductSeller.csv' WITH DELIMITER ',' NULL '' CSV
SELECT pg_catalog.setval('public.productseller_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM ProductSeller), 1),
                         false);

\COPY Cart (user_id, product_id, listing_id, seller_id, unit_price, quantity) FROM 'Cart.csv' WITH DELIMITER ',' NULL '' CSV;

SELECT pg_catalog.setval('public.orders_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM Orders), 1),
                         false);

SELECT pg_catalog.setval('public.orderitems_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM OrderItems), 1),
                         false);
