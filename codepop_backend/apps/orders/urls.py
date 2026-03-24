from django.urls import path

from .views import (
    AccountOrderHistoryView,
    BuilderAiFillView,
    CartItemRemoveView,
    CartItemUpdateView,
    BuilderAssistantView,
    CartView,
    CheckoutValidateView,
    CheckoutView,
    CustomizeDrinkView,
    FavoriteAddToCartView,
    FavoriteListView,
    FavoriteRemoveView,
    GuestLookupView,
    MarkPickedUpView,
    MarkPreparingView,
    MarkReadyView,
    MenuView,
    OrderCancelView,
    OrderConfirmationView,
    OrderDetailView,
    OrderWorkspaceView,
    RecommendationView,
)


app_name = "orders"

urlpatterns = [
    path("", OrderWorkspaceView.as_view(), name="index"),
    path("menu/<str:store_code>/", MenuView.as_view(), name="menu"),
    path(
        "menu/<str:store_code>/<slug:drink_slug>/",
        CustomizeDrinkView.as_view(),
        name="customize",
    ),
    path(
        "menu/<str:store_code>/<slug:drink_slug>/assistant/",
        BuilderAssistantView.as_view(),
        name="assistant",
    ),
    path(
        "menu/<str:store_code>/<slug:drink_slug>/ai-fill/",
        BuilderAiFillView.as_view(),
        name="ai-fill",
    ),
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/<str:item_id>/update/", CartItemUpdateView.as_view(), name="cart-item-update"),
    path("cart/items/<str:item_id>/remove/", CartItemRemoveView.as_view(), name="cart-item-remove"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("checkout/validate/", CheckoutValidateView.as_view(), name="checkout-validate"),
    path("confirmation/<str:order_code>/", OrderConfirmationView.as_view(), name="confirmation"),
    path("lookup/", GuestLookupView.as_view(), name="guest-lookup"),
    path("history/", AccountOrderHistoryView.as_view(), name="history"),
    path("favorites/", FavoriteListView.as_view(), name="favorites"),
    path("favorites/<uuid:favorite_id>/remove/", FavoriteRemoveView.as_view(), name="favorite-remove"),
    path("favorites/<uuid:favorite_id>/add-to-cart/", FavoriteAddToCartView.as_view(), name="favorite-add-to-cart"),
    path("recommendations/", RecommendationView.as_view(), name="recommendations"),
    path("<str:order_code>/", OrderDetailView.as_view(), name="detail"),
    path("<str:order_code>/cancel/", OrderCancelView.as_view(), name="cancel"),
    path("<uuid:order_id>/mark-preparing/", MarkPreparingView.as_view(), name="mark-preparing"),
    path("<uuid:order_id>/mark-ready/", MarkReadyView.as_view(), name="mark-ready"),
    path("<uuid:order_id>/mark-picked-up/", MarkPickedUpView.as_view(), name="mark-picked-up"),
]
