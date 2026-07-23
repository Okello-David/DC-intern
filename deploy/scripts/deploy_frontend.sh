#!/usr/bin/env bash
#
# Build the React frontend and publish it to the Nginx web root on the EC2
# instance.
#
# Run it from a Session Manager shell, as ec2-user (NOT as root — npm should not
# run as root, and the build output stays owned by ec2-user):
#
#   cd /opt/dc-intern
#   git pull
#   ./deploy/scripts/deploy_frontend.sh
#
# Prerequisites on the instance:
#   * Node.js 20 or newer:  sudo dnf install -y nodejs npm
#   * The backend already deployed, so /etc/nginx/conf.d/dc-intern.conf exists
#     (deploy/scripts/deploy_backend.sh renders it).
#
# It handles no secrets. The only build-time variable it sets is the API base
# URL, which is public by definition — it ends up in the JavaScript bundle that
# every visitor downloads. Nothing else from the environment is passed to the
# build, deliberately: any VITE_* value would be compiled into that same public
# bundle.

set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/dc-intern}"
FRONTEND_DIR="${APP_ROOT}/frontend"
WEB_ROOT="${WEB_ROOT:-/var/www/dc-intern}"

# Same-origin: Nginx serves this app and proxies /api/ to Gunicorn, so the
# browser calls its own address. No public IP or hostname is compiled into the
# bundle, which means the same build keeps working when the instance's IP
# changes or a domain name and TLS are added later.
API_BASE_URL="${VITE_API_BASE_URL:-/api}"

step()  { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
info()  { printf '    %s\n' "$1"; }
fail()  { printf '\n\033[31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }

# --------------------------------------------------------------------------
step 'Preflight checks'
# --------------------------------------------------------------------------

[[ ${EUID} -ne 0 ]] || fail "Do not run this as root or with sudo. Run it as ec2-user; it will call sudo where needed."
[[ -d ${FRONTEND_DIR} ]] || fail "${FRONTEND_DIR} not found. Clone the repository to ${APP_ROOT} first."
[[ -f ${FRONTEND_DIR}/package.json ]] || fail "${FRONTEND_DIR}/package.json not found."

command -v npm > /dev/null || fail "npm not found. Install Node.js: sudo dnf install -y nodejs npm"

node_major=$(node --version | sed 's/^v\([0-9]*\).*/\1/')
(( node_major >= 20 )) || fail "Node.js ${node_major} is too old; Vite 8 needs Node 20 or newer.
       On Amazon Linux 2023: sudo dnf install -y nodejs20 (or use nvm)."

info "$(node --version), npm $(npm --version)"
info "Building with VITE_API_BASE_URL=${API_BASE_URL}"

# --------------------------------------------------------------------------
step 'Install dependencies'
# --------------------------------------------------------------------------

# `npm ci` installs exactly what package-lock.json pins and starts from a clean
# node_modules, so a deployment cannot pick up a different dependency version
# from the one that was tested. It requires the lock file to be in sync with
# package.json — if it refuses, that mismatch is a real problem to fix, not to
# work around with `npm install`.
cd "${FRONTEND_DIR}"
if [[ -f package-lock.json ]]; then
    npm ci --no-audit --no-fund
else
    info 'No package-lock.json found; falling back to npm install.'
    npm install --no-audit --no-fund
fi

# --------------------------------------------------------------------------
step 'Build the production bundle'
# --------------------------------------------------------------------------

# Remove any previous build so stale files cannot be published.
rm -rf "${FRONTEND_DIR}/dist"

VITE_API_BASE_URL="${API_BASE_URL}" npm run build

[[ -f ${FRONTEND_DIR}/dist/index.html ]] || fail "Build finished but ${FRONTEND_DIR}/dist/index.html is missing."
info "Built $(find "${FRONTEND_DIR}/dist" -type f | wc -l) files into dist/"

# Fail loudly if a developer machine's localhost URL made it into the bundle —
# it would leave the deployed app calling a backend that does not exist for the
# visitor. Only meaningful for a same-origin build.
if [[ ${API_BASE_URL} == /* ]] && grep -rq '127\.0\.0\.1:8000' "${FRONTEND_DIR}/dist"; then
    fail "The built bundle contains 127.0.0.1:8000. A stale frontend/.env is the usual cause; remove it and re-run."
fi

# --------------------------------------------------------------------------
step 'Publish to the web root'
# --------------------------------------------------------------------------

sudo install -d -o root -g root -m 755 "${WEB_ROOT}"

# --delete removes files from a previous release that no longer exist, so old
# hashed bundles do not accumulate. The trailing slash on the source copies the
# CONTENTS of dist/, not the directory itself.
if command -v rsync > /dev/null; then
    sudo rsync -a --delete "${FRONTEND_DIR}/dist/" "${WEB_ROOT}/"
else
    sudo find "${WEB_ROOT}" -mindepth 1 -delete
    sudo cp -r "${FRONTEND_DIR}/dist/." "${WEB_ROOT}/"
fi

# Owned by root, world-readable, not writable by the web server. Nginx only ever
# needs to READ these files; if the nginx user could write here, a compromise of
# the web server would become the ability to replace the application's
# JavaScript for every visitor.
sudo chown -R root:root "${WEB_ROOT}"
sudo find "${WEB_ROOT}" -type d -exec chmod 755 {} +
sudo find "${WEB_ROOT}" -type f -exec chmod 644 {} +

# SELinux is enforcing on Amazon Linux 2023; without the httpd_sys_content_t
# label Nginx gets "Permission denied" on files that look perfectly readable.
if command -v restorecon > /dev/null; then
    sudo restorecon -R "${WEB_ROOT}" || info 'restorecon reported an issue (ignore if SELinux is disabled).'
fi

info "Published to ${WEB_ROOT}"

# --------------------------------------------------------------------------
step 'Validate and reload Nginx'
# --------------------------------------------------------------------------

sudo nginx -t
# reload, not restart: reload swaps the configuration without dropping the
# connections currently being served.
sudo systemctl reload nginx
info 'nginx reloaded'

# --------------------------------------------------------------------------
step 'Smoke test'
# --------------------------------------------------------------------------

info 'Frontend  (127.0.0.1:80/)'
curl --silent --show-error --fail --max-time 10 -o /dev/null -w '    HTTP %{http_code}, %{size_download} bytes\n' http://127.0.0.1/

info 'SPA fallback  (127.0.0.1:80/some/deep/link)'
curl --silent --show-error --fail --max-time 10 -o /dev/null -w '    HTTP %{http_code}\n' http://127.0.0.1/some/deep/link

info 'API through the same origin  (127.0.0.1:80/api/health/)'
curl --silent --show-error --fail --max-time 10 http://127.0.0.1/api/health/ && printf '\n'

printf '\n\033[32mFrontend deployment complete.\033[0m\n'
printf 'Open http://<public-dns-or-ip>/ in a browser and generate a skill gap analysis.\n'
