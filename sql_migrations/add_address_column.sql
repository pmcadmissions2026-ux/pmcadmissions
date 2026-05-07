-- Add address columns to relevant tables
ALTER TABLE public.basic_enquiry ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE public.enquiries ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE public.students ADD COLUMN IF NOT EXISTS address TEXT;
