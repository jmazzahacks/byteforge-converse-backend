-- Schema ownership moved to byteforge-converse-core >= 0.9.0.
-- Use dev_scripts/setup_database.py, or export the installed canonical SQL:
--   python -m byteforge_converse_core.schema > /tmp/converse-schema.sql
--   psql -v ON_ERROR_STOP=1 -f /tmp/converse-schema.sql
-- Fail explicitly so old automation cannot silently skip provisioning.
DO $$ BEGIN
    RAISE EXCEPTION 'Use packaged byteforge_converse_core.schema or dev_scripts/setup_database.py';
END $$;
