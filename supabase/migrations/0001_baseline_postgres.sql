BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 916651f2e591

CREATE TABLE users (
    id SERIAL NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    email VARCHAR(100) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    is_active BOOLEAN, 
    is_verified BOOLEAN, 
    is_deleted BOOLEAN, 
    created_at TIMESTAMP WITH TIME ZONE, 
    updated_at TIMESTAMP WITH TIME ZONE, 
    last_login TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE INDEX ix_users_id ON users (id);

CREATE TABLE accounts (
    id SERIAL NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    account_type VARCHAR(11) NOT NULL, 
    currency VARCHAR(3) NOT NULL, 
    balance NUMERIC(12, 2) NOT NULL, 
    initial_balance NUMERIC(12, 2) NOT NULL, 
    credit_limit NUMERIC(12, 2), 
    closing_day INTEGER, 
    due_day INTEGER, 
    color VARCHAR(20) NOT NULL, 
    icon VARCHAR(50), 
    is_active BOOLEAN NOT NULL, 
    user_id INTEGER NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    deleted_at TIMESTAMP WITHOUT TIME ZONE, 
    is_deleted BOOLEAN NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_accounts_id ON accounts (id);

CREATE INDEX ix_accounts_user_id ON accounts (user_id);

CREATE TABLE assets (
    id SERIAL NOT NULL, 
    ticker VARCHAR(20) NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    asset_type VARCHAR(12) NOT NULL, 
    sector VARCHAR(50), 
    user_id INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_asset_ticker_user UNIQUE (ticker, user_id)
);

CREATE INDEX ix_assets_id ON assets (id);

CREATE INDEX ix_assets_ticker ON assets (ticker);

CREATE TABLE categories (
    id SERIAL NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    transaction_type VARCHAR(8), 
    icon VARCHAR(40), 
    color VARCHAR(20), 
    is_system BOOLEAN, 
    user_id INTEGER, 
    parent_id INTEGER, 
    PRIMARY KEY (id), 
    FOREIGN KEY(parent_id) REFERENCES categories (id), 
    FOREIGN KEY(user_id) REFERENCES users (id), 
    CONSTRAINT uq_category_name_user UNIQUE (name, user_id)
);

CREATE INDEX ix_categories_id ON categories (id);

CREATE TABLE password_reset_tokens (
    id SERIAL NOT NULL, 
    jti VARCHAR(36) NOT NULL, 
    user_id INTEGER NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    used BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_password_reset_tokens_id ON password_reset_tokens (id);

CREATE UNIQUE INDEX ix_password_reset_tokens_jti ON password_reset_tokens (jti);

CREATE INDEX ix_password_reset_tokens_user_id ON password_reset_tokens (user_id);

CREATE TABLE budgets (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    category_id INTEGER NOT NULL, 
    amount NUMERIC(12, 2) NOT NULL, 
    month INTEGER NOT NULL, 
    year INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_budget_amount_positive CHECK (amount > 0), 
    CONSTRAINT ck_budget_month CHECK (month >= 1 AND month <= 12), 
    FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT unique_budget_per_month UNIQUE (user_id, category_id, month, year)
);

CREATE INDEX ix_budgets_id ON budgets (id);

CREATE TABLE goals (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    account_id INTEGER, 
    name VARCHAR(200) NOT NULL, 
    description TEXT, 
    category VARCHAR(14) NOT NULL, 
    target_amount NUMERIC(12, 2) NOT NULL, 
    current_amount NUMERIC(12, 2), 
    monthly_contribution NUMERIC(12, 2), 
    deadline TIMESTAMP WITH TIME ZONE, 
    status VARCHAR(9) NOT NULL, 
    is_deleted BOOLEAN, 
    created_at TIMESTAMP WITH TIME ZONE, 
    updated_at TIMESTAMP WITH TIME ZONE, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(account_id) REFERENCES accounts (id) ON DELETE SET NULL, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_goals_id ON goals (id);

CREATE INDEX ix_goals_status ON goals (status);

CREATE INDEX ix_goals_user_id ON goals (user_id);

CREATE TABLE investment_operations (
    id SERIAL NOT NULL, 
    asset_id INTEGER NOT NULL, 
    account_id INTEGER, 
    operation_type VARCHAR(8) NOT NULL, 
    date DATE NOT NULL, 
    quantity NUMERIC(14, 4) NOT NULL, 
    price_per_unit NUMERIC(14, 4) NOT NULL, 
    fees NUMERIC(14, 4), 
    total_amount NUMERIC(14, 4) NOT NULL, 
    notes VARCHAR(255), 
    created_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(account_id) REFERENCES accounts (id) ON DELETE SET NULL, 
    FOREIGN KEY(asset_id) REFERENCES assets (id) ON DELETE CASCADE
);

CREATE INDEX ix_investment_operations_date ON investment_operations (date);

CREATE INDEX ix_investment_operations_id ON investment_operations (id);

CREATE INDEX ix_investment_ops_asset_date ON investment_operations (asset_id, date);

CREATE TABLE scheduled_bills (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    account_id INTEGER, 
    category_id INTEGER, 
    name VARCHAR(200) NOT NULL, 
    description TEXT, 
    bill_type VARCHAR(10) NOT NULL, 
    amount NUMERIC(12, 2) NOT NULL, 
    paid_amount NUMERIC(12, 2), 
    due_date DATE NOT NULL, 
    paid_date DATE, 
    status VARCHAR(9) NOT NULL, 
    is_deleted BOOLEAN, 
    reminder_days_before SMALLINT, 
    reminded_at TIMESTAMP WITH TIME ZONE, 
    recurrence VARCHAR(9) NOT NULL, 
    parent_bill_id INTEGER, 
    notes TEXT, 
    created_at TIMESTAMP WITH TIME ZONE, 
    updated_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_bill_amount_positive CHECK (amount > 0), 
    FOREIGN KEY(account_id) REFERENCES accounts (id) ON DELETE SET NULL, 
    FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE SET NULL, 
    FOREIGN KEY(parent_bill_id) REFERENCES scheduled_bills (id) ON DELETE SET NULL, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_bills_user_due_status ON scheduled_bills (user_id, due_date, status);

CREATE INDEX ix_scheduled_bills_bill_type ON scheduled_bills (bill_type);

CREATE INDEX ix_scheduled_bills_due_date ON scheduled_bills (due_date);

CREATE INDEX ix_scheduled_bills_id ON scheduled_bills (id);

CREATE INDEX ix_scheduled_bills_status ON scheduled_bills (status);

CREATE INDEX ix_scheduled_bills_user_id ON scheduled_bills (user_id);

CREATE TABLE transactions (
    id SERIAL NOT NULL, 
    description VARCHAR(255) NOT NULL, 
    base_amount NUMERIC(12, 2) NOT NULL, 
    transaction_type VARCHAR(8) NOT NULL, 
    purchase_date DATE NOT NULL, 
    due_date DATE NOT NULL, 
    paid_date DATE, 
    status VARCHAR(9), 
    is_recurring BOOLEAN, 
    installment_number INTEGER, 
    total_installments INTEGER, 
    user_id INTEGER NOT NULL, 
    account_id INTEGER NOT NULL, 
    category_id INTEGER NOT NULL, 
    destination_account_id INTEGER, 
    transfer_group_id VARCHAR(36), 
    client_transfer_id VARCHAR(36), 
    scheduled_bill_id INTEGER, 
    notes VARCHAR(500), 
    import_hash VARCHAR(64), 
    categorization_source VARCHAR(20), 
    created_at TIMESTAMP WITH TIME ZONE, 
    updated_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(account_id) REFERENCES accounts (id) ON DELETE RESTRICT, 
    FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE RESTRICT, 
    FOREIGN KEY(destination_account_id) REFERENCES accounts (id) ON DELETE RESTRICT, 
    FOREIGN KEY(scheduled_bill_id) REFERENCES scheduled_bills (id) ON DELETE SET NULL, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_transactions_client_transfer_id ON transactions (client_transfer_id);

CREATE INDEX ix_transactions_due_date ON transactions (due_date);

CREATE INDEX ix_transactions_id ON transactions (id);

CREATE UNIQUE INDEX ix_transactions_import_hash ON transactions (import_hash);

CREATE INDEX ix_transactions_paid_date ON transactions (paid_date);

CREATE INDEX ix_transactions_purchase_date ON transactions (purchase_date);

CREATE INDEX ix_transactions_status ON transactions (status);

CREATE INDEX ix_transactions_transfer_group_id ON transactions (transfer_group_id);

CREATE INDEX ix_transactions_user_due ON transactions (user_id, due_date);

CREATE INDEX ix_transactions_user_id ON transactions (user_id);

CREATE INDEX ix_transactions_user_paid ON transactions (user_id, paid_date);

INSERT INTO alembic_version (version_num) VALUES ('916651f2e591') RETURNING alembic_version.version_num;

COMMIT;

