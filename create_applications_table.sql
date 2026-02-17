-- Create applications table for document uploads
-- Run this in Supabase SQL Editor

-- Drop table if exists (careful with this in production!)
DROP TABLE IF EXISTS public.applications CASCADE;

-- Create applications table
CREATE TABLE public.applications (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES public.students(id) ON DELETE CASCADE,
    documents JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(50) DEFAULT 'draft',
    submitted_at TIMESTAMP WITH TIME ZONE,
    submitted_by BIGINT,  -- No foreign key constraint to avoid errors
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on student_id for faster lookups
CREATE INDEX idx_applications_student_id ON public.applications(student_id);

-- Create index on status
CREATE INDEX idx_applications_status ON public.applications(status);

-- Add unique constraint on student_id (one application per student)
ALTER TABLE public.applications ADD CONSTRAINT unique_student_application UNIQUE (student_id);

-- Grant permissions (adjust as needed)
ALTER TABLE public.applications ENABLE ROW LEVEL SECURITY;
