-- ==============================================================================
-- LazyVA SaaS Relational Database Schema (PostgreSQL / Supabase)
-- ==============================================================================

-- 1. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    phone VARCHAR(50),
    country VARCHAR(10) DEFAULT 'PH',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Licenses Table
CREATE TABLE IF NOT EXISTS licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_key VARCHAR(64) NOT NULL UNIQUE,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    plan VARCHAR(32) NOT NULL DEFAULT 'pro', -- 'pro_monthly', 'pro_annual', 'lifetime'
    max_activations INT NOT NULL DEFAULT 2,
    status VARCHAR(32) NOT NULL DEFAULT 'active', -- 'active', 'suspended', 'revoked'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE, -- NULL for lifetime licenses
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 3. Device Activations Table (Binds licenses to machine HWIDs)
CREATE TABLE IF NOT EXISTS activations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_id UUID NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
    machine_id VARCHAR(64) NOT NULL,
    os_name VARCHAR(64),
    app_version VARCHAR(32),
    ip_address VARCHAR(45),
    activated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_validated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(license_id, machine_id)
);

-- 4. Payment Orders & Webhook Log
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_gateway VARCHAR(32) NOT NULL, -- 'paymongo', 'lemonsqueezy', 'gcash_manual', 'maya'
    gateway_reference VARCHAR(128) UNIQUE,
    customer_email VARCHAR(255) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'PHP',
    status VARCHAR(32) NOT NULL DEFAULT 'completed',
    license_key VARCHAR(64) REFERENCES licenses(license_key),
    raw_payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Indexes for Fast License Lookup
CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses(license_key);
CREATE INDEX IF NOT EXISTS idx_activations_license_machine ON activations(license_id, machine_id);
CREATE INDEX IF NOT EXISTS idx_orders_gateway_ref ON orders(gateway_reference);
