#!/usr/bin/env python3
"""HTTP server for Palmer site clone — handles CORS, SPA routing, CMS range requests, asset redirects."""
import os, sys, re, mimetypes
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

mimetypes.add_type('application/javascript', '.mjs')
mimetypes.add_type('font/woff2', '.woff2')
mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('video/webm', '.webm')
mimetypes.add_type('application/octet-stream', '.framercms')
mimetypes.add_type('application/javascript', '.js')

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parsed.query

        # 1. Redirect nested asset/JS requests to root
        #    e.g. /work/images/x.png -> /images/x.png  (Framer relative path fix for sub-routes)
        m = re.match(r'^/[^/]+/(images|fonts|videos|assets|js|css)/(.+)$', path)
        if m:
            new_path = f'/{m.group(1)}/{m.group(2)}'
            if qs:
                new_path += '?' + qs
            self.send_response(301)
            self.send_header('Location', new_path)
            self.end_headers()
            return

        # 2. CMS binary files: serve with ?range= support
        if path.endswith('.framercms'):
            filepath = self.translate_path(path)
            if os.path.exists(filepath):
                self._serve_framercms(filepath, qs)
                return

        # 3. SPA routing: try .html extension, fallback to index.html
        file_path = self.translate_path(path)
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            if os.path.exists(file_path + '.html'):
                self.path = path + '.html'
            elif not any(path.endswith(x) for x in [
                '.mjs','.js','.css','.png','.jpg','.jpeg','.gif',
                '.webp','.svg','.woff2','.woff','.mp4','.webm',
                '.json','.avif','.ico','.ttf','.framercms'
            ]):
                self.path = '/index.html'

        return super().do_GET()

    def _serve_framercms(self, filepath, qs):
        """Serve .framercms binary with Framer ?range= query support.

        Framer requests byte ranges like: ?range=0-182,183-364,...
        We extract those ranges from the file and concatenate them.
        """
        with open(filepath, 'rb') as f:
            data = f.read()

        params = parse_qs(qs)
        range_param = params.get('range', [None])[0]

        if range_param:
            # Parse "0-182,183-364,..." -> list of (start, end_inclusive)
            parts = []
            for chunk in range_param.split(','):
                chunk = chunk.strip()
                if '-' in chunk:
                    s, e = chunk.split('-', 1)
                    parts.append((int(s), int(e)))

            result = bytearray()
            for start, end_inc in parts:
                result.extend(data[start:end_inc + 1])

            body = bytes(result)
        else:
            body = data

        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        return self.do_GET()

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # Suppress logs

def run(port=8000):
    site = Path(__file__).parent
    os.chdir(site)
    httpd = HTTPServer(('0.0.0.0', port), Handler)
    print(f"Palmer site: http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == '__main__':
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
