"""Database configuration selection.

Kept out of `settings.py` so the rule "SQLite locally, PostgreSQL when the
environment says so" is a plain function that can be unit-tested without
touching a real database.

The rule is deliberately driven by a single switch — `DB_HOST`:

* `DB_HOST` empty  -> SQLite file in the project folder (local development).
* `DB_HOST` set    -> PostgreSQL, using the other `DB_*` variables.

No credential is ever hard-coded here; every value arrives from the
environment.
"""

from django.core.exceptions import ImproperlyConfigured

# PostgreSQL connection tuning. Both matter on AWS:
# * CONN_MAX_AGE keeps a connection open between requests instead of paying
#   TCP + TLS setup on every call, but is kept short (60s) so idle Gunicorn
#   workers do not sit on RDS connection slots. CONN_HEALTH_CHECKS makes Django
#   verify a reused connection is still alive, which matters when RDS closes
#   idle connections or fails over to another Availability Zone.
# * CONNECT_TIMEOUT bounds how long a request waits on an unreachable database.
#   Without it, a misconfigured security group looks like a hung application
#   instead of a fast, obvious failure.
CONN_MAX_AGE_SECONDS = 60
CONNECT_TIMEOUT_SECONDS = 10

REQUIRED_POSTGRES_VARS = ('DB_NAME', 'DB_USER', 'DB_PASSWORD')


def build_database_config(
    base_dir,
    db_host='',
    db_name='',
    db_user='',
    db_password='',
    db_port='5432',
    db_sslmode='require',
    conn_max_age=CONN_MAX_AGE_SECONDS,
    connect_timeout=CONNECT_TIMEOUT_SECONDS,
):
    """Return the `DATABASES['default']` dictionary for the current environment.

    Args:
        base_dir: project root, used for the local SQLite file path.
        db_host: RDS endpoint. **Empty means "use SQLite"** — this is the switch.
        db_name, db_user, db_password: PostgreSQL credentials from the environment.
        db_port: PostgreSQL port, defaults to 5432.
        db_sslmode: libpq SSL mode, defaults to `require` so traffic to RDS is
            encrypted in transit.
        conn_max_age: seconds to reuse a connection for.
        connect_timeout: seconds to wait for a connection before failing.

    Raises:
        ImproperlyConfigured: if `db_host` is set but a required credential is
            missing. The names of the missing variables are reported; their
            values never are.
    """
    if not str(db_host or '').strip():
        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': base_dir / 'db.sqlite3',
        }

    provided = {
        'DB_NAME': str(db_name or '').strip(),
        'DB_USER': str(db_user or '').strip(),
        'DB_PASSWORD': str(db_password or ''),
    }
    missing = [name for name in REQUIRED_POSTGRES_VARS if not provided[name]]
    if missing:
        raise ImproperlyConfigured(
            'DB_HOST is set, so Django is configured for PostgreSQL, but these '
            f'environment variables are missing or empty: {", ".join(missing)}. '
            'Set them in the server environment (never in source control).'
        )

    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': provided['DB_NAME'],
        'USER': provided['DB_USER'],
        'PASSWORD': provided['DB_PASSWORD'],
        'HOST': str(db_host).strip(),
        'PORT': str(db_port or '5432').strip() or '5432',
        'CONN_MAX_AGE': conn_max_age,
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'sslmode': str(db_sslmode or 'require').strip() or 'require',
            'connect_timeout': connect_timeout,
        },
    }
