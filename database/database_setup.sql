-- =====================================================================
-- MoMo SMS Data Processing System - Database Setup
-- Week 2 deliverable: Urban Mobility Data Explorer (MoMo ETL) team
--
-- Target engine : MySQL 8.0.16+ (required for CHECK constraint enforcement;
--                  on 5.7/8.0.0-8.0.15 CHECK clauses parse but are ignored)
-- How to run    : mysql -u <user> -p < database_setup.sql
-- =====================================================================

DROP DATABASE IF EXISTS momo_sms;
CREATE DATABASE momo_sms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE momo_sms;

-- ---------------------------------------------------------------------
-- 1. users
--    People or entities that appear as a party (sender/receiver/agent)
--    in a transaction. Populated from names + phone numbers found in
--    the SMS body text.
--
--    NOTE: momo.xml masks some phone numbers ("*********013") and shows
--    others in full ("250791666666") for the same real-world contact,
--    and MoMo does not guarantee a phone number is present at all
--    (e.g. bank deposits only show a settlement account number). A
--    surrogate PK is therefore used and phone_number is deliberately
--    NOT unique/NOT NOT-NULL - see docs/database_design.md.
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id         INT AUTO_INCREMENT PRIMARY KEY,
    full_name       VARCHAR(100)        NOT NULL COMMENT 'Counterparty name as it appears in the SMS body',
    phone_number    VARCHAR(15)         NULL COMMENT 'E.164-ish MSISDN when available; may be masked or absent',
    is_phone_masked BOOLEAN             NOT NULL DEFAULT FALSE COMMENT 'TRUE if phone_number contains asterisk-masked digits',
    user_type       ENUM('CUSTOMER','AGENT','MERCHANT','SYSTEM') NOT NULL DEFAULT 'CUSTOMER'
                                        COMMENT 'Role this party most commonly plays',
    created_at      DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME            NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_users_phone_format CHECK (
        phone_number IS NULL OR phone_number REGEXP '^[0-9*]{6,15}$'
    )
) ENGINE=InnoDB COMMENT='Sender/receiver/agent parties referenced by transactions';

CREATE INDEX idx_users_phone ON users (phone_number);
CREATE INDEX idx_users_name ON users (full_name);

-- ---------------------------------------------------------------------
-- 2. transaction_categories
--    Lookup table of the transaction types observed in the XML body
--    text (see etl/categorize.py rules).
-- ---------------------------------------------------------------------
CREATE TABLE transaction_categories (
    category_id      INT AUTO_INCREMENT PRIMARY KEY,
    category_code    VARCHAR(30)   NOT NULL UNIQUE COMMENT 'Stable machine key used by etl/categorize.py',
    category_name    VARCHAR(100)  NOT NULL COMMENT 'Human-readable label for the dashboard',
    description      VARCHAR(255)  NULL,
    default_direction ENUM('CREDIT','DEBIT') NOT NULL COMMENT 'Whether this category typically increases or decreases balance'
) ENGINE=InnoDB COMMENT='Lookup of MoMo transaction types (payment, transfer, deposit, withdrawal, etc.)';

-- ---------------------------------------------------------------------
-- 3. sms_messages
--    One row per raw <sms> element from the XML backup, kept verbatim
--    for traceability/auditing and re-processing.
-- ---------------------------------------------------------------------
CREATE TABLE sms_messages (
    sms_id            INT AUTO_INCREMENT PRIMARY KEY,
    address           VARCHAR(30)   NOT NULL COMMENT 'SMS sender address, e.g. "M-Money"',
    sms_protocol      TINYINT       NULL,
    sms_type          TINYINT       NULL COMMENT 'Android SMS type attribute (1 = inbox)',
    body              TEXT          NOT NULL COMMENT 'Raw, unparsed SMS body text',
    service_center    VARCHAR(20)   NULL,
    sms_timestamp     DATETIME      NOT NULL COMMENT 'Parsed from the date (epoch ms) attribute',
    sms_date_sent     DATETIME      NULL,
    readable_date     VARCHAR(40)   NULL COMMENT 'Original readable_date attribute, kept for debugging',
    raw_hash          CHAR(64)      NOT NULL UNIQUE COMMENT 'SHA-256 of the raw <sms> element; de-dupes re-ingested backups',
    is_parsed         BOOLEAN       NOT NULL DEFAULT FALSE COMMENT 'Set TRUE once a transaction row exists for this message',
    ingested_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='Verbatim staging table for every SMS in data/raw/momo.xml';

CREATE INDEX idx_sms_timestamp ON sms_messages (sms_timestamp);
CREATE INDEX idx_sms_is_parsed ON sms_messages (is_parsed);

-- ---------------------------------------------------------------------
-- 4. transactions
--    One row per successfully parsed MoMo transaction. 1:1 with the
--    sms_messages row it was extracted from.
-- ---------------------------------------------------------------------
CREATE TABLE transactions (
    transaction_id            INT AUTO_INCREMENT PRIMARY KEY,
    sms_id                    INT           NOT NULL UNIQUE COMMENT '1:1 link back to the raw SMS this was parsed from',
    category_id               INT           NOT NULL,
    financial_transaction_id  VARCHAR(30)   NULL UNIQUE COMMENT 'MoMo "Financial Transaction Id" / TxId - natural idempotency key',
    external_transaction_id   VARCHAR(30)   NULL COMMENT 'Third-party "External Transaction Id" when present (e.g. merchant txns)',
    amount                    DECIMAL(12,2) NOT NULL,
    fee                       DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    balance_after             DECIMAL(12,2) NULL COMMENT 'Account balance reported after this transaction, when the SMS includes it',
    currency                  CHAR(3)       NOT NULL DEFAULT 'RWF',
    direction                 ENUM('CREDIT','DEBIT') NOT NULL COMMENT 'CREDIT increases the account balance, DEBIT decreases it',
    status                    ENUM('COMPLETED','FAILED','PENDING','REVERSED') NOT NULL DEFAULT 'COMPLETED',
    transaction_datetime      DATETIME      NOT NULL COMMENT 'Timestamp embedded in the SMS body, e.g. "at 2024-05-10 16:30:51"',
    reverses_transaction_id   INT           NULL COMMENT 'Self-reference: set when status=REVERSED and the original transaction is known',
    created_at                DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_txn_sms
        FOREIGN KEY (sms_id) REFERENCES sms_messages (sms_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_txn_category
        FOREIGN KEY (category_id) REFERENCES transaction_categories (category_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_txn_reversal
        FOREIGN KEY (reverses_transaction_id) REFERENCES transactions (transaction_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_txn_amount_positive CHECK (amount > 0),
    CONSTRAINT chk_txn_fee_nonnegative CHECK (fee >= 0),
    CONSTRAINT chk_txn_balance_nonnegative CHECK (balance_after IS NULL OR balance_after >= 0)
) ENGINE=InnoDB COMMENT='One row per parsed MoMo SMS transaction';

CREATE INDEX idx_txn_datetime ON transactions (transaction_datetime);
CREATE INDEX idx_txn_category ON transactions (category_id);
CREATE INDEX idx_txn_status ON transactions (status);

-- ---------------------------------------------------------------------
-- 5. transaction_participants (junction table -> resolves the
--    users <-> transactions many-to-many relationship)
--
--    A transaction can involve more than one user in different roles
--    (sender, receiver, and - for agent withdrawals - both the account
--    holder and the agent), and a single user participates in many
--    transactions over time. This table is the resolved M:N.
-- ---------------------------------------------------------------------
CREATE TABLE transaction_participants (
    participant_id   INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id   INT NOT NULL,
    user_id          INT NOT NULL,
    role             ENUM('SENDER','RECEIVER','AGENT','ACCOUNT_HOLDER') NOT NULL,
    CONSTRAINT fk_participant_txn
        FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_participant_user
        FOREIGN KEY (user_id) REFERENCES users (user_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT uq_txn_role UNIQUE (transaction_id, role)
) ENGINE=InnoDB COMMENT='Junction table resolving the many-to-many relationship between users and transactions';

CREATE INDEX idx_participant_user ON transaction_participants (user_id);
CREATE INDEX idx_participant_txn ON transaction_participants (transaction_id);

-- ---------------------------------------------------------------------
-- 6. system_logs
--    ETL processing audit trail (parse -> clean -> categorize -> load),
--    including the dead-letter path for unparseable SMS.
-- ---------------------------------------------------------------------
CREATE TABLE system_logs (
    log_id              INT AUTO_INCREMENT PRIMARY KEY,
    sms_id              INT NULL COMMENT 'SMS being processed when this log entry was written, if applicable',
    transaction_id      INT NULL COMMENT 'Resulting transaction, once one exists',
    stage               ENUM('PARSE','CLEAN','CATEGORIZE','LOAD') NOT NULL,
    log_level           ENUM('INFO','WARNING','ERROR') NOT NULL DEFAULT 'INFO',
    processing_status   ENUM('SUCCESS','FAILED','SKIPPED') NOT NULL,
    message             VARCHAR(500) NOT NULL,
    raw_snippet         TEXT NULL COMMENT 'Offending SMS body excerpt, populated for dead-letter entries',
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_sms
        FOREIGN KEY (sms_id) REFERENCES sms_messages (sms_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_log_txn
        FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='ETL pipeline audit trail, including dead-letter records for unparsed SMS';

CREATE INDEX idx_log_stage_status ON system_logs (stage, processing_status);
CREATE INDEX idx_log_created ON system_logs (created_at);

-- =====================================================================
-- SAMPLE DATA (DML)
-- Hand-picked to cover every message shape found in data/raw/momo.xml:
-- incoming money, payment to code holder, bank deposit, transfer to
-- mobile number, airtime, cash power, bundles/packs, third-party debit,
-- agent withdrawal, and one failed + one reversed transaction.
-- =====================================================================

-- --- users (account holder + counterparties + one agent) -------------
INSERT INTO users (user_id, full_name, phone_number, is_phone_masked, user_type) VALUES
(1, 'Account Holder',      '250788110381', FALSE, 'CUSTOMER'),
(2, 'Jane Smith',          '*********013', TRUE,  'CUSTOMER'),
(3, 'Samuel Carter',       '250791666666', FALSE, 'CUSTOMER'),
(4, 'Alex Doe',            '250790777777', FALSE, 'CUSTOMER'),
(5, 'Robert Brown',        '250788999999', FALSE, 'CUSTOMER'),
(6, 'Linda Green',         '*********704', TRUE,  'CUSTOMER'),
(7, 'Agent John',          '250788999999', FALSE, 'AGENT'),
(8, 'DIRECT PAYMENT LTD',  NULL,           FALSE, 'MERCHANT'),
(9, 'Mediatrice UWAYISENGA','250788658286', FALSE, 'CUSTOMER'),
(10, 'Agent Sophia',       '250790777777', FALSE, 'AGENT');

-- --- transaction_categories -------------------------------------------
INSERT INTO transaction_categories (category_id, category_code, category_name, description, default_direction) VALUES
(1, 'RECEIVE_MONEY',       'Incoming Money',              'Money received from another MoMo user',            'CREDIT'),
(2, 'PAYMENT_CODE_HOLDER', 'Payment to Code Holder',      'Payment to a merchant/till code (TxId payments)',  'DEBIT'),
(3, 'BANK_DEPOSIT',        'Bank Deposit',                'Cash deposit into the MoMo account from a bank',   'CREDIT'),
(4, 'TRANSFER_MOBILE',     'Transfer to Mobile Number',   'Peer-to-peer transfer to another mobile number',   'DEBIT'),
(5, 'AIRTIME_BILL',        'Airtime Bill Payment',        'Airtime top-up purchase',                          'DEBIT'),
(6, 'CASH_POWER_BILL',     'Cash Power Bill Payment',     'MTN Cash Power (electricity) token purchase',      'DEBIT'),
(7, 'BUNDLES_PACKS',       'Bundles and Packs Purchase',  'Data/voice bundle purchase',                       'DEBIT'),
(8, 'THIRD_PARTY_TXN',     'Third Party Transaction',     'Debit initiated by a registered third party',      'DEBIT'),
(9, 'AGENT_WITHDRAWAL',    'Withdrawal from Agent',       'Cash withdrawal via a MoMo agent',                 'DEBIT'),
(10,'TRANSACTION_REVERSAL','Transaction Reversal',        'Reversal of a previously completed transaction',   'CREDIT');

-- --- sms_messages (raw, verbatim) -------------------------------------
INSERT INTO sms_messages (sms_id, address, sms_protocol, sms_type, body, service_center, sms_timestamp, sms_date_sent, readable_date, raw_hash, is_parsed) VALUES
(1, 'M-Money', 0, 1, 'You have received 2000 RWF from Jane Smith (*********013) on your mobile money account at 2024-05-10 16:30:51. Message from sender: . Your new balance:2000 RWF. Financial Transaction Id: 76662021700.', '+250788110381', '2024-05-10 16:30:58', '2024-05-10 16:30:51', '10 May 2024 4:30:58 PM', SHA2('sms-1715351458724', 256), TRUE),
(2, 'M-Money', 0, 1, 'TxId: 73214484437. Your payment of 1,000 RWF to Jane Smith 12845 has been completed at 2024-05-10 16:31:39. Your new balance: 1,000 RWF. Fee was 0 RWF.', '+250788110381', '2024-05-10 16:31:46', '2024-05-10 16:31:39', '10 May 2024 4:31:46 PM', SHA2('sms-1715351506754', 256), TRUE),
(3, 'M-Money', 0, 1, '*113*R*A bank deposit of 40000 RWF has been added to your mobile money account at 2024-05-11 18:43:49. Your NEW BALANCE :40400 RWF. Cash Deposit::CASH::::0::250795963036.Thank you for using MTN MobileMoney.*EN#', '+250788110381', '2024-05-11 18:45:36', '2024-05-11 18:43:49', '11 May 2024 6:45:36 PM', SHA2('sms-1715445936412', 256), TRUE),
(4, 'M-Money', 0, 1, '*165*S*10000 RWF transferred to Samuel Carter (250791666666) from 36521838 at 2024-05-11 20:34:47 . Fee was: 100 RWF. New balance: 28300 RWF.', '+250788110381', '2024-05-11 20:34:55', '2024-05-11 20:34:47', '11 May 2024 8:34:55 PM', SHA2('sms-1715452495316', 256), TRUE),
(5, 'M-Money', 0, 1, '*162*TxId:13913173274*S*Your payment of 2000 RWF to Airtime with token has been completed at 2024-05-12 11:41:28. Fee was 0 RWF. Your new balance: 25280 RWF.', '+250788110381', '2024-05-12 11:41:35', '2024-05-12 11:41:28', '12 May 2024 11:41:35 AM', SHA2('sms-1715506895734', 256), TRUE),
(6, 'M-Money', 0, 1, '*162*TxId:14264876273*S*Your payment of 2000 RWF to MTN Cash Power with token 06476-53398 has been completed at 2024-05-12 12:10:00. Fee was 0 RWF. Your new balance: 23280 RWF.', '+250788110381', '2024-05-12 12:10:07', '2024-05-12 12:10:00', '12 May 2024 12:10:07 PM', SHA2('sms-1715510000000', 256), TRUE),
(7, 'M-Money', 0, 1, '*162*TxId:14324965479*S*Your payment of 2000 RWF to Bundles and Packs with token has been completed at 2024-05-12 13:00:00. Fee was 0 RWF. Your new balance: 21280 RWF.', '+250788110381', '2024-05-12 13:00:07', '2024-05-12 13:00:00', '12 May 2024 1:00:07 PM', SHA2('sms-1715512000000', 256), TRUE),
(8, 'M-Money', 0, 1, '*164*S*Y''ello,A transaction of 25000 RWF by DIRECT PAYMENT LTD on your MOMO account was successfully completed at 2024-05-14 21:01:00. Message from debit receiver: . Your new balance:4060 RWF. Fee was 0 RWF. Financial Transaction Id: 13947831685. External Transaction Id: 47842929.', '+250788110381', '2024-05-14 21:01:09', '2024-05-14 21:01:00', '14 May 2024 9:01:09 PM', SHA2('sms-1715713269609', 256), TRUE),
(9, 'M-Money', 0, 1, 'You Account Holder (*********036) have via agent: Agent John (250788999999), withdrawn 15000 RWF from your mobile money account at 2024-05-16 10:00:00. Your new balance: 6060 RWF. Fee was 100 RWF. Financial Transaction Id: 98765432101.', '+250788110381', '2024-05-16 10:00:08', '2024-05-16 10:00:00', '16 May 2024 10:00:08 AM', SHA2('sms-1715850000000', 256), TRUE),
(10, 'M-Money', 0, 1, '*143*TxId:16803066185*S*Your payment of 5000 RWF to Bundles and Packs with token has failed at 2024-05-17 09:00:00.', '+250788110381', '2024-05-17 09:00:07', '2024-05-17 09:00:00', '17 May 2024 9:00:07 AM', SHA2('sms-1715930000000', 256), TRUE),
(11, 'M-Money', 0, 1, 'A reversal has been initiated for your transaction to Mediatrice UWAYISENGA (250788658286), on 2024-05-18 08:00:00. Financial Transaction Id: 76662021700. Your new balance: 6060 RWF.', '+250788110381', '2024-05-18 08:00:07', '2024-05-18 08:00:00', '18 May 2024 8:00:07 AM', SHA2('sms-1716010000000', 256), TRUE);

-- --- transactions --------------------------------------------------------
INSERT INTO transactions (transaction_id, sms_id, category_id, financial_transaction_id, external_transaction_id, amount, fee, balance_after, currency, direction, status, transaction_datetime, reverses_transaction_id) VALUES
(1, 1,  1,  '76662021700', NULL,        2000.00,   0.00, 2000.00,  'RWF', 'CREDIT', 'COMPLETED', '2024-05-10 16:30:51', NULL),
(2, 2,  2,  '73214484437', NULL,        1000.00,   0.00, 1000.00,  'RWF', 'DEBIT',  'COMPLETED', '2024-05-10 16:31:39', NULL),
(3, 3,  3,  NULL,          NULL,       40000.00,   0.00, 40400.00, 'RWF', 'CREDIT', 'COMPLETED', '2024-05-11 18:43:49', NULL),
(4, 4,  4,  NULL,          NULL,       10000.00, 100.00, 28300.00, 'RWF', 'DEBIT',  'COMPLETED', '2024-05-11 20:34:47', NULL),
(5, 5,  5,  '13913173274', NULL,        2000.00,   0.00, 25280.00, 'RWF', 'DEBIT',  'COMPLETED', '2024-05-12 11:41:28', NULL),
(6, 6,  6,  '14264876273', NULL,        2000.00,   0.00, 23280.00, 'RWF', 'DEBIT',  'COMPLETED', '2024-05-12 12:10:00', NULL),
(7, 7,  7,  '14324965479', NULL,        2000.00,   0.00, 21280.00, 'RWF', 'DEBIT',  'COMPLETED', '2024-05-12 13:00:00', NULL),
(8, 8,  8,  '13947831685', '47842929',  25000.00,   0.00, 4060.00,  'RWF', 'DEBIT',  'COMPLETED', '2024-05-14 21:01:00', NULL),
(9, 9,  9,  '98765432101', NULL,        15000.00, 100.00, 6060.00,  'RWF', 'DEBIT',  'COMPLETED', '2024-05-16 10:00:00', NULL),
(10,10, 7,  '16803066185', NULL,        5000.00,   0.00, NULL,      'RWF', 'DEBIT',  'FAILED',    '2024-05-17 09:00:00', NULL),
(11,11, 10, NULL,          NULL,        2000.00,   0.00, 6060.00,  'RWF', 'CREDIT', 'REVERSED',  '2024-05-18 08:00:00', 1);

-- --- transaction_participants (resolves users <-> transactions M:N) ------
INSERT INTO transaction_participants (transaction_id, user_id, role) VALUES
(1, 2, 'SENDER'), (1, 1, 'RECEIVER'),
(2, 1, 'SENDER'), (2, 2, 'RECEIVER'),
(3, 1, 'RECEIVER'),
(4, 1, 'SENDER'), (4, 3, 'RECEIVER'),
(5, 1, 'SENDER'),
(6, 1, 'SENDER'),
(7, 1, 'SENDER'),
(8, 1, 'SENDER'), (8, 8, 'RECEIVER'),
(9, 1, 'ACCOUNT_HOLDER'), (9, 7, 'AGENT'),
(10, 1, 'SENDER'),
(11, 1, 'RECEIVER');

-- --- system_logs -----------------------------------------------------
INSERT INTO system_logs (sms_id, transaction_id, stage, log_level, processing_status, message, raw_snippet) VALUES
(1, 1,  'LOAD',        'INFO',    'SUCCESS', 'Loaded RECEIVE_MONEY transaction 76662021700', NULL),
(2, 2,  'CATEGORIZE',  'INFO',    'SUCCESS', 'Matched PAYMENT_CODE_HOLDER pattern "TxId: ... payment of"', NULL),
(4, 4,  'CLEAN',       'INFO',    'SUCCESS', 'Normalized phone 250791666666 and amount 10000', NULL),
(10,10, 'LOAD',        'WARNING', 'SUCCESS', 'Transaction loaded with status FAILED; balance_after left NULL', NULL),
(NULL, NULL, 'PARSE',  'ERROR',   'FAILED',  'Unrecognized SMS body pattern; routed to dead-letter', 'Kanda*182*16# wiyandikishe muri poromosiyo...'),
(11,11, 'CATEGORIZE',  'INFO',    'SUCCESS', 'Linked reversal to original financial_transaction_id 76662021700', NULL);

-- =====================================================================
-- SAMPLE CRUD / QUERY OPERATIONS (see docs/database_design.md for
-- annotated output and screenshots run against MySQL 8.0)
-- =====================================================================

-- CREATE: add a new user discovered in a later SMS batch
-- INSERT INTO users (full_name, phone_number, user_type) VALUES ('Grace Uwimana', '250788123456', 'CUSTOMER');

-- READ: full transaction detail with category and all participants
-- SELECT t.transaction_id, t.financial_transaction_id, t.amount, t.fee,
--        t.direction, t.status, t.transaction_datetime,
--        tc.category_name,
--        GROUP_CONCAT(CONCAT(tp.role, ':', u.full_name) SEPARATOR ' | ') AS participants
-- FROM transactions t
-- JOIN transaction_categories tc ON tc.category_id = t.category_id
-- JOIN transaction_participants tp ON tp.transaction_id = t.transaction_id
-- JOIN users u ON u.user_id = tp.user_id
-- GROUP BY t.transaction_id
-- ORDER BY t.transaction_datetime;

-- READ: spend by category (dashboard aggregate)
-- SELECT tc.category_name, COUNT(*) AS txn_count, SUM(t.amount) AS total_amount
-- FROM transactions t JOIN transaction_categories tc ON tc.category_id = t.category_id
-- WHERE t.status = 'COMPLETED'
-- GROUP BY tc.category_name
-- ORDER BY total_amount DESC;

-- UPDATE: correct a mis-parsed amount after manual review
-- UPDATE transactions SET amount = 1000.00 WHERE transaction_id = 2;

-- DELETE: remove a log entry after investigation is closed
-- DELETE FROM system_logs WHERE log_id = 5;
