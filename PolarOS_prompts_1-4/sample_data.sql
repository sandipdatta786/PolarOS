-- =====================================================================
--  PolarOS — sample_data.sql
--  Hand-written events that exercise all four views.
--
--  Deliberately NOT generated. If the generator in Prompt 2 has a bug,
--  these rows are the fixed point you can trust: small enough that you
--  can compute every expected answer on paper before running anything.
--
--  Staged in two parts so the audit re-base is visible:
--    STAGE A — 15 events. Establishes stock, a crate journey, a roster,
--              and two field parties (one still out).
--    STAGE B —  2 events. A physical count that CONTRADICTS the running
--              arithmetic, plus one consumption after it.
--
--  Run:  sqlite3 sample.db < schema.sql
--        sqlite3 sample.db < sample_data.sql
--        sqlite3 sample.db < verify.sql
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- STAGE A
-- ---------------------------------------------------------------------

-- --- Cargo: one hazardous diesel drum, Goa -> Cape Town -> Maitri ------
-- Note the deliberate flaw modelled here: the crate is PACKED first and
-- only declared hazardous a day later. That gap is a real IMDG
-- compliance failure and the burn-down demo calls it out.

INSERT INTO events (event_id, node_id, seq, ts, priority, type, subject, payload) VALUES
('GOA-000001','GOA',1,'2026-10-05T06:00:00Z',5,'MANIFEST_CREATED','LOT-2',
 '{"lot_name":"Lot 2 — station spares","season":"2026-27","line_count":168,"created_by":"NCPOR-LOG-01"}'),

('GOA-000002','GOA',2,'2026-10-06T09:15:00Z',3,'CRATE_PACKED','CR-0001',
 '{"lot_id":"LOT-2","category":"diesel","item":"Diesel drum 200L","qty":200,"unit":"L","weight_kg":178.0,"volume_m3":0.25,"hazard":1,"destination":"MAITRI","needed_by":"2026-12-28","location":"GOA"}'),

('GOA-000003','GOA',3,'2026-10-07T11:00:00Z',1,'HAZARD_DECLARED','CR-0001',
 '{"un_class":"3","un_number":"UN1202","declared_by":"NCPOR-SAFETY","note":"declared 26h after packing — audit finding"}'),

('VESSEL-000001','VESSEL',1,'2026-11-02T14:20:00Z',3,'CRATE_SCANNED','CR-0001',
 '{"location":"CAPETOWN","scanner":"VESSEL_BOSUN","lot_id":"LOT-2"}'),

('VESSEL-000002','VESSEL',2,'2026-12-28T08:05:00Z',3,'CUSTODY_TRANSFERRED','CR-0001',
 '{"location":"MAITRI","custodian_from":"VESSEL_BOSUN","custodian_to":"MAITRI_STORE","lot_id":"LOT-2"}'),

-- --- Personnel: one member who travels, one who has not left Goa ------
('GOA-000004','GOA',4,'2026-08-01T05:00:00Z',2,'MEMBER_REGISTERED','M-001',
 '{"name":"A. Mehta","role":"Station Engineer","org":"NCPOR","cohort":"WINTER","base":"GOA"}'),

('GOA-000005','GOA',5,'2026-08-02T05:00:00Z',2,'MEMBER_REGISTERED','M-002',
 '{"name":"R. Nair","role":"Logistics Officer","org":"NCPOR","cohort":"SUMMER","base":"GOA"}'),

('GOA-000006','GOA',6,'2026-08-14T05:00:00Z',2,'CLEARANCE_RECORDED','M-001',
 '{"clearance":"medical","status":"CLEARED","valid_until":"2027-12-31"}'),

('MAITRI-000001','MAITRI',1,'2026-12-29T10:00:00Z',2,'MEMBER_MOVED','M-001',
 '{"location":"MAITRI","from_location":"VESSEL","reason":"station induction"}'),

-- --- Inventory: Maitri diesel, received then burned -------------------
('MAITRI-000002','MAITRI',2,'2026-12-28T09:00:00Z',4,'STOCK_RECEIVED','MAITRI:diesel',
 '{"qty":1000,"unit":"L","source":"LOT-2","crate_id":"CR-0001"}'),

('MAITRI-000003','MAITRI',3,'2027-01-05T18:00:00Z',4,'STOCK_CONSUMED','MAITRI:diesel',
 '{"qty":120,"unit":"L","headcount":7,"note":"generator daily run"}'),

('MAITRI-000004','MAITRI',4,'2027-01-06T18:00:00Z',4,'STOCK_CONSUMED','MAITRI:diesel',
 '{"qty":130,"unit":"L","headcount":7}'),

-- --- Field parties: FP-01 still out, FP-02 back safely ----------------
('BHARATI-000001','BHARATI',1,'2027-01-10T12:00:00Z',2,'PARTY_DEPARTED','FP-01',
 '{"station":"BHARATI","members":["M-004","M-009"],"destination":"Larsemann ridge line","eta_ts":"2027-01-10T20:00:00Z","radio_schedule_min":120}'),

('BHARATI-000002','BHARATI',2,'2027-01-11T02:00:00Z',2,'PARTY_DEPARTED','FP-02',
 '{"station":"BHARATI","members":["M-011"],"destination":"Grovnes automatic weather station","eta_ts":"2027-01-11T10:00:00Z","radio_schedule_min":60}'),

('BHARATI-000003','BHARATI',3,'2027-01-11T09:30:00Z',2,'PARTY_RETURNED','FP-02',
 '{"station":"BHARATI","members":["M-011"],"condition":"OK"}');

COMMIT;

-- ---------------------------------------------------------------------
-- Expected state after STAGE A — work these out before you run verify.sql
-- ---------------------------------------------------------------------
--   v_stock          MAITRI/diesel = 1000 - 120 - 130 = 750 L, never counted
--   v_crate_location CR-0001 at MAITRI, custodian MAITRI_STORE, hazard=1
--   v_roster         M-001 at MAITRI (via MOVED), M-002 at GOA (via REGISTERED)
--   v_open_parties   FP-01 only  (FP-02 closed by its return)
-- ---------------------------------------------------------------------


-- =====================================================================
-- STAGE B — the audit re-base
-- =====================================================================
-- The storekeeper dips the tanks on 7 Jan and finds 700 L, not 750.
-- Fifty litres were burned from a drum nobody logged. In a system that
-- STORED stock, someone would now edit a number and the history would
-- lie. Here we append one STOCK_COUNTED, and v_stock re-bases itself:
-- everything before the count is discarded, the count becomes the new
-- floor, and only movements after it are applied.

BEGIN;

INSERT INTO events (event_id, node_id, seq, ts, priority, type, subject, payload) VALUES
('MAITRI-000005','MAITRI',5,'2027-01-07T09:00:00Z',4,'STOCK_COUNTED','MAITRI:diesel',
 '{"qty":700,"unit":"L","counted_by":"MAITRI_STORE","method":"dip stick, 3 tanks"}'),

('MAITRI-000006','MAITRI',6,'2027-01-08T18:00:00Z',4,'STOCK_CONSUMED','MAITRI:diesel',
 '{"qty":50,"unit":"L","headcount":7}');

COMMIT;

-- ---------------------------------------------------------------------
-- Expected state after STAGE B
-- ---------------------------------------------------------------------
--   v_stock  MAITRI/diesel = 700 (counted) - 50 (consumed after the count)
--                          = 650 L, last_counted_ts 2027-01-07T09:00:00Z
--
--   NOT 1000 - 120 - 130 - 50 = 700.  The 250 L of pre-count consumption
--   is deliberately NOT subtracted again — the count already accounts for
--   it. If your view returns 700 here, your re-base is broken.
-- ---------------------------------------------------------------------
