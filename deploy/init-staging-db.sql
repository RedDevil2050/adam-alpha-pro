-- Create the grafana role if it doesn't exist
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'grafana') THEN
      CREATE ROLE grafana WITH LOGIN PASSWORD 'grafana_pass';
   END IF;
END $$;

-- Grant privileges to the grafana role
GRANT ALL PRIVILEGES ON DATABASE zion_staging TO grafana;