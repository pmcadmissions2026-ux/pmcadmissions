# Deploying Flask on Vercel

## Docker (Custom Runtime)
- If your Vercel plan supports Docker, keep your Dockerfile and vercel.json.
- Set all secrets (SUPABASE_URL, SUPABASE_KEY, etc.) as Vercel Environment Variables.
- Flask static files: place in `/static`, templates in `/templates`.
- Use `gunicorn` as WSGI server (already in Dockerfile).

## Serverless (Recommended for Free/Pro plans)
- Remove vercel.json and Dockerfile if not using Docker.
- Add `/api/index.py`:
  ```python
  from vercel_wsgi import handle
  from app import app
  def handler(environ, start_response):
      return handle(app, environ, start_response)
  ```
- Add `vercel-wsgi` to `requirements.txt`.
- All Flask routes must be compatible with serverless (no file uploads to disk, no local session storage).
- Set all secrets in Vercel dashboard.

## Common Issues
- **Session Storage:** Use Redis or signed cookies, not filesystem.
- **File Uploads:** Use S3/Supabase Storage, not local disk.
- **Static/Template Paths:** Use relative paths.
- **Startup:** Docker: `CMD ["gunicorn", ...]`; Serverless: use handler above.

## Environment Variables
Set these in Vercel dashboard:
- SUPABASE_URL
- SUPABASE_KEY
- SECRET_KEY
- FLASK_ENV=production
- Any SMTP/other secrets

## Local Test (Serverless)
```bash
pip install vercel-wsgi
vercel dev
```

## Local Test (Docker)
```bash
docker build -t pmc-admissions .
docker run --rm -p 5000:5000 --env-file .env pmc-admissions
```

## References
- https://github.com/juancarlospaco/vercel-wsgi
- https://vercel.com/docs/concepts/functions/serverless-functions/runtimes/python
- https://vercel.com/docs/deployments/overview
