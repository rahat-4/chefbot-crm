from django.utils.translation import activate


class TranslatedChoiceSerializerMixin:
    """
    Mixin to automatically translate all choice fields in serializer
    """

    # Define which fields should be translated (optional - if not set, all choice fields will be translated)
    translated_choice_fields = None

    def to_representation(self, instance):
        """Override to add translated labels for choice fields"""
        data = super().to_representation(instance)

        # Get all choice fields from the model
        choice_fields = self._get_choice_fields(instance)

        # Transform each choice field
        for field_name in choice_fields:
            if (
                self.translated_choice_fields
                and field_name not in self.translated_choice_fields
            ):
                continue

            field_value = getattr(instance, field_name, None)
            if field_value:
                display_method = f"get_{field_name}_display"
                if hasattr(instance, display_method):
                    data[field_name] = {
                        "value": field_value,
                        "label": getattr(instance, display_method)(),
                    }

        return data

    def _get_choice_fields(self, instance):
        """Get all fields that have choices defined"""
        choice_fields = []

        for field in instance._meta.fields:
            if field.choices:
                choice_fields.append(field.name)

        return choice_fields

    def update(self, instance, validated_data):
        """Override update to activate new language if changed"""
        # Check if language field exists and is being updated
        if hasattr(instance, "language"):
            new_language = validated_data.get("language", instance.language)
            old_language = instance.language

            # Update the instance
            instance = super().update(instance, validated_data)

            # If language changed, activate it immediately for this response
            if new_language != old_language:
                self._activate_language(new_language)

            return instance

        return super().update(instance, validated_data)

    def _activate_language(self, language):
        """Helper method to activate language"""
        language_map = {
            "ENGLISH": "en",
            "GERMAN": "de",
        }
        language_code = language_map.get(language, "en")
        activate(language_code)
