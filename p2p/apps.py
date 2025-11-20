from django.apps import AppConfig


class P2PConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'p2p'

    def ready(self):
        # import signals to ensure UserProfile auto-creation
        try:
            import p2p.signals  # noqa: F401
        except Exception:
            pass
