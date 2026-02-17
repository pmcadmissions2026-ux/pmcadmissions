# Vercel serverless entrypoint for Flask app
from app import app

def handler(environ, start_response):
    """Simple WSGI handler that forwards the request to the Flask WSGI app.

    Vercel's Python runtime will call this function with a WSGI environ and
    start_response; forwarding directly avoids depending on the external
    `vercel-wsgi` package which is not available in Vercel's package registry.
    """
    return app(environ, start_response)
