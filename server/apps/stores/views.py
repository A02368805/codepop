from apps.users.permissions import user_can_use_customer_ordering
from django.conf import settings
from django.shortcuts import render
from django.views.generic import TemplateView

from .forms import StoreRecommendationForm
from .models import Region, Store
from .services import recommend_stores


class StoreIndexView(TemplateView):
    template_name = "stores/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = StoreRecommendationForm(self.request.GET or None)
        pickup_time_requested = None
        latitude = None
        longitude = None
        location_query = ""
        if form.is_valid():
            pickup_time_requested = form.cleaned_data.get("pickup_time_requested")
            latitude = form.cleaned_data.get("latitude")
            longitude = form.cleaned_data.get("longitude")
            location_query = form.cleaned_data.get("location_query", "")

        context.update(
            {
                "recommendation_form": form,
                "store_recommendations": recommend_stores(
                    user=(
                        self.request.user
                        if self.request.user.is_authenticated
                        else None
                    ),
                    latitude=latitude,
                    longitude=longitude,
                    location_query=location_query,
                    pickup_time_requested=pickup_time_requested,
                ),
                "regions": Region.objects.prefetch_related("stores").order_by("code"),
                "stores": Store.objects.filter(is_active=True)
                .select_related("region")
                .order_by("name"),
                "mapbox_public_token": settings.MAPBOX_PUBLIC_TOKEN,
                "can_start_order": user_can_use_customer_ordering(self.request.user),
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if getattr(request, "htmx", False):
            return render(
                request, "stores/partials/recommendation_results.html", context
            )
        return self.render_to_response(context)
