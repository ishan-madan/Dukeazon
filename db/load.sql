\COPY Users (id, email, password, firstname, lastname, address, balance, is_seller, created_at) FROM 'Users.csv' WITH (FORMAT csv, DELIMITER ',', NULL '', HEADER false);
-- since id is auto-generated; we need the next command to adjust the counter
-- for auto-generation so next INSERT will not clash with ids loaded above:
SELECT pg_catalog.setval('public.users_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM Users), 1),
                         false);

\COPY Categories (id, name) FROM 'Categories.csv' WITH (FORMAT csv, DELIMITER ',', NULL '', HEADER false);
SELECT pg_catalog.setval('public.categories_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM Categories), 1),
                         false);

\COPY Products (id, category_id, category_name, name, description, price, available, image_link) FROM 'Products.csv' WITH (FORMAT csv, DELIMITER ',', NULL '', HEADER false);
SELECT pg_catalog.setval('public.products_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM Products), 1),
                         false);

\COPY Purchases (id, uid, pid, time_purchased) FROM 'Purchases.csv' WITH (FORMAT csv, DELIMITER ',', NULL '', HEADER false);
SELECT pg_catalog.setval('public.purchases_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM Purchases), 1),
                         false);

\COPY ProductSeller (id, seller_id, product_id, price, quantity, is_active) FROM 'ProductSeller.csv' WITH (FORMAT csv, DELIMITER ',', NULL '', HEADER false);
SELECT pg_catalog.setval('public.productseller_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM ProductSeller), 1),
                         false);

\COPY Cart (user_id, product_id, listing_id, seller_id, unit_price, quantity) FROM 'Cart.csv' WITH (FORMAT csv, DELIMITER ',', NULL '', HEADER false);

\COPY SavedItems (user_id, product_id, listing_id, seller_id, unit_price, quantity, saved_at) FROM 'SavedItems.csv' WITH (FORMAT csv, DELIMITER ',', NULL '', HEADER false);

\COPY Orders (id, user_id, created_at, status, total_amount, shipping_street, shipping_city, shipping_state, shipping_zip, shipping_apt) FROM 'Orders.csv' WITH (FORMAT csv, DELIMITER ',', NULL '', HEADER false);

\COPY OrderItems (id, order_id, listing_id, seller_id, product_id, unit_price, quantity, subtotal, fulfilled, fulfilled_at, fulfillment_status) FROM 'OrderItems.csv' WITH (FORMAT csv, DELIMITER ',', NULL '', HEADER false);

SELECT pg_catalog.setval('public.orders_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM Orders), 1),
                         false);

SELECT pg_catalog.setval('public.orderitems_id_seq',
                         COALESCE((SELECT MAX(id)+1 FROM OrderItems), 1),
                         false);


\COPY product_reviews FROM 'ProductReviews.csv' WITH (FORMAT csv, DELIMITER ',', NULL '', HEADER false);
SELECT pg_catalog.setval('public.product_reviews_product_review_id_seq',
                         (SELECT COALESCE(MAX(product_review_id)+1, 1) FROM product_reviews),
                         false);

\COPY seller_reviews FROM 'SellerReviews.csv' WITH (FORMAT csv, DELIMITER ',', NULL '', HEADER false);
SELECT pg_catalog.setval('public.seller_reviews_seller_review_id_seq',
                         (SELECT COALESCE(MAX(seller_review_id)+1, 1) FROM seller_reviews),
                         false);

\COPY review_votes (vote_id, review_type, review_id, user_id, vote, created_at) FROM 'ReviewVotes.csv' WITH (FORMAT csv, DELIMITER ',', NULL '', HEADER false);
SELECT pg_catalog.setval('public.review_votes_vote_id_seq',
                         (SELECT COALESCE(MAX(vote_id)+1, 1) FROM review_votes),
                         false);

                         
