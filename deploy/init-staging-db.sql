-- Initialize staging database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create initial test user
INSERT INTO users (id, email, username, is_active)
VALUES (
    uuid_generate_v4(),
    'staging@example.com',
    'staging_user',
    true
) ON CONFLICT DO NOTHING;

-- Create staging watchlist
INSERT INTO watchlists (id, user_id, name, description)
SELECT 
    uuid_generate_v4(),
    users.id,
    'Staging Watchlist',
    'Test watchlist for staging environment'
FROM users
WHERE username = 'staging_user'
ON CONFLICT DO NOTHING;

-- Add test symbols to watchlist
INSERT INTO watchlist_items (watchlist_id, symbol)
SELECT 
    watchlists.id,
    unnest(ARRAY['TCS', 'INFY', 'RELIANCE']) as symbol
FROM watchlists
JOIN users ON users.id = watchlists.user_id
WHERE users.username = 'staging_user'
ON CONFLICT DO NOTHING;

-- Set up test alerts
INSERT INTO alerts (id, user_id, symbol, alert_type, condition, is_active)
SELECT 
    uuid_generate_v4(),
    users.id,
    'TCS',
    'price',
    'price > 3500',
    true
FROM users
WHERE username = 'staging_user'
ON CONFLICT DO NOTHING;