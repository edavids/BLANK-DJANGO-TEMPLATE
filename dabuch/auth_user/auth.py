AUTH_USER_MODEL = 'accounts.User' #changes the built-in user model to ours
LOGIN_URL = '/login/'
LOGIN_URL_REDIRECT = '/'
LOGOUT_URL = '/logout/'
LOGOUT_REDIRECT_URL = '/login/'

FORCE_SESSION_TO_ONE = False
FORCE_INACTIVE_USER_ENDSESSION= False
