from django.urls import path

from .views import (
    SupportConversationDetailView,
    SupportEscalateView,
    SupportHomeView,
    SupportSendView,
    SupportStartView,
)

app_name = "support"

urlpatterns = [
    path("", SupportHomeView.as_view(), name="index"),
    path("start/", SupportStartView.as_view(), name="start"),
    path(
        "conversations/<uuid:conversation_id>/",
        SupportConversationDetailView.as_view(),
        name="conversation-detail",
    ),
    path("send/<uuid:conversation_id>/", SupportSendView.as_view(), name="send"),
    path(
        "escalate/<uuid:conversation_id>/",
        SupportEscalateView.as_view(),
        name="escalate",
    ),
]
