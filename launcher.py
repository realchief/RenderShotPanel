from django.contrib.auth.models import User


def startup():

    # create admin super user
    User.objects.create_superuser('admin', 'admin@admin.com', 'admin')

    # create hamed test user
    User.objects.get_or_create(username='hamed', email='hamedhematyar91@admin.com', password='hamed')


startup()