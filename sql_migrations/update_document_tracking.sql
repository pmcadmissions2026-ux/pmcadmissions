-- Update admission_applications table to track step 3 completion
-- Add column to mark step 3 (documents) as completed
ALTER TABLE public.admission_applications
ADD COLUMN IF NOT EXISTS step3_completed BOOLEAN DEFAULT FALSE;

-- Add column to store count of uploaded documents
ALTER TABLE public.admission_applications
ADD COLUMN IF NOT EXISTS documents_count INTEGER DEFAULT 0;

-- Add column to store timestamp when documents were submitted
ALTER TABLE public.admission_applications
ADD COLUMN IF NOT EXISTS documents_submitted_at TIMESTAMP WITH TIME ZONE;

-- Update admissions table to also track documents
ALTER TABLE public.admissions
ADD COLUMN IF NOT EXISTS step3_completed BOOLEAN DEFAULT FALSE;

-- Add column to store count of uploaded documents
ALTER TABLE public.admissions
ADD COLUMN IF NOT EXISTS documents_count INTEGER DEFAULT 0;

-- Add column to store timestamp when documents were submitted  
ALTER TABLE public.admissions
ADD COLUMN IF NOT EXISTS documents_submitted_at TIMESTAMP WITH TIME ZONE;

-- Update documents table to add index for faster queries
ALTER TABLE public.documents
ADD CONSTRAINT documents_app_id_fkey FOREIGN KEY (app_id) 
REFERENCES admission_applications(app_id) ON DELETE CASCADE;

-- Create index for faster document lookups by app_id
CREATE INDEX IF NOT EXISTS idx_documents_app_id ON public.documents(app_id);

-- Create index for faster document lookups by student_id (via admission_applications)
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON public.documents(created_at DESC);

-- Optional: Create a view to easily get document info with student details
CREATE OR REPLACE VIEW public.vw_student_documents AS
SELECT 
    s.id as student_id,
    s.full_name,
    s.unique_id,
    aa.app_id,
    COUNT(d.doc_id) as total_documents,
    STRING_AGG(DISTINCT d.document_type, ', ') as document_types,
    MAX(d.created_at) as last_document_upload,
    aa.step3_completed as documents_submitted
FROM students s
LEFT JOIN admission_applications aa ON s.id = aa.student_id
LEFT JOIN documents d ON aa.app_id = d.app_id
GROUP BY s.id, s.full_name, s.unique_id, aa.app_id, aa.step3_completed;

-- Create trigger to automatically update documents_count when a document is inserted
CREATE OR REPLACE FUNCTION update_documents_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE admission_applications 
    SET documents_count = (SELECT COUNT(*) FROM documents WHERE app_id = NEW.app_id),
        step3_completed = true,
        documents_submitted_at = NOW()
    WHERE app_id = NEW.app_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_documents_count ON documents;
CREATE TRIGGER trg_update_documents_count
AFTER INSERT ON documents
FOR EACH ROW
EXECUTE FUNCTION update_documents_count();

-- Update admissions table with document count from linked admission_applications
CREATE OR REPLACE FUNCTION sync_admissions_documents()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE admissions 
    SET documents_count = NEW.documents_count,
        step3_completed = NEW.step3_completed,
        documents_submitted_at = NEW.documents_submitted_at
    WHERE student_id = NEW.student_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sync_admissions_documents ON admission_applications;
CREATE TRIGGER trg_sync_admissions_documents
AFTER UPDATE ON admission_applications
FOR EACH ROW
EXECUTE FUNCTION sync_admissions_documents();
