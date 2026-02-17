-- Create payments table for initial payment collection
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS public.payments (
    payment_id BIGSERIAL PRIMARY KEY,
    app_id BIGINT NOT NULL REFERENCES admission_applications(app_id) ON DELETE CASCADE,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    bill_no TEXT NOT NULL UNIQUE,
    mode_of_payment TEXT NOT NULL CHECK (mode_of_payment IN ('Cash', 'Card', 'Cheque', 'Bank Transfer', 'UPI')),
    amount NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_payments_app_id ON public.payments(app_id);
CREATE INDEX IF NOT EXISTS idx_payments_student_id ON public.payments(student_id);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON public.payments(created_at DESC);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_payments_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_payments_timestamp
BEFORE UPDATE ON public.payments
FOR EACH ROW
EXECUTE FUNCTION update_payments_updated_at();
