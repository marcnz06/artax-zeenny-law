from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Sets up user groups and permissions'

    def handle(self, *args, **options):
        user_content_type = ContentType.objects.get(app_label='main', model="user")
        book_content_type = ContentType.objects.get(app_label='books', model="book")
        loc_content_type = ContentType.objects.get(app_label='books', model="location")
        author_content_type = ContentType.objects.get(app_label='books', model="author")

        user_permissions = [
            Permission.objects.get(codename=code, content_type=user_content_type)
            for code in ['view_user', 'change_user', 'delete_user', 'add_user']
        ]

        book_permissions = [
            Permission.objects.get(codename=code, content_type=book_content_type)
            for code in ['view_book', 'change_book', 'delete_book', 'add_book']
        ]

        loc_permissions = [
            Permission.objects.get(codename=code, content_type=loc_content_type)
            for code in ['view_location', 'change_location', 'delete_location', 'add_location']
        ]

        author_permissions = [
            Permission.objects.get(codename=code, content_type=author_content_type)
            for code in ['view_author', 'change_author', 'delete_author', 'add_author']
        ]

        # Define your groups and assign permissions
        group_permissions = {
            'Visitor': [book_permissions[0]] + [user_permissions[0]],
            'Lawyer': book_permissions[:2] + user_permissions[:2],
            'Office Administrator': book_permissions + user_permissions + loc_permissions + author_permissions,
            'System Administrator': Permission.objects.all(),
        }

        for group_name, permissions in group_permissions.items():
            group, created = Group.objects.get_or_create(name=group_name)
            group.permissions.set(permissions)

            if created:
                self.stdout.write(self.style.SUCCESS(f'All permissions assigned to group: {group_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Group already exists. Permissions not assigned for: {group_name}'))
