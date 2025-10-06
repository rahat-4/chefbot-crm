# from django.db.models.signals import post_save
# from django.dispatch import receiver

# from .emails import send_email_confirmation
# from .models import RegistrationSession


# @receiver(post_save, sender=RegistrationSession)
# def send_email_on_registration(sender, instance, created, **kwargs):
#     if created:
#         send_email_confirmation(
#             instance.email, f"{instance.first_name} {instance.last_name}", instance.uid
#         )
