from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.models import User
from accounts.permissions import role_required
from core.team_forms import StaffCreationForm


@role_required(User.Role.ADMIN)
def team_index(request):
    staff = User.objects.filter(role=User.Role.STAFF).order_by("last_name", "first_name", "email")
    return render(request, "core/team/list.html", {"staff": staff})


@role_required(User.Role.ADMIN)
def staff_create(request):
    form = StaffCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            form.create_user()
        except Exception as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Staff account created.")
            return redirect("team:list")
    return render(request, "core/team/form.html", {"form": form})
