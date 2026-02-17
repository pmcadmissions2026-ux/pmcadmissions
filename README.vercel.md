# Deploying Flask on Vercel and Render

## Vercel Deployment

### Docker (Custom Runtime)
- If your Vercel plan supports Docker, keep your Dockerfile and vercel.json.
- Set all secrets (SUPABASE_URL, SUPABASE_KEY, etc.) as Vercel Environment Variables.
- Flask static files: place in `/static`, templates in `/templates`.
- Use `gunicorn` as WSGI server (already in Dockerfile).

### Serverless (Recommended for Free/Pro plans)
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

## Render Deployment (Recommended for Flask)
- Sign up at https://render.com and create a new Web Service.
- Connect your GitHub repo or deploy manually.
- Set the build and start commands:
  - **Build Command:** (leave blank for pure Python)
  - **Start Command:**
    ```
    gunicorn app:app
    ```
- Set all environment variables from your `.env` file in the Render dashboard (Settings > Environment).
- **Static Files:**
  - Place static assets in `/static` and templates in `/templates` (already set up).
- **Session Storage:**
  - Use signed cookies or a cloud session backend (avoid filesystem sessions).
- **File Uploads:**
  - Use Supabase Storage or S3, not local disk.
- **Port:**
  - Render automatically sets the `PORT` environment variable. In your Flask app, use `os.environ.get('PORT', 5000)` for the port.

### Example: Flask Port Handling
```python
import os
port = int(os.environ.get('PORT', 5000))
app.run(host='0.0.0.0', port=port)
```

## Environment Variables
Set these in Render (Settings > Environment):
- SUPABASE_URL
- SUPABASE_KEY
- SUPABASE_SERVICE_KEY
- SECRET_KEY
- FLASK_ENV=production
- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, etc.
- Any other secrets from your `.env`

## Common Issues
- **Session Storage:** Use Redis or signed cookies, not filesystem.
- **File Uploads:** Use S3/Supabase Storage, not local disk.
- **Static/Template Paths:** Use relative paths.
- **Startup:** Docker: `CMD ["gunicorn", ...]`; Serverless: use handler above.

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
- https://render.com/docs/deploy-flask
- https://render.com/docs/environment-variables
- https://render.com/docs/web-services
