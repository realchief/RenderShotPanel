from django.contrib import admin

app_list_order = {'sites': 0,
                  'auth': 10,
                  'users': 20,
                  'job': 33,
                  'ticketing': 40,
                  'payment': 50,
                  'system': 60,
                  'authtoken': 70,
                  'advanced_filters': 80,
                  }


class MyAdminSite(admin.AdminSite):

    def get_app_list(self, request):
        app_list = sorted(super(MyAdminSite, self).get_app_list(request), key=lambda x: app_list_order[x['app_label']])
        return app_list
