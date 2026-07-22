"""`python manage.py check_database` — report and verify the database Django is using.

Useful in three places:
  * locally, to confirm you are still on SQLite;
  * on EC2 after setting environment variables, to prove Django reads them;
  * on EC2 when connectivity fails, to tell "wrong settings" apart from
    "security group is blocking me".

The database password is never printed, in any mode.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, connections


def mask_host(host):
    """Show enough of an endpoint to identify it, without publishing it in full.

    `careerdb.abc123.eu-west-1.rds.amazonaws.com` -> `ca***.eu-west-1.rds.amazonaws.com`
    An RDS endpoint is not a credential, but it is infrastructure detail that
    ends up in screenshots and reports, so it is masked unless asked for.
    """
    if not host:
        return '(not set)'
    head, separator, tail = host.partition('.')
    if not separator:
        return f'{head[:2]}***' if len(head) > 2 else '***'
    return f'{head[:2]}***.{tail}' if len(head) > 2 else f'***.{tail}'


class Command(BaseCommand):
    help = 'Show which database Django is configured to use and verify it responds.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--show-host',
            action='store_true',
            help='Print the database host in full instead of masking it.',
        )
        parser.add_argument(
            '--database',
            default=DEFAULT_DB_ALIAS,
            help=f'Database alias to check (default: {DEFAULT_DB_ALIAS}).',
        )

    def handle(self, *args, **options):
        alias = options['database']
        if alias not in settings.DATABASES:
            raise CommandError(f'No database alias named {alias!r} is configured.')

        db_settings = settings.DATABASES[alias]
        connection = connections[alias]
        engine = db_settings.get('ENGINE', '')
        is_sqlite = engine.endswith('sqlite3')

        self.stdout.write(self.style.MIGRATE_HEADING('Database configuration'))
        self.stdout.write(f'  Alias:    {alias}')
        self.stdout.write(f'  Engine:   {engine}')
        self.stdout.write(f'  Vendor:   {connection.vendor}')

        if is_sqlite:
            self.stdout.write(f'  File:     {db_settings.get("NAME")}')
            self.stdout.write(
                '  Mode:     local development (DB_HOST is not set, so SQLite is used)'
            )
        else:
            host = db_settings.get('HOST') or ''
            options_ = db_settings.get('OPTIONS') or {}
            self.stdout.write(f'  Name:     {db_settings.get("NAME")}')
            self.stdout.write(f'  User:     {db_settings.get("USER")}')
            self.stdout.write(
                '  Host:     '
                + (host if options['show_host'] else f'{mask_host(host)}  (masked; use --show-host)')
            )
            self.stdout.write(f'  Port:     {db_settings.get("PORT")}')
            self.stdout.write(f'  SSL mode: {options_.get("sslmode")}')
            self.stdout.write(f'  Timeout:  {options_.get("connect_timeout")}s')
            self.stdout.write(f'  Max age:  {db_settings.get("CONN_MAX_AGE")}s')
            # Report only whether a password exists — never its value or length.
            self.stdout.write(
                '  Password: ' + ('set (not shown)' if db_settings.get('PASSWORD') else 'NOT SET')
            )
            self.stdout.write(
                '  Mode:     PostgreSQL (DB_HOST is set, so Django targets Amazon RDS)'
            )

        self.stdout.write('')
        self.stdout.write('Running SELECT 1 ...')

        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                row = cursor.fetchone()
        except Exception as exc:
            raise CommandError(self._clean_error(exc, db_settings)) from None

        if not row or row[0] != 1:
            raise CommandError(f'Database responded with an unexpected result: {row!r}')

        self.stdout.write(self.style.SUCCESS('OK — the database is reachable and responding.'))

    @staticmethod
    def _clean_error(exc, db_settings):
        """Turn a driver exception into a short, actionable, password-free message."""
        detail = str(exc).strip() or exc.__class__.__name__

        # Belt and braces: some drivers echo the connection string back in errors.
        password = db_settings.get('PASSWORD')
        if password:
            detail = detail.replace(password, '***')

        hint = (
            'Check that DB_HOST/DB_NAME/DB_USER/DB_PASSWORD are correct, that this '
            'machine is inside the VPC, and that the RDS security group allows '
            'PostgreSQL from this instance\'s security group.'
            if not db_settings.get('ENGINE', '').endswith('sqlite3')
            else 'Check that migrations have been run (python manage.py migrate).'
        )
        return f'Could not query the database.\n  Reason: {detail}\n  Hint: {hint}'
