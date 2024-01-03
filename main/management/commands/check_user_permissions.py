# main/management/commands/check_user_permissions.py

from django.core.management.base import BaseCommand
from main.models import User  # Replace 'yourapp' with the actual name of your app

class Command(BaseCommand):
    help = 'Check permissions and groups of a user by username'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Specify the username for which to check permissions and groups')

    def handle(self, *args, **options):
        username = options['username']

        try:
            user = User.objects.get(username=username)
            permissions = user.get_all_permissions()
            groups = user.groups.all()

            self.stdout.write(self.style.SUCCESS(f'Permissions and groups for user {username}:'))
            
            if permissions:
                self.stdout.write(self.style.SUCCESS('Permissions:'))
                for permission in permissions:
                    self.stdout.write(self.style.SUCCESS(f'- {permission}'))
            else:
                self.stdout.write(self.style.SUCCESS('No permissions for this user'))

            if groups:
                self.stdout.write(self.style.SUCCESS('Groups:'))
                for group in groups:
                    self.stdout.write(self.style.SUCCESS(f'- {group.name}'))
            else:
                self.stdout.write(self.style.SUCCESS('No groups for this user'))

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with username {username} does not exist'))
