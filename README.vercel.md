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
# Deploying Flask on Vercel and Render

## Background
Vercel deprecated the `@vercel/docker` builder (it is not published on npm). If your `vercel.json` references `@vercel/docker` the Vercel build will fail with "The package `@vercel/docker` is not published". Use the serverless approach on Vercel instead, or deploy a Docker image to a provider that supports containers (Render, Fly, Railway).

## Vercel (Serverless - Recommended)

- This repository includes `/api/index.py` which wraps the Flask `app` with `vercel-wsgi` for Vercel serverless functions.
- Ensure `vercel-wsgi` is present in `requirements.txt` (this repo is pre-configured).
- `vercel.json` is set to map `api/**/*.py` to the Python runtime. No Docker builder is used.

Deployment steps on Vercel:
- Connect your GitHub repo in the Vercel dashboard.
- Ensure Environment variables are set in Project Settings → Environment Variables (e.g. `SUPABASE_URL`, `SUPABASE_KEY`, `SECRET_KEY`, SMTP vars).
- Deploy — Vercel will build and install `requirements.txt` and expose the `/api` endpoints as serverless functions.

Local test (serverless):
```bash
pip install -r requirements.txt
vercel dev
```

Serverless considerations:
- Do not use local filesystem for sessions or uploads (ephemeral). Use Supabase Storage, S3, or a remote session store.
- Keep static assets in `/static`; for large files use a CDN.

## Docker / Container-hosting (Alternative)

If you specifically need to run Docker images, deploy to a service that supports containers (Render, Fly, Railway, AWS ECS, GCP Cloud Run). This repo includes a `Dockerfile` for local builds and those platforms.

Example Docker local run:
```bash
docker build -t pmc-admissions .
docker run --rm -p 5000:5000 --env-file .env pmc-admissions
```

## Render quick notes

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
- Set env vars in Render Dashboard.

## References
- https://vercel.com/docs/concepts/functions/serverless-functions/runtimes/python
- https://github.com/juancarlospaco/vercel-wsgi
- https://render.com/docs/deploy-flask
