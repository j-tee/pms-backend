from django.apps import AppConfig


class ExpensesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "expenses"
    verbose_name = "Expense Tracking"
    
    def ready(self):
        """Import signals when app is ready."""
        import expenses.signals  # noqa: F401
