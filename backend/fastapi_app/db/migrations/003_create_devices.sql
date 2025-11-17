-- 003_create_devices.sql
CREATE TABLE IF NOT EXISTS devices (
  device_id SERIAL PRIMARY KEY,
  device_uuid UUID NOT NULL UNIQUE,

  credential_type VARCHAR(20) NOT NULL DEFAULT 'token',
  credential_hash TEXT,              -- bcrypt/HMAC of token

  device_name TEXT,
  assigned_site TEXT,

  registered_by INTEGER REFERENCES users(employee_id),

  status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending|active|blocked|revoked

  -- Versioning fields
  app_version VARCHAR(20),
  os_version VARCHAR(50),
  last_update_check TIMESTAMPTZ DEFAULT now(),

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_uuid ON devices(device_uuid);
