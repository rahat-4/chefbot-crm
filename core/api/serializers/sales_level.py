from rest_framework import serializers


from apps.restaurant.models import SalesLevel


class SalesLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesLevel
        fields = [
            "uid",
            "name",
            "level",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sales_level = self._get_sales_level()
        self._add_dynamic_fields()

    def _get_sales_level(self):
        """Get the sales level from the instance or context."""

        if self.instance:
            return self.instance.level

        if hasattr(self, "context") and "request" in self.context:
            sales_level_uid = (
                self.context["request"]
                .parser_context.get("kwargs")
                .get("sales_level_uid")
            )

            if sales_level_uid:
                try:
                    return SalesLevel.objects.get(uid=sales_level_uid).level
                except SalesLevel.DoesNotExist:
                    pass
        return 1

    def _add_dynamic_fields(self):
        """Add dynamic fields based on the sales level."""
        if self.sales_level >= 2:
            self.fields["menu_reward_type"] = serializers.CharField()
            self.fields["menu_reward_label"] = serializers.CharField()
        elif self.sales_level >= 3:
            pass
        elif self.sales_level >= 4:
            self.fields["personalization_enabled"] = serializers.BooleanField()
        elif self.sales_level == 5:
            pass

    def validate(self, attrs):
        errors = {}
        level = self.sales_level

        if level == 2:
            if not attrs.get("menu_reward_type"):
                errors["menu_reward_type"] = [
                    "Menu reward type is required for level 2."
                ]
            if not attrs.get("menu_reward_label"):
                errors["menu_reward_label"] = [
                    "Menu reward label is required for level 2."
                ]

        if errors:
            raise serializers.ValidationError(errors)

        return attrs
