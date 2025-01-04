import csv
from django.core.management.base import BaseCommand
from ...models import User, Organization  # Adjust the import based on your actual app name

class Command(BaseCommand):
    help = 'Export users and their associated organization data to a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file where data should be exported')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        
        # Open the CSV file for writing
        with open(csv_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            
            # Write the header row with the appropriate field names
            writer.writerow([
                'username', 'email', 'first_name', 'last_name', 'address', 'organization_id', 'organization_name', 'plain_password'
            ])

            # Query all users and their related organizations
            users = User.objects.select_related('organization').all()
            
            # Iterate through each user and write a row to the CSV
            for user in users:
                organization_id = user.organization.id if user.organization else ''
                organization_name = user.organization.name if user.organization else ''  # Assuming 'name' field exists in Organization model
                
                # Write user and organization data to the CSV file
                writer.writerow([
                    user.username, 
                    user.email, 
                    user.first_name, 
                    user.last_name, 
                    user.address, 
                    organization_id, 
                    organization_name, 
                    user.plain_password
                ])
        
        self.stdout.write(self.style.SUCCESS(f'Successfully exported user data to {csv_file_path}'))
