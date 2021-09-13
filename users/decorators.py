from functools import wraps
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib.auth.models import User


def blocked_validation(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        try:
            if request.user.profile.blocked:
                return redirect('logout')
        except Exception as err:
            print(err)
        return function(request, *args, **kwargs)
    return wrap


def reset_password_validation(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        try:
            if request.user.profile.reset_password_required:
                return redirect('user_password_reset')
        except Exception as err:
            print(err)
        return function(request, *args, **kwargs)
    return wrap