from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from core.admin_site import yea_admin_site

User = get_user_model()


class UserAdmin(BaseUserAdmin):
    """Admin interface for the custom User model."""
    
    list_display = (
        'username', 'email', 'phone', 'role', 'region', 'constituency',
        'is_verified', 'is_active', 'is_staff', 'date_joined'
    )
    list_filter = (
        'role', 'is_verified', 'is_active', 'is_staff',
        'region', 'constituency', 'date_joined'
    )
    search_fields = ('username', 'email', 'phone', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'preferred_contact_method')
        }),
        ('Role & Location', {
            'fields': ('role', 'region', 'constituency')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'last_login_at', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'phone', 'password1', 'password2',
                'first_name', 'last_name', 'role', 'preferred_contact_method',
                'region', 'constituency'
            ),
        }),
    )
    
    
    readonly_fields = ('date_joined', 'last_login', 'last_login_at')


# Register with custom admin site
yea_admin_site.register(User, UserAdmin)
