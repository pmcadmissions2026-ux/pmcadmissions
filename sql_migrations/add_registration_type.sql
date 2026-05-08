-- SQL Migration to add registration_type to students table
ALTER TABLE public.students 
ADD COLUMN IF NOT EXISTS registration_type VARCHAR(20) DEFAULT 'enquiry';

-- Update existing students to 'enquiry' if they were not direct entries
-- (Assuming existing students were mostly enquiries)
UPDATE public.students SET registration_type = 'enquiry' WHERE registration_type IS NULL;
