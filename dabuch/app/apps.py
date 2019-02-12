INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Importing apps from a single directory for easy change
    'tasks.apps.TasksConfig',
    'accounts.apps.AccountsConfig',
]