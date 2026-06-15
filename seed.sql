INSERT OR IGNORE INTO organizations (id, name, org_type, country, license_id, compliance_score) VALUES
(1, 'Karamoja Women Miners Cooperative', 'cooperative', 'Uganda', 'UG-KRM-COOP-001', 91),
(2, 'Moroto Responsible Refiners Ltd', 'refiner', 'Uganda', 'UG-RFN-044', 88),
(3, 'Nile Ethical Exports', 'buyer', 'Uganda', 'UG-BUY-220', 94),
(4, 'Uganda Minerals Regulator', 'regulator', 'Uganda', 'UG-REG-001', 100),
(5, 'FairEarth Audit Partners', 'auditor', 'Kenya', 'EA-AUD-771', 96);

INSERT OR IGNORE INTO users (id, organization_id, full_name, email, role, password_hash) VALUES
(1, 4, 'Amina Okello', 'regulator@goldtrace.ug', 'regulator', 'PBKDF2_PLACEHOLDER'),
(2, 1, 'Grace Nakiru', 'coop@goldtrace.ug', 'cooperative', 'PBKDF2_PLACEHOLDER'),
(3, 2, 'David Lokiru', 'refiner@goldtrace.ug', 'refiner', 'PBKDF2_PLACEHOLDER'),
(4, 3, 'Leah Achieng', 'buyer@goldtrace.ug', 'buyer', 'PBKDF2_PLACEHOLDER'),
(5, 4, 'Nabachwa Stella', 'stella.nabachwa@goldtrace.ug', 'regulator', 'PBKDF2_PLACEHOLDER');

INSERT OR IGNORE INTO mining_blocks (id, cooperative_id, block_code, district, latitude, longitude, radius_km, license_status, environmental_status) VALUES
(1, 1, 'KRM-MRT-A12', 'Moroto', 2.5332, 34.6643, 4.2, 'active', 'clear'),
(2, 1, 'KRM-NPK-C07', 'Napak', 2.2511, 34.2508, 3.1, 'active', 'watch'),
(3, 1, 'KRM-KTN-B03', 'Kotido', 2.9806, 34.1334, 2.7, 'review', 'clear');

INSERT OR IGNORE INTO gold_batches (id, batch_code, mining_block_id, cooperative_id, current_holder_id, status, gross_weight_g, purity_pct, fair_trade_premium_pct, extraction_date) VALUES
(1, 'GT-2026-0001', 1, 1, 2, 'refining', 1250.5, 87.4, 8.0, '2026-06-03'),
(2, 'GT-2026-0002', 2, 1, 1, 'allocated', 780.0, 83.2, 7.5, '2026-06-07'),
(3, 'GT-2026-0003', 3, 1, 3, 'certified', 1535.8, 90.1, 9.0, '2026-05-29'),
(4, 'GT-2026-0004', 1, 1, 3, 'exported', 990.3, 88.8, 8.5, '2026-05-19');

INSERT OR IGNORE INTO ledger_events (id, batch_id, actor_org_id, event_type, location_lat, location_lng, notes, event_hash, previous_hash, created_at) VALUES
(1, 1, 1, 'ore_allocated', 2.5332, 34.6643, 'Ore allocated from licensed Moroto block.', 'h-0001-a', NULL, '2026-06-03 08:15:00'),
(2, 1, 2, 'refiner_received', 2.5299, 34.6680, 'Received sealed consignment; weight verified.', 'h-0001-b', 'h-0001-a', '2026-06-04 14:20:00'),
(3, 2, 1, 'ore_allocated', 2.2511, 34.2508, 'Allocation pending transport escrow funding.', 'h-0002-a', NULL, '2026-06-07 09:05:00'),
(4, 3, 5, 'audit_passed', 2.9806, 34.1334, 'Chain of custody and labor audit passed.', 'h-0003-a', NULL, '2026-06-01 10:40:00'),
(5, 4, 3, 'export_cleared', 0.3156, 32.5811, 'Export documentation cleared for certified buyer.', 'h-0004-a', NULL, '2026-05-25 16:30:00');

INSERT OR IGNORE INTO escrows (id, batch_id, buyer_id, seller_id, amount_usd, status, release_conditions, created_at, released_at) VALUES
(1, 1, 3, 1, 84250.00, 'funded', 'Release after refiner assay and ethical audit score above 85.', '2026-06-04 10:00:00', NULL),
(2, 2, 3, 1, 49620.00, 'pending', 'Fund before transport dispatch from Napak block.', '2026-06-07 11:00:00', NULL),
(3, 3, 3, 1, 108900.00, 'released', 'Released after certificate and export invoice verification.', '2026-06-01 12:00:00', '2026-06-05 09:30:00');

INSERT OR IGNORE INTO ethical_audits (id, batch_id, auditor_id, audit_type, score, finding, corrective_action, created_at) VALUES
(1, 1, 5, 'chain_of_custody', 92, 'Seals intact and ledger continuity verified.', NULL, '2026-06-04 15:20:00'),
(2, 2, 5, 'environmental', 81, 'Water settling controls require inspection before next extraction.', 'Install second settling pond within 14 days.', '2026-06-08 10:10:00'),
(3, 3, 5, 'labor', 95, 'Worker payment records and PPE controls meet fair-trade standard.', NULL, '2026-06-01 11:00:00'),
(4, 4, 5, 'export', 93, 'Export documents match certified batch manifest.', NULL, '2026-05-25 15:50:00');

INSERT OR IGNORE INTO gold_prices (id, source, price_usd_per_gram, captured_at) VALUES
(1, 'LBMA Reference', 74.21, '2026-06-10 08:00:00'),
(2, 'LBMA Reference', 74.88, '2026-06-11 08:00:00'),
(3, 'LBMA Reference', 75.42, '2026-06-12 08:00:00'),
(4, 'LBMA Reference', 76.05, '2026-06-13 08:00:00'),
(5, 'LBMA Reference', 75.73, '2026-06-14 08:00:00'),
(6, 'LBMA Reference', 76.30, '2026-06-15 08:00:00');
