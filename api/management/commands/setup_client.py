"""
Bootstrap a fresh database with one company + its master admin user + the
default CodeMaster seed (board_category, event_category, job_level, job_title,
team). Used to onboard a new client deployment.

Workflow:
    1. Create a new empty MySQL database for the client.
    2. Configure the .env to point Django at it.
    3. Run `python manage.py migrate`.
    4. Run `python manage.py setup_client ...` (this command).
    5. Hand off the admin credentials to the client.

Any arg you omit will be prompted for interactively.
"""

from getpass import getpass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.admin.company import create_company_with_defaults
from api.models import CompanyMaster, UserMaster


class Command(BaseCommand):
    help = 'Bootstrap a fresh DB with one company + its admin user + default codes.'

    def add_arguments(self, parser):
        parser.add_argument('--code', help='Company code (e.g., ACME-001)')
        parser.add_argument('--name', help='Company display name')
        parser.add_argument('--admin-id', help='Admin login user_id')
        parser.add_argument('--admin-password', help='Admin password (omit to prompt securely)')
        parser.add_argument('--admin-email', default='', help='Admin email (optional)')
        parser.add_argument('--admin-name', default='관리자', help="Admin display name (default '관리자')")
        parser.add_argument('--force', action='store_true', help='Skip the non-empty-DB confirmation prompt')

    def handle(self, *args, **options):
        existing = CompanyMaster.objects.count()
        if existing > 0 and not options['force']:
            self.stdout.write(self.style.WARNING(
                f'This DB already has {existing} company row(s):'
            ))
            for c in CompanyMaster.objects.values('id', 'code', 'name'):
                self.stdout.write(f"  - id={c['id']} code={c['code']} name={c['name']}")
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'Continue anyway? This will ADD a new company alongside existing ones.'
            ))
            if input('Type "yes" to proceed: ').strip().lower() != 'yes':
                raise CommandError('Aborted.')

        code = (options['code'] or input('회사 코드 (Company code): ')).strip()
        name = (options['name'] or input('회사 이름 (Company name): ')).strip()
        admin_id = (options['admin_id'] or input('관리자 ID (Admin login): ')).strip()

        password = options['admin_password']
        if not password:
            password = getpass('관리자 비밀번호 (Admin password): ')
            if password != getpass('비밀번호 확인 (Confirm password): '):
                raise CommandError('Passwords do not match.')

        admin_email = (options['admin_email'] or input('관리자 이메일 (Admin email, blank to skip): ')).strip()
        admin_name = options['admin_name'] or '관리자'

        for field_label, value in [
            ('--code', code),
            ('--name', name),
            ('--admin-id', admin_id),
            ('--admin-password', password),
        ]:
            if not value:
                raise CommandError(f'{field_label} is required.')

        if CompanyMaster.objects.filter(code=code).exists():
            raise CommandError(f'Company with code "{code}" already exists.')
        if UserMaster.objects.filter(user_id=admin_id).exists():
            raise CommandError(f'User with user_id "{admin_id}" already exists.')

        with transaction.atomic():
            company, master_user = create_company_with_defaults(
                code=code,
                name=name,
                master_id=admin_id,
                master_password=password,
                signup_email=admin_email,
                master_name=admin_name,
            )

        self.stdout.write(self.style.SUCCESS(
            f'\nClient setup complete.\n'
            f'  Company: id={company.id} code={company.code} name={company.name}\n'
            f'  Admin:   user_id={master_user.user_id} email={master_user.email or "(none)"}\n'
            f'\n  Login at /login/ with user_id "{master_user.user_id}" and the password you set.'
        ))
