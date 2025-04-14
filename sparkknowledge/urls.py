from django.urls import path

from . import views

app_name = "sparkknowledge"

urlpatterns = [
    path("", views.setup_view, name="setup"),
    path("sparkknowledge/<int:attempt_id>/", views.quiz_run_view, name="quiz_run"),
    path("attempts/", views.attempt_list_view, name="attempt_list"),
    path(
        "attempts/<int:attempt_id>/", views.attempt_detail_view, name="attempt_detail"
    ),
    path("about/", views.about_view, name="about"),
]
