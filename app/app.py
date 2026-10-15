import os
import socket

from flask import Flask, Response

app = Flask(__name__)

APP_VERSION = os.environ.get("APP_VERSION", "dev")
GIT_SHA = os.environ.get("GIT_SHA", "unknown")      # baked in at build time
BUILD_NUMBER = os.environ.get("BUILD_NUMBER", "0")  # baked in at build time


@app.route("/")
def index():
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Homework 2 - CI/CD Pipeline1</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 3rem auto; max-width: 36rem;
           line-height: 1.6; color: #14202b; }}
    .badge {{ background: #0b7285; color: #fff; padding: .15rem .6rem;
              border-radius: 999px; font-size: .85rem; }}
    code {{ background: #eef2f5; padding: .1rem .35rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>CI/CD with Jenkins, ECR &amp; Docker Swarm</h1>
  <p><span class="badge">{APP_VERSION}</span></p>
  <p>Jenkins build: <code>#{BUILD_NUMBER}</code></p>
  <p>Git commit: <code>{GIT_SHA}</code></p>
  <p>Served by container: <code>{socket.gethostname()}</code></p>
</body>
</html>"""
    resp = Response(html, mimetype="text/html")
    resp.headers["X-Git-Sha"] = GIT_SHA
    return resp


@app.route("/health")
def health():
    return {"status": "ok", "version": APP_VERSION, "sha": GIT_SHA}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
