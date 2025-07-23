from django.contrib import admin

from .models import SalesLevel, Menu

admin.site.register(Menu)
admin.site.register(SalesLevel)

# @admin.register(SalesLevel)
# class SalesLevelAdmin(admin.ModelAdmin):
#     list_display = [
#         "level",
#         "personalization_enabled",
#         "menu_reward_type",
#     ]
#     list_filter = ["level", "personalization_enabled", "menu_reward_type"]

# fieldsets = (
#     ("Basic Configuration", {"fields": ("level")}),
#     (
#         "Menu Reward (Level 2+)",
#         {
#             "fields": ("menu_reward_type", "menu_reward_label"),
#             "classes": ("collapse",),
#         },
#     ),
#     (
#         "Personalization (Level 4+)",
#         {"fields": ("personalization_enabled",), "classes": ("collapse",)},
#     ),
# )
