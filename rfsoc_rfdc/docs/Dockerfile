# ── Stage 1: build the static documentation ──────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install MkDocs and plugins
COPY rfsoc_rfdc/docs/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python source so mkdocstrings can parse the docstrings.
# The __init__ files in sub-packages use a .y extension; rename them.
COPY rfsoc_rfdc/ ./rfsoc_rfdc/
RUN find ./rfsoc_rfdc -name "*.y" | while read f; do cp "$f" "${f%.y}.py"; done

# Copy the MkDocs project (mkdocs.yml + pages/).
# docs_dir is "pages" and paths are relative to mkdocs.yml, so
# ".." resolves to /app/ which contains rfsoc_rfdc/ — correct for Docker.
COPY rfsoc_rfdc/docs/ ./docs/

WORKDIR /app/docs
RUN mkdocs build

# ── Stage 2: serve the built site with nginx ──────────────────────────────────
FROM nginx:alpine AS server

COPY --from=builder /app/docs/site /usr/share/nginx/html

# Optional: custom nginx config for clean URLs
RUN printf 'server {\n\
    listen 80;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location / {\n\
        try_files $uri $uri/ $uri.html =404;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
