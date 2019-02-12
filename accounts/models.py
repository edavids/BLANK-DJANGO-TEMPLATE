from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import get_template
from django.utils import timezone
from django.urls import reverse
from django.db.models import Q
from django.db.models.signals import pre_save, post_save
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager
)

from dabuch.utils import random_string_generator, unique_key_generator

#Email Activation Days before expiration
DEFAULT_ACTIVATION_DAYS = getattr(settings, 'DEFAULT_ACTIVATION_DAYS', 7)


# Create your models here.
class UserManager(BaseUserManager):
    def create_user(self, email, company_name=None, password=None, is_active=True, is_client=True, is_staff=False, is_superuser=False):
        if not email:
            raise ValueError("Users must have an email address")
        if not company_name:
            raise ValueError("Users must have a company name")
        if not password:
            raise ValueError("Users must have a password")
        user_obj = self.model(
            email = self.normalize_email(email),
            company_name=company_name
        )
        user_obj.set_password(password) # change user password
        user_obj.client = is_client
        user_obj.staff = is_staff
        user_obj.admin = is_superuser
        user_obj.is_active = is_active
        user_obj.save(using=self._db)
        return user_obj

    def create_clientuser(self, email, company_name=None, password=None):
        user = self.create_user(
                email,
                company_name=company_name,
                password=password,
                is_client=True
        )
        return user

    def create_staffuser(self, email, company_name=None, password=None):
        user = self.create_user(
                email,
                company_name=company_name,
                password=password,
                is_client=True,
                is_staff=True
        )
        return user

    def create_superuser(self, email, company_name=None, password=None):
        user = self.create_user(
                email,
                company_name=company_name,
                password=password,
                is_client=True,
                is_staff=True,
                is_superuser=True
        )
        return user


class User(AbstractBaseUser):
    email           = models.EmailField(max_length=255, unique=True)
    company_name    = models.CharField(max_length=255, blank=False, null=True, unique=True)
    is_active       = models.BooleanField(default=True) # can login 
    client          = models.BooleanField(default=True)
    staff           = models.BooleanField(default=False) # staff user non superuser
    admin           = models.BooleanField(default=False) # superuser 
    timestamp       = models.DateTimeField(auto_now_add=True)
    # confirm     = models.BooleanField(default=False)
    # confirmed_date     = models.DateTimeField(default=False)

    USERNAME_FIELD = 'email' #username
    # USERNAME_FIELD and password are required by default
    REQUIRED_FIELDS = ['company_name'] #['full_name'] #python manage.py createsuperuser

    objects = UserManager()

    def __str__(self):
        return self.email

    def get_full_name(self):
        if self.company_name:
            return self.company_name
        return self.email

    def get_short_name(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_client(self):
        if self.is_superuser or self.is_staff:
            return True
        return self.client

    @property
    def is_staff(self):
        if self.is_superuser:
            return True
        return self.staff

    @property
    def is_superuser(self):
        return self.admin

    # @property
    # def is_active(self):
    #     return self.active


class EmailActivationQuerySet(models.query.QuerySet):
    def confirmable(self):
        now = timezone.now()
        start_range = now - timedelta(days=DEFAULT_ACTIVATION_DAYS)
        # does my object have a timestamp in here
        end_range = now
        return self.filter(
                activated = False,
                forced_expired = False
              ).filter(
                timestamp__gt=start_range,
                timestamp__lte=end_range
              )


class EmailActivationManager(models.Manager):
    def get_queryset(self):
        return EmailActivationQuerySet(self.model, using=self._db)

    def confirmable(self):
        return self.get_queryset().confirmable()

    def email_exists(self, email):
        return self.get_queryset().filter(
                    Q(email=email) | 
                    Q(user__email=email)
                ).filter(
                    activated=False
                )


class EmailActivation(models.Model):
    user            = models.ForeignKey(User, on_delete=models.CASCADE)
    email           = models.EmailField()
    key             = models.CharField(max_length=120, blank=True, null=True)
    activated       = models.BooleanField(default=False)
    forced_expired  = models.BooleanField(default=False)
    expires         = models.IntegerField(default=7) # 7 Days
    timestamp       = models.DateTimeField(auto_now_add=True)
    update          = models.DateTimeField(auto_now=True)

    objects = EmailActivationManager()

    def __str__(self):
        return self.email

    def can_activate(self):
        qs = EmailActivation.objects.filter(pk=self.pk).confirmable() # 1 object
        if qs.exists():
            return True
        return False

    def activate(self):
        if self.can_activate():
            # pre activation user signal
            user = self.user
            user.is_active = True
            user.client = True
            user.save()
            # post activation signal for user
            self.activated = True
            self.save()
            return True
        return False

    def regenerate(self):
        self.key = None
        self.save()
        if self.key is not None:
            return True
        return False

    def send_activation(self):
        if not self.activated and not self.forced_expired:
            if self.key:
                base_url = getattr(settings, 'BASE_URL', 'https://www.dabuch.com')
                key_path = reverse("account:email-activate", kwargs={'key': self.key}) # use reverse
                path = "{base}{path}".format(base=base_url, path=key_path)
                context = {
                    'path': path,
                    'email': self.email
                }
                txt_ = get_template("registration/emails/verify.txt").render(context)
                html_ = get_template("registration/emails/verify.html").render(context)
                subject = '1-Click Email Verification'
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [self.email]
                sent_mail = send_mail(
                            subject,
                            txt_,
                            from_email,
                            recipient_list,
                            html_message=html_,
                            fail_silently=False,
                    )
                return sent_mail
        return False



def pre_save_email_activation(sender, instance, *args, **kwargs):
    if not instance.activated and not instance.forced_expired:
        if not instance.key:
            instance.key = unique_key_generator(instance)

pre_save.connect(pre_save_email_activation, sender=EmailActivation)


def post_save_user_create_reciever(sender, instance, created, *args, **kwargs):
    if created:
        obj = EmailActivation.objects.create(user=instance, email=instance.email)
        obj.send_activation()

post_save.connect(post_save_user_create_reciever, sender=User)