SELECT 'product' AS type,
       pr.product_review_id AS review_id,
       pr.product_id        AS target_id,
       pr.rating,
       pr.body,
       pr.created_at
FROM product_reviews pr
WHERE pr.user_id = :user_id
UNION ALL
SELECT 'seller'  AS type,
       sr.seller_review_id AS review_id,
       sr.seller_id        AS target_id,
       sr.rating,
       sr.body,
       sr.created_at
FROM seller_reviews sr
WHERE sr.user_id = :user_id
ORDER BY created_at DESC
LIMIT 5;
