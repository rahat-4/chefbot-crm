from django.db import models


class OrganizationQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(organization_users__user=user)

    def restaurants(self):
        from apps.organization.models import OrganizationType

        return self.filter(organization_type=OrganizationType.RESTAURANT)
