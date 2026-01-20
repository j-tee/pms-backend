from django.apps import AppConfig


class FlockManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "flock_management"
    
    def ready(self):
        """
        Import signals to register them when the app is ready.
        
        This enables automatic expense record creation when mortality is recorded.
        """
        import flock_management.signals  # noqa: F401
