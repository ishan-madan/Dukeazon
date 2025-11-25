\COPY Users FROM '/home/ubuntu/mini-amazon-skeleton/db/data/Users.csv' WITH DELIMITER ',' NULL '' CSV
-- since id is auto-generated; we need the next command to adjust the counter
-- for auto-generation so next INSERT will not clash with ids loaded above:
SELECT pg_catalog.setval('public.users_id_seq',
                         (SELECT MAX(id)+1 FROM Users),
                         false);

\COPY Products FROM '/home/ubuntu/mini-amazon-skeleton/db/data/Products.csv' WITH DELIMITER ',' NULL '' CSV
SELECT pg_catalog.setval('public.products_id_seq',
                         (SELECT MAX(id)+1 FROM Products),
                         false);

\COPY Purchases FROM '/home/ubuntu/mini-amazon-skeleton/db/data/Purchases.csv' WITH DELIMITER ',' NULL '' CSV
SELECT pg_catalog.setval('public.purchases_id_seq',
                         (SELECT MAX(id)+1 FROM Purchases),
                         false);

\COPY Cart FROM '/home/ubuntu/mini-amazon-skeleton/db/data/Cart.csv' WITH DELIMITER ',' NULL '' CSV;

\COPY ProductSeller FROM 'ProductSeller.csv' WITH DELIMITER ',' NULL '' CSV
SELECT pg_catalog.setval('public.productseller_id_seq',
                         (SELECT MAX(id)+1 FROM ProductSeller),
                         false);

\COPY product_reviews FROM '/home/ubuntu/mini-amazon-skeleton/db/data/ProductReviews.csv' WITH DELIMITER ',' NULL '' CSV HEADER;
SELECT pg_catalog.setval('public.product_reviews_product_review_id_seq',
                         (SELECT COALESCE(MAX(product_review_id)+1, 1) FROM product_reviews),
                         false);

\COPY seller_reviews FROM '/home/ubuntu/mini-amazon-skeleton/db/data/SellerReviews.csv' WITH DELIMITER ',' NULL '' CSV HEADER;
SELECT pg_catalog.setval('public.seller_reviews_seller_review_id_seq',
                         (SELECT COALESCE(MAX(seller_review_id)+1, 1) FROM seller_reviews),
                         false);


                         