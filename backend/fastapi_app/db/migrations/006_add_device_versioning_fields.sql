-- 006_add_device_versioning_fields.sql
-- This migration is idempotent: it will add app_version, os_version, last_update_check if not present.

ALTER TABLE devices
ADD COLUMN IF NOT EXISTS app_version VARCHAR(20);

ALTER TABLE devices
ADD COLUMN IF NOT EXISTS os_version VARCHAR(50);

ALTER TABLE devices
ADD COLUMN IF NOT EXISTS last_update_check TIMESTAMPTZ DEFAULT now();