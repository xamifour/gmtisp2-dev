# python manage.py load_users path/to/your/file.csv

import csv
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist

from ...models import User, Organization 

class Command(BaseCommand):
    help = 'Load users from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        
        with open(csv_file_path, mode='r') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                username = row['username']
                password = row['password']
                email = row['email']
                first_name = row['first_name']
                last_name = row['last_name']
                address = row['address']
                plain_password = row['plain_password']
                organization_id = row['organization']  # Assuming it's an ID or name

                # Get or create the organization
                try:
                    organization = Organization.objects.get(id=organization_id)
                except ObjectDoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Organization ID {organization_id} not found. Skipping user {username}."))
                    continue  # Skip if the organization is not found
                
                # Create or update the User
                user, created = User.objects.get_or_create(
                    username=username,
                    # password=password,
                    email=email,
                    defaults={
                        'password': password,
                        'first_name': first_name,
                        'last_name': last_name,
                        'address': address,
                        'plain_password': plain_password,
                        'organization': organization,
                    }
                )
                
                # If the user already exists, update fields that are not unique
                if not created:
                    user.password = password
                    user.first_name = first_name
                    user.last_name = last_name
                    user.address = address
                    user.plain_password = plain_password
                    user.organization = organization
                    user.save()

                # Output success message
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created user {username}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"Updated user {username}"))



# # python manage.py load_users path/to/your/file.csv

# import csv
# from django.core.management.base import BaseCommand
# from django.core.exceptions import ObjectDoesNotExist

# from ...models import User, Organization 

# class Command(BaseCommand):
#     help = 'Load users from a CSV file'

#     def add_arguments(self, parser):
#         parser.add_argument('csv_file', type=str, help='Path to the CSV file')

#     def handle(self, *args, **options):
#         csv_file_path = options['csv_file']
        
#         with open(csv_file_path, mode='r') as file:
#             reader = csv.DictReader(file)
            
#             for row in reader:
#                 username = row['username']
#                 email = row['email']
#                 first_name = row['first_name']
#                 last_name = row['last_name']
#                 address = row['address']
#                 plain_password = row['plain_password']
#                 organization_id = row['organization']  # Assuming it's an ID or name

#                 # Get or create the organization
#                 try:
#                     organization = Organization.objects.get(id=organization_id)
#                 except ObjectDoesNotExist:
#                     self.stdout.write(self.style.WARNING(f"Organization ID {organization_id} not found. Skipping user {username}."))
#                     continue  # Skip if the organization is not found
                
#                 # Create or update the User
#                 user, created = User.objects.get_or_create(
#                     username=username,
#                     email=email,
#                     defaults={
#                         'first_name': first_name,
#                         'last_name': last_name,
#                         'address': address,
#                         'plain_password': plain_password,
#                         'organization': organization,
#                     }
#                 )
                
#                 # If the user already exists, update fields that are not unique
#                 if not created:
#                     user.first_name = first_name
#                     user.last_name = last_name
#                     user.address = address
#                     user.plain_password = plain_password
#                     user.organization = organization
#                     user.save()

#                 # Output success message
#                 if created:
#                     self.stdout.write(self.style.SUCCESS(f"Created user {username}"))
#                 else:
#                     self.stdout.write(self.style.SUCCESS(f"Updated user {username}"))
