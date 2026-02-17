# Vercel serverless entrypoint for Flask app
from vercel_wsgi import handle
from app import app

def handler(environ, start_response):
    return handle(app, environ, start_response)
