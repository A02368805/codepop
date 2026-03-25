from django.urls import path

from .views import (
    AdminDashboardView,
    AdminUserManagementView,
    AdminUserUpdateView,
    CustomerDashboardView,
    FloatStackLoginView,
    FloatStackLogoutView,
    HomePageView,
    LogisticsDashboardView,
    ManagerDashboardView,
    PreferenceView,
    RegisterView,
    RepairDashboardView,
    RoleAwareDashboardRedirectView,
    SuperAdminDashboardView,
)

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("login/", FloatStackLoginView.as_view(), name="login"),
    path("logout/", FloatStackLogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
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
