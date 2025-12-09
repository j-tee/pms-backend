"""
Management command to create YEA National Admin user for testing.

Usage:
    python manage.py create_yea_admin
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User


class Command(BaseCommand):
    help = 'Creates YEA National Admin user for testing'

    def handle(self, *args, **options):
        email = 'mikedlt009@gmail.com'
        username = 'adminuser'
        password = 'testuser123'
        
        try:
            with transaction.atomic():
                # Check if user already exists
                if User.objects.filter(email=email).exists():
                    user = User.objects.get(email=email)
                    self.stdout.write(
                        self.style.WARNING(f'User with email {email} already exists.')
                    )
                    
                    # Update user to ensure correct settings
                    user.username = username
                    user.role = User.UserRole.NATIONAL_ADMIN
                    user.is_active = True
                    user.is_verified = True
                    user.email_verified = True
                    user.phone_verified = True
                    user.is_staff = True
                    user.set_password(password)
                    user.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Updated existing user: {username}')
                    )
                else:
                    # Create new user
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name='YEA',
                        last_name='Admin',
                        role=User.UserRole.NATIONAL_ADMIN,
                        phone='+233241234567',  # Placeholder phone
                        is_active=True,
                        is_verified=True,
                        email_verified=True,
                        phone_verified=True,
                        is_staff=True,
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Created new user: {username}')
                    )
                
                # Display user details
                self.stdout.write('\n' + '='*60)
                self.stdout.write(self.style.SUCCESS('YEA NATIONAL ADMIN USER CREATED/UPDATED'))
                self.stdout.write('='*60)
                self.stdout.write(f'Username:       {user.username}')
                self.stdout.write(f'Email:          {user.email}')
                self.stdout.write(f'Password:       {password}')
                self.stdout.write(f'Role:           {user.get_role_display()}')
                self.stdout.write(f'Is Active:      {user.is_active}')
                self.stdout.write(f'Is Verified:    {user.is_verified}')
                self.stdout.write(f'Email Verified: {user.email_verified}')
                self.stdout.write(f'Phone Verified: {user.phone_verified}')
                self.stdout.write(f'Is Staff:       {user.is_staff}')
                self.stdout.write('='*60)
                self.stdout.write('\n' + self.style.SUCCESS('LOGIN INSTRUCTIONS:'))
                self.stdout.write('1. POST to /api/auth/login/ with:')
                self.stdout.write('   {')
                self.stdout.write(f'     "username": "{username}",')
                self.stdout.write(f'     "password": "{password}"')
                self.stdout.write('   }')
                self.stdout.write('\n2. Use the returned access token for admin API calls:')
                self.stdout.write('   Authorization: Bearer <access_token>')
                self.stdout.write('\n3. Access admin dashboard:')
                self.stdout.write('   GET /api/admin/dashboard/overview/')
                self.stdout.write('='*60 + '\n')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating user: {str(e)}')
            )
            raise
