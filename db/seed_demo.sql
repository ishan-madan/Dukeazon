-- 0) Ensure demo user (only if not exists)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM users WHERE email = 'demo@mini-amazon.com') THEN
    INSERT INTO users(email,password,firstname,lastname)
    VALUES ('demo@mini-amazon.com','demo123','Demo','User');
  END IF;
END$$;

-- 1) Seed product reviews for demo (products 1-6 if they exist), only if demo has none
WITH demo AS (
  SELECT id AS demo_id FROM users WHERE email='demo@mini-amazon.com'
),
p6 AS (
  SELECT id AS pid FROM products WHERE id BETWEEN 1 AND 6 ORDER BY id
)
INSERT INTO product_reviews(product_id, user_id, rating, body)
SELECT p.pid, d.demo_id, 5, 'Auto-seeded review for product ' || p.pid
FROM p6 p CROSS JOIN demo d
WHERE NOT EXISTS (SELECT 1 FROM product_reviews WHERE user_id = d.demo_id);

-- 2) Seed one seller review for demo (only if none yet)
WITH demo AS (
  SELECT id AS demo_id FROM users WHERE email='demo@mini-amazon.com'
),
seller AS (
  SELECT COALESCE(
           (SELECT id FROM users WHERE email <> 'demo@mini-amazon.com' ORDER BY id LIMIT 1),
           (SELECT demo_id FROM demo)
         ) AS seller_id
)
INSERT INTO seller_reviews(seller_id, user_id, rating, body)
SELECT s.seller_id, d.demo_id, 4, 'Auto-seeded seller review'
FROM demo d, seller s
WHERE NOT EXISTS (SELECT 1 FROM seller_reviews WHERE user_id = d.demo_id);

-- 3) Sequence sync 
SELECT setval(pg_get_serial_sequence('product_reviews','product_review_id'),
              COALESCE((SELECT MAX(product_review_id) FROM product_reviews),0), true);
SELECT setval(pg_get_serial_sequence('seller_reviews','seller_review_id'),
              COALESCE((SELECT MAX(seller_review_id) FROM seller_reviews),0), true);
