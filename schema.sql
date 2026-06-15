PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS organizations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  org_type TEXT NOT NULL CHECK (org_type IN ('cooperative', 'refiner', 'buyer', 'regulator', 'auditor')),
  country TEXT NOT NULL,
  license_id TEXT NOT NULL UNIQUE,
  compliance_score INTEGER NOT NULL CHECK (compliance_score BETWEEN 0 AND 100),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  organization_id INTEGER NOT NULL REFERENCES organizations(id),
  full_name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL CHECK (role IN ('admin', 'regulator', 'cooperative', 'refiner', 'buyer', 'auditor')),
  password_hash TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mining_blocks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cooperative_id INTEGER NOT NULL REFERENCES organizations(id),
  block_code TEXT NOT NULL UNIQUE,
  district TEXT NOT NULL,
  latitude REAL NOT NULL,
  longitude REAL NOT NULL,
  radius_km REAL NOT NULL,
  license_status TEXT NOT NULL CHECK (license_status IN ('active', 'review', 'suspended')),
  environmental_status TEXT NOT NULL CHECK (environmental_status IN ('clear', 'watch', 'breach')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gold_batches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_code TEXT NOT NULL UNIQUE,
  mining_block_id INTEGER NOT NULL REFERENCES mining_blocks(id),
  cooperative_id INTEGER NOT NULL REFERENCES organizations(id),
  current_holder_id INTEGER NOT NULL REFERENCES organizations(id),
  status TEXT NOT NULL CHECK (status IN ('allocated', 'in_transit', 'refining', 'certified', 'exported', 'held')),
  gross_weight_g REAL NOT NULL CHECK (gross_weight_g > 0),
  purity_pct REAL NOT NULL CHECK (purity_pct BETWEEN 0 AND 100),
  fair_trade_premium_pct REAL NOT NULL DEFAULT 7.5,
  extraction_date TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ledger_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER NOT NULL REFERENCES gold_batches(id),
  actor_org_id INTEGER NOT NULL REFERENCES organizations(id),
  event_type TEXT NOT NULL,
  location_lat REAL,
  location_lng REAL,
  notes TEXT NOT NULL,
  event_hash TEXT NOT NULL,
  previous_hash TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS escrows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER NOT NULL REFERENCES gold_batches(id),
  buyer_id INTEGER NOT NULL REFERENCES organizations(id),
  seller_id INTEGER NOT NULL REFERENCES organizations(id),
  amount_usd REAL NOT NULL CHECK (amount_usd > 0),
  status TEXT NOT NULL CHECK (status IN ('pending', 'funded', 'released', 'disputed')),
  release_conditions TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  released_at TEXT
);

CREATE TABLE IF NOT EXISTS ethical_audits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER NOT NULL REFERENCES gold_batches(id),
  auditor_id INTEGER NOT NULL REFERENCES organizations(id),
  audit_type TEXT NOT NULL CHECK (audit_type IN ('labor', 'environmental', 'chain_of_custody', 'export')),
  score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
  finding TEXT NOT NULL,
  corrective_action TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gold_prices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  price_usd_per_gram REAL NOT NULL CHECK (price_usd_per_gram > 0),
  captured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER REFERENCES users(id),
  action TEXT NOT NULL,
  ip_address TEXT NOT NULL,
  details TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_batches_status ON gold_batches(status);
CREATE INDEX IF NOT EXISTS idx_ledger_batch ON ledger_events(batch_id, created_at);
CREATE INDEX IF NOT EXISTS idx_escrows_status ON escrows(status);
CREATE INDEX IF NOT EXISTS idx_audits_batch ON ethical_audits(batch_id);
