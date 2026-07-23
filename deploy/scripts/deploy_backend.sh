#!/usr/bin/env bash
#
# Deploy the Django backend on the EC2 instance.
#
# Run it from a Session Manager shell, as ec2-user (NOT as root — the script
# uses sudo only for the few steps that need it, so application files stay owned
# by ec2-user):
#
#   cd /opt/dc-intern
#   git pull
#   SERVER_NAME=ec2-1-2-3-4.compute-1.amazonaws.com ./deploy/scripts/deploy_backend.sh
#
# The React frontend is deployed separately by deploy/scripts/deploy_frontend.sh,
# which this script prompts for at the end. Set DEPLOY_FRONTEND=1 to run both in
# one go. They are separate because they fail for different reasons and are
# redeployed at different times: a backend change does not need a 200MB npm
# install, and a copy-change in the UI does not need a database migration.
#
# Assumptions:
#   * The repository is already at /opt/dc-intern and owned by ec2-user.
#   * /etc/dc-intern/backend.env already exists, created by hand or from
#     Parameter Store. This script NEVER creates, fetches, edits, or prints it.
#
# It handles no secrets itself: it sources the environment file into a subshell
# so Django can read it, and never echoes any value from it.

set -euo pipefail

# Never enable `set -x` in this script — it would print the contents of the
# environment file, including the database password and any AI API key.

# APP_ROOT and ENV_FILE are overridable so the preflight checks can be
# exercised against a scratch copy before touching a real instance. The systemd
# unit and Nginx template hard-code /opt/dc-intern, so a real deployment must
# use the defaults.
APP_ROOT="${APP_ROOT:-/opt/dc-intern}"
BACKEND_DIR="${APP_ROOT}/backend"
VENV_DIR="${BACKEND_DIR}/venv"
# Django 6.0 requires Python >= 3.12. On Amazon Linux 2023 the bare `python3` is
# 3.9, so defaulting to it would build the virtualenv on an interpreter that
# cannot install the pinned Django and fail deep inside pip. Name the version
# explicitly, and verify it below rather than trusting the name.
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
MIN_PYTHON='3.12'
ENV_FILE="${ENV_FILE:-/etc/dc-intern/backend.env}"
SERVICE_NAME=dc-intern-backend
SERVICE_SRC="${APP_ROOT}/deploy/systemd/${SERVICE_NAME}.service"
SERVICE_DEST="/etc/systemd/system/${SERVICE_NAME}.service"
NGINX_TEMPLATE="${APP_ROOT}/deploy/nginx/dc-intern.conf.template"
NGINX_DEST=/etc/nginx/conf.d/dc-intern.conf
SERVER_NAME="${SERVER_NAME:-_}"
# Nginx's document root for the React build. This script only ensures it exists
# (an Nginx `root` pointing at a missing directory serves errors); the build
# itself is deploy_frontend.sh's job.
WEB_ROOT="${WEB_ROOT:-/var/www/dc-intern}"
FRONTEND_SCRIPT="${APP_ROOT}/deploy/scripts/deploy_frontend.sh"

step()  { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
info()  { printf '    %s\n' "$1"; }
fail()  { printf '\n\033[31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }

# --------------------------------------------------------------------------
step 'Preflight checks'
# --------------------------------------------------------------------------

[[ ${EUID} -ne 0 ]] || fail "Do not run this as root or with sudo. Run it as ec2-user; it will call sudo where needed."
[[ -d ${BACKEND_DIR} ]] || fail "${BACKEND_DIR} not found. Clone the repository to ${APP_ROOT} first."
[[ -f ${BACKEND_DIR}/manage.py ]] || fail "${BACKEND_DIR}/manage.py not found. Is ${APP_ROOT} the repository root?"
[[ -f ${SERVICE_SRC} ]] || fail "Missing ${SERVICE_SRC}."
[[ -f ${NGINX_TEMPLATE} ]] || fail "Missing ${NGINX_TEMPLATE}."

if [[ ! -r ${ENV_FILE} ]]; then
    fail "${ENV_FILE} is missing or not readable by $(id -un).
       Create it (root:ec2-user, chmod 640) with DEBUG, SECRET_KEY, ALLOWED_HOSTS,
       CORS_ALLOWED_ORIGINS, CSRF_TRUSTED_ORIGINS, the DB_* values and the AI_* values.
       This script deliberately does not create or fetch it."
fi

# Confirm the required keys are present WITHOUT printing any value.
missing_keys=()
for key in DEBUG SECRET_KEY ALLOWED_HOSTS DB_NAME DB_USER DB_PASSWORD DB_HOST; do
    grep -qE "^[[:space:]]*${key}=" "${ENV_FILE}" || missing_keys+=("${key}")
done
if (( ${#missing_keys[@]} > 0 )); then
    fail "${ENV_FILE} is missing these keys: ${missing_keys[*]}"
fi

# Optional keys: Django has a safe default for each (AI_PROVIDER falls back to
# `mock`, which makes no external call), so a missing one is worth saying out
# loud but is not a reason to refuse to deploy.
advisory_keys=()
for key in AI_PROVIDER AI_MODEL AWS_BEDROCK_REGION AI_FALLBACK_TO_MOCK; do
    grep -qE "^[[:space:]]*${key}=" "${ENV_FILE}" || advisory_keys+=("${key}")
done
if (( ${#advisory_keys[@]} > 0 )); then
    info "Not set (Django defaults apply, AI stays in mock mode): ${advisory_keys[*]}"
fi

if [[ ${SERVER_NAME} == '_' ]]; then
    info "SERVER_NAME not set; Nginx will accept any hostname (fine for a first smoke test)."
    info "Re-run with SERVER_NAME=<public-dns-name> once you know it."
else
    info "Nginx server_name: ${SERVER_NAME}"
fi
info "Environment file present with all required keys (values not shown)."

# --------------------------------------------------------------------------
step 'Python virtual environment'
# --------------------------------------------------------------------------

# Fail with an actionable message if the interpreter is too old, rather than
# letting pip fail later on an unsatisfiable Django requirement.
require_python() {
    local interpreter=$1 label=$2
    "${interpreter}" -c "import sys; sys.exit(0 if sys.version_info >= tuple(int(p) for p in '${MIN_PYTHON}'.split('.')) else 1)" \
        || fail "${label} is $("${interpreter}" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))'), but Django requires Python ${MIN_PYTHON} or newer.
       On Amazon Linux 2023: sudo dnf install -y python3.12 python3.12-pip
       Then re-run, optionally with PYTHON_BIN=/usr/bin/python3.12"
}

if [[ ! -x ${VENV_DIR}/bin/python ]]; then
    command -v "${PYTHON_BIN}" > /dev/null \
        || fail "${PYTHON_BIN} not found. Install it (sudo dnf install -y python3.12 python3.12-pip) or set PYTHON_BIN."
    require_python "${PYTHON_BIN}" "${PYTHON_BIN}"
    info "Creating ${VENV_DIR} with $("${PYTHON_BIN}" --version)"
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
else
    info "Reusing ${VENV_DIR}"
fi

# Also checks a pre-existing virtualenv, which may have been built by an older
# run of this script back when it defaulted to `python3`.
require_python "${VENV_DIR}/bin/python" "The virtualenv interpreter"

"${VENV_DIR}/bin/python" -m pip install --quiet --upgrade pip
info "Installing requirements"
"${VENV_DIR}/bin/pip" install --quiet --requirement "${BACKEND_DIR}/requirements.txt"
info "$("${VENV_DIR}/bin/python" --version), $("${VENV_DIR}/bin/gunicorn" --version)"

# --------------------------------------------------------------------------
step 'Django checks and database'
# --------------------------------------------------------------------------

# Run a manage.py command with the environment file loaded. `set -a` exports
# everything sourced; it happens inside a subshell so nothing leaks into the
# rest of this script, and no value is ever echoed.
manage() {
    (
        set -a
        # shellcheck disable=SC1090
        source "${ENV_FILE}"
        set +a
        cd "${BACKEND_DIR}"
        exec "${VENV_DIR}/bin/python" manage.py "$@"
    )
}

info 'manage.py check'
manage check

info 'manage.py check --deploy (advisory only)'
manage check --deploy || info 'Deployment warnings above are expected until TLS is configured.'

info 'manage.py check_database  (must report postgresql and OK)'
manage check_database

info 'manage.py migrate'
manage migrate --noinput

info 'manage.py collectstatic'
manage collectstatic --noinput

# --------------------------------------------------------------------------
step 'Gunicorn service'
# --------------------------------------------------------------------------

info "Installing ${SERVICE_DEST}"
sudo install -o root -g root -m 644 "${SERVICE_SRC}" "${SERVICE_DEST}"
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

# Give the service a moment to fail loudly if it is going to.
sleep 2
if ! systemctl is-active --quiet "${SERVICE_NAME}"; then
    printf '\n'
    sudo systemctl status "${SERVICE_NAME}" --no-pager --lines 20 || true
    fail "${SERVICE_NAME} did not start. Check: sudo journalctl -u ${SERVICE_NAME} -n 50"
fi
info "${SERVICE_NAME} is active"

# --------------------------------------------------------------------------
step 'Nginx'
# --------------------------------------------------------------------------

# The Nginx site now has `root /var/www/dc-intern`. Create it before reloading,
# so a backend-only deployment on a fresh instance cannot fail on a missing
# directory, and leave a holding page rather than an empty 403 if the frontend
# has not been deployed yet.
if [[ ! -d ${WEB_ROOT} ]]; then
    info "Creating ${WEB_ROOT} (frontend not deployed yet)"
    sudo install -d -o root -g root -m 755 "${WEB_ROOT}"
fi
if [[ ! -f ${WEB_ROOT}/index.html ]]; then
    printf '%s\n' \
        '<!doctype html><meta charset="utf-8"><title>DC-Intern</title>' \
        '<p>Backend deployed. The frontend has not been published yet —' \
        'run deploy/scripts/deploy_frontend.sh.</p>' \
        '<p>API health check: <a href="/api/health/">/api/health/</a></p>' \
        | sudo tee "${WEB_ROOT}/index.html" > /dev/null
    sudo chmod 644 "${WEB_ROOT}/index.html"
fi

info "Rendering ${NGINX_DEST}"
sed "s/SERVER_NAME_PLACEHOLDER/${SERVER_NAME}/" "${NGINX_TEMPLATE}" \
    | sudo tee "${NGINX_DEST}" > /dev/null

info 'nginx -t'
sudo nginx -t

sudo systemctl enable nginx
sudo systemctl restart nginx
info 'nginx restarted'

# --------------------------------------------------------------------------
step 'Smoke test'
# --------------------------------------------------------------------------

# Through Gunicorn directly, then through Nginx — this distinguishes an
# application failure from a proxy misconfiguration.
info 'Gunicorn  (127.0.0.1:8000/api/health/)'
curl --silent --show-error --fail --max-time 10 http://127.0.0.1:8000/api/health/ && printf '\n'

info 'Nginx     (127.0.0.1:80/api/health/)'
curl --silent --show-error --fail --max-time 10 http://127.0.0.1/api/health/ && printf '\n'

info 'Web root  (127.0.0.1:80/)'
curl --silent --show-error --fail --max-time 10 -o /dev/null -w '    HTTP %{http_code}\n' http://127.0.0.1/

# --------------------------------------------------------------------------
step 'Frontend'
# --------------------------------------------------------------------------

if [[ ${DEPLOY_FRONTEND:-0} == 1 ]]; then
    [[ -x ${FRONTEND_SCRIPT} ]] || fail "DEPLOY_FRONTEND=1 but ${FRONTEND_SCRIPT} is not executable."
    "${FRONTEND_SCRIPT}"
else
    info 'Not deployed by this script. To publish the React build:'
    info "    ${FRONTEND_SCRIPT}"
    info 'or re-run this script with DEPLOY_FRONTEND=1 to do both.'
fi

printf '\n\033[32mDeployment complete.\033[0m\n'
printf 'Logs:    sudo journalctl -u %s -f\n' "${SERVICE_NAME}"
printf 'Restart: sudo systemctl restart %s\n' "${SERVICE_NAME}"
