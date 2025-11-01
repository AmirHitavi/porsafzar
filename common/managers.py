from django.db import models


class BaseSafeDeleteManager(models.Manager):
    """
    Base manager that contains methods for SafeDelete operations.
    """

    def get_queryset(self):
        """
        Returns all objects.
        Override this method in Subclasses.
        """
        return super().get_queryset()


class AllObjectsManager(BaseSafeDeleteManager):
    """
    Returns all objects
    """

    pass


class ActiveObjectsManager(BaseSafeDeleteManager):
    """
    Returns only active (non-deleted) objects.
    """

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class DeletedObjectsManager(BaseSafeDeleteManager):
    """
    Returns only deleted objects.
    """

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=False)
