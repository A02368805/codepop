from django.urls import path

from .views import (
    AdminDashboardView,
    AdminUserManagementView,
    AdminUserUpdateView,
    CodePopLoginView,
    CodePopLogoutView,
    CustomerDashboardView,
    HomePageView,
    LogisticsDashboardView,
    ManagerDashboardView,
    PeerValidateView,
    PreferenceView,
    RegisterView,
    RepairDashboardView,
    RoleAwareDashboardRedirectView,
    SuperAdminDashboardView,
)

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("login/", CodePopLoginView.as_view(), name="login"),
    path("logout/", CodePopLogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path(
        "peer-validate/",
        PeerValidateView.as_view(),
        name="peer-validate",
    ),
    path("dashboard/", RoleAwareDashboardRedirectView.as_view(), name="dashboard"),
    path("account/preferences/", PreferenceView.as_view(), name="account-preferences"),
    path("admin/users/", AdminUserManagementView.as_view(), name="admin-users"),
    path(
        "admin/users/<uuid:user_id>/update/",
        AdminUserUpdateView.as_view(),
        name="admin-user-update",
    ),
    path(
        "dashboards/customer/",
        CustomerDashboardView.as_view(),
        name="customer-dashboard",
    ),
    path(
        "dashboards/manager/",
        ManagerDashboardView.as_view(),
        name="manager-dashboard",
    ),
    path(
        "dashboards/admin/",
        AdminDashboardView.as_view(),
        name="admin-dashboard",
    ),
    path(
        "dashboards/logistics/",
        LogisticsDashboardView.as_view(),
        name="logistics-dashboard",
    ),
    path(
        "dashboards/repair/",
        RepairDashboardView.as_view(),
        name="repair-dashboard",
    ),
    path(
        "dashboards/super-admin/",
        SuperAdminDashboardView.as_view(),
        name="super-admin-dashboard",
    ),
]
