#  The context processor function
from django.shortcuts import render

from sales.models import Role
from sales.views import get_menu


def roles(request):
    all_roles = Role.objects.all()
    role = request.session.get('role')

    # role = 'GUEST'
    if not role:
        role = 'GUEST'
    request.session['role'] = role
    return {
        'roles': all_roles,
        'role': role,
        'mimenu': get_menu(request),
    }
