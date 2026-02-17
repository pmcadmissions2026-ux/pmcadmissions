-- Add document upload columns to admissions table
-- Run this in Supabase SQL Editor

-- Add columns for document tracking
ALTER TABLE public.admissions 
ADD COLUMN IF NOT EXISTS documents_uploaded BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS documents JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS documents_submitted_at TIMESTAMP WITH TIME ZONE;

-- Create index on documents_uploaded for faster queries
CREATE INDEX IF NOT EXISTS idx_admissions_documents_uploaded ON public.admissions(documents_uploaded);

-- Update any existing records
UPDATE public.admissions SET documents_uploaded = FALSE WHERE documents_uploaded IS NULL;
UPDATE public.admissions SET documents = '{}'::jsonb WHERE documents IS NULL;
