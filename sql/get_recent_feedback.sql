SELECT *
FROM (
    SELECT 'product' AS type,
           pr.product_review_id AS review_id,
           pr.product_id        AS target_id,
           p.name               AS target_name,
           pr.rating,
           pr.body,
           pr.created_at
    FROM product_reviews pr
    JOIN products p ON p.id = pr.product_id
    WHERE pr.user_id = :user_id

    UNION ALL

    SELECT 'seller' AS type,
           sr.seller_review_id AS review_id,
           sr.seller_id        AS target_id,
           (u.firstname || ' ' || u.lastname) AS target_name,
           sr.rating,
           sr.body,
           sr.created_at
    FROM seller_reviews sr
    JOIN users u ON u.id = sr.seller_id
    WHERE sr.user_id = :user_id
) AS all_feedback
WHERE (:type = 'all' OR type = :type) 
ORDER BY created_at DESC
LIMIT :limit;
