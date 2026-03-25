document.addEventListener("DOMContentLoaded", () => {
    document.body.addEventListener("htmx:configRequest", (event) => {
        const csrfInput = document.querySelector("input[name=csrfmiddlewaretoken]");
        if (csrfInput) {
            event.detail.headers["X-CSRFToken"] = csrfInput.value;
        }
    });

    initStoreRecommendation();
    initDrinkBuilder();
    initStripeElementsPanel();
    initPaymentIntentPanel();
});

function getCsrfToken() {
    return document.querySelector("input[name=csrfmiddlewaretoken]")?.value || "";
}

function debounce(callback, wait = 240) {
    let timeoutId;
    return (...args) => {
        window.clearTimeout(timeoutId);
        timeoutId = window.setTimeout(() => callback(...args), wait);
    };
}

function initStoreRecommendation() {
    const recommendationForm = document.querySelector("#store-recommendation-form");
    if (!recommendationForm) {
        return;
    }

    const locateButton = document.querySelector("#geo-locate-btn");
    const latitudeInput = recommendationForm.querySelector("input[name=latitude]");
    const longitudeInput = recommendationForm.querySelector("input[name=longitude]");
    const locationQueryInput = recommendationForm.querySelector("input[name=location_query]");
    const pickupTimeSelect = recommendationForm.querySelector("select[name=pickup_time_choice]");
    const geoStatus = document.querySelector("#geo-status");
    const mapboxToken = recommendationForm.dataset.mapboxToken || "";

    const refreshResults = debounce(() => {
        recommendationForm.requestSubmit();
    }, 180);

    const updateLocationStatus = (message) => {
        if (geoStatus) {
            geoStatus.textContent = message;
        }
    };

    locationQueryInput?.addEventListener("change", () => {
        if (latitudeInput) {
            latitudeInput.value = "";
        }
        if (longitudeInput) {
            longitudeInput.value = "";
        }
        refreshResults();
    });

    pickupTimeSelect?.addEventListener("change", refreshResults);

    if (!locateButton || !latitudeInput || !longitudeInput) {
        return;
    }

    locateButton.addEventListener("click", async () => {
        if (!navigator.geolocation) {
            updateLocationStatus("Location sharing is not available in this browser. Search by ZIP code or address instead.");
            return;
        }

        updateLocationStatus("Finding your location...");

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                latitudeInput.value = position.coords.latitude.toFixed(6);
                longitudeInput.value = position.coords.longitude.toFixed(6);

                if (locationQueryInput && mapboxToken) {
                    const reverseLabel = await reverseGeocode({
                        latitude: latitudeInput.value,
                        longitude: longitudeInput.value,
                        token: mapboxToken,
                    });
                    if (reverseLabel) {
                        locationQueryInput.value = reverseLabel;
                    }
                }

                updateLocationStatus("Location captured. Refreshing recommendations.");
                recommendationForm.requestSubmit();
            },
            () => {
                updateLocationStatus("We couldn't access your location. You can still choose a store manually.");
            },
            { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
        );
    });
}

async function reverseGeocode({ latitude, longitude, token }) {
    if (!latitude || !longitude || !token) {
        return "";
    }

    const url = new URL(
        `https://api.mapbox.com/geocoding/v5/mapbox.places/${longitude},${latitude}.json`
    );
    url.searchParams.set("limit", "1");
    url.searchParams.set("access_token", token);

    try {
        const response = await window.fetch(url.toString(), { method: "GET" });
        if (!response.ok) {
            return "";
        }
        const payload = await response.json();
        return payload.features?.[0]?.place_name || "";
    } catch (error) {
        return "";
    }
}

function initDrinkBuilder() {
    const builderForm = document.querySelector("#drink-builder-form");
    if (!builderForm) {
        return;
    }

    const cupLiquid = builderForm.querySelector(".cup-preview__liquid");
    const cupFoam = builderForm.querySelector(".cup-preview__foam");
    const builderHeading = document.querySelector("[data-builder-heading]");
    const builderSummary = document.querySelector("[data-builder-summary]");
    const builderChips = document.querySelector("[data-builder-chips]");
    const builderCupLabel = document.querySelector("[data-builder-cup-label]");
    const builderTotal = document.querySelector("[data-builder-total]");
    const builderQuantity = document.querySelector("[data-builder-quantity]");
    const builderStyle = document.querySelector("[data-builder-style]");
    const assistantPanel = document.querySelector("#builder-assistant");
    const assistantUrl = builderForm.dataset.builderAssistantUrl;
    const aiFillUrl = builderForm.dataset.builderAiFillUrl;
    const menuName = builderForm.dataset.builderMenuName || "Custom drink";
    const notesField = builderForm.querySelector("textarea[name=notes]");
    const quantityField = builderForm.querySelector("input[name=quantity]");
    const pricingData = readJsonScript("builder-pricing-data");

    const ingredientSummary = () => {
        const syrupLabels = getCheckedLabels(builderForm, "syrups");
        const addInLabels = getCheckedLabels(builderForm, "add_ins");
        const iceCreamLabel = getSelectedLabel(builderForm, "ice_cream");
        const chips = [];
        const sodaLabel = getSelectedLabel(builderForm, "soda");
        const sizeLabel = getSelectedLabel(builderForm, "size");
        if (sizeLabel) {
            chips.push(sizeLabel);
        }
        if (sodaLabel) {
            chips.push(sodaLabel);
        }
        if (iceCreamLabel && iceCreamLabel !== "No ice cream") {
            chips.push(`${iceCreamLabel} float`);
        }
        return chips.concat(syrupLabels, addInLabels);
    };

    const buildPreviewHeadline = ({ sodaLabel, syrupLabels, addInLabels, iceCreamLabel }) => {
        if (!sodaLabel) {
            return menuName;
        }
        if (iceCreamLabel && iceCreamLabel !== "No ice cream") {
            return `${sodaLabel} + ${iceCreamLabel} float`;
        }
        const flavorLabel = syrupLabels[0] || addInLabels[0];
        if (flavorLabel) {
            return `${sodaLabel} + ${flavorLabel}`;
        }
        return sodaLabel;
    };

    const buildDisplayChips = (chips) => {
        const limited = chips.slice(0, 5);
        if (chips.length > 5) {
            limited.push(`+${chips.length - 5} more`);
        }
        return limited;
    };

    const renderSelectedCards = () => {
        builderForm.querySelectorAll(".choice-card").forEach((card) => {
            const input = card.querySelector("input");
            if (!input) {
                return;
            }
            card.classList.toggle("is-selected", input.checked);
        });
    };

    const calculateTotal = () => {
        if (!pricingData) {
            return 0;
        }
        const size = getSelectedValue(builderForm, "size") || "medium";
        const syrups = getCheckedValues(builderForm, "syrups");
        const addIns = getCheckedValues(builderForm, "add_ins");
        const iceCream = getSelectedValue(builderForm, "ice_cream");
        const quantity = Number(quantityField?.value || 1);
        const basePrice = Number(pricingData.base_prices?.[size] || 0);
        const syrupTotal = syrups.reduce(
            (sum, token) => sum + Number(pricingData.syrups?.[token] || 0),
            0
        );
        const addInTotal = addIns.reduce(
            (sum, token) => sum + Number(pricingData.add_ins?.[token] || 0),
            0
        );
        const iceCreamTotal = Number(pricingData.ice_cream?.[iceCream] || 0);
        return (basePrice + syrupTotal + addInTotal + iceCreamTotal) * Math.max(quantity, 1);
    };

    const renderPreview = () => {
        const chips = ingredientSummary();
        const syrupLabels = getCheckedLabels(builderForm, "syrups");
        const addInLabels = getCheckedLabels(builderForm, "add_ins");
        const iceCreamValue = getSelectedValue(builderForm, "ice_cream");
        const iceCreamLabel = getSelectedLabel(builderForm, "ice_cream");
        const hasFloat = Boolean(iceCreamValue);
        const hasFresh = addInLabels.some(
            (label) => label.toLowerCase().includes("lime") || label.toLowerCase().includes("mint")
        );
        const sodaValue = getSelectedValue(builderForm, "soda") || "lemon-lime";
        const sodaLabel = getSelectedLabel(builderForm, "soda");
        const quantity = quantityField?.value || "1";
        const total = calculateTotal();

        if (cupLiquid) {
            cupLiquid.dataset.soda = resolveCupTone(sodaValue);
            cupLiquid.style.transform = syrupLabels.length > 1 ? "scaleY(1.02)" : "scaleY(1)";
        }
        if (cupFoam) {
            cupFoam.dataset.hasFloat = hasFloat ? "1" : "0";
        }
        if (builderHeading) {
            builderHeading.textContent = buildPreviewHeadline({
                sodaLabel,
                syrupLabels,
                addInLabels,
                iceCreamLabel,
            });
        }
        if (builderCupLabel) {
            builderCupLabel.textContent = hasFloat ? `${menuName} Float` : menuName;
        }
        if (builderSummary) {
            const notes = notesField?.value?.trim();
            if (notes) {
                builderSummary.textContent = notes;
            } else if (hasFloat && iceCreamValue) {
                builderSummary.textContent = "This build is leaning creamy and float-forward while still staying fully editable.";
            } else if (hasFloat) {
                builderSummary.textContent = "A creamy topper is on deck, so the build leans dessert-forward and pickup-friendly.";
            } else if (hasFresh) {
                builderSummary.textContent = "Fresh finishing notes keep the drink brighter and more refreshing.";
            } else if (syrupLabels.length) {
                builderSummary.textContent = "This build is leaning flavor-forward while staying balanced enough for an easy pickup.";
            } else {
                builderSummary.textContent = "Choose a base, layer in flavor, and let FloatStack AI smooth out the balance.";
            }
        }
        if (builderChips) {
            builderChips.innerHTML = buildDisplayChips(chips)
                .map((chip) => `<span class="pill pill--soft">${chip}</span>`)
                .join("");
        }
        if (builderTotal) {
            builderTotal.textContent = formatCurrency(total);
        }
        if (builderQuantity) {
            builderQuantity.textContent = quantity;
        }
        if (builderStyle) {
            builderStyle.textContent = summarizeStyle({ hasFloat, hasFresh, syrupCount: syrupLabels.length, sodaValue });
        }
        renderSelectedCards();
    };

    const refreshAssistant = debounce(async () => {
        if (!assistantUrl || !assistantPanel) {
            return;
        }

        const formData = new FormData(builderForm);
        assistantPanel.setAttribute("aria-busy", "true");

        try {
            const response = await window.fetch(assistantUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCsrfToken(),
                    "HX-Request": "true",
                },
                body: formData,
            });
            if (!response.ok) {
                throw new Error("Assistant request failed.");
            }
            assistantPanel.innerHTML = await response.text();
        } catch (error) {
            assistantPanel.innerHTML = `
                <div class="assistant-card">
                    <p class="eyebrow">FloatStack Assist</p>
                    <h2>Build guidance is temporarily offline</h2>
                    <p>Keep customizing your drink. The builder preview is still live, and server-side validation will still protect pricing and recipe rules.</p>
                </div>
            `;
        } finally {
            assistantPanel.removeAttribute("aria-busy");
        }
    }, 220);

    const applyAiFill = async () => {
        if (!aiFillUrl || !assistantPanel) {
            return;
        }

        const trigger = assistantPanel.querySelector("[data-builder-ai-trigger]");
        if (trigger) {
            trigger.disabled = true;
            trigger.textContent = "Building...";
        }
        assistantPanel.setAttribute("aria-busy", "true");

        try {
            const response = await window.fetch(aiFillUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCsrfToken(),
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
                body: new URLSearchParams(new FormData(builderForm)).toString(),
            });
            if (!response.ok) {
                throw new Error("AI fill request failed.");
            }
            const payload = await response.json();
            syncBuilderSelection(builderForm, payload.selection || {});
            if (assistantPanel && payload.assistant_html) {
                assistantPanel.innerHTML = payload.assistant_html;
            }
            renderPreview();
        } catch (error) {
            if (assistantPanel) {
                assistantPanel.innerHTML = `
                    <div class="assistant-card">
                        <p class="eyebrow">FloatStack AI</p>
                        <h2>AI fill is temporarily unavailable</h2>
                        <p>The builder is still live, and your current selections remain editable.</p>
                    </div>
                `;
            }
        } finally {
            assistantPanel.removeAttribute("aria-busy");
        }
    };

    builderForm.addEventListener("change", () => {
        renderPreview();
        refreshAssistant();
    });

    builderForm.addEventListener("input", () => {
        renderPreview();
        refreshAssistant();
    });

    assistantPanel?.addEventListener("click", (event) => {
        const trigger = event.target.closest("[data-builder-ai-trigger]");
        if (!trigger) {
            return;
        }
        event.preventDefault();
        applyAiFill();
    });

    renderPreview();
    refreshAssistant();
}

function initPaymentIntentPanel() {
    const panel = document.querySelector("#payment-intent-panel");
    const button = document.querySelector("#payment-intent-btn");
    const status = document.querySelector("#payment-intent-status");
    if (!panel || !button || !status) {
        return;
    }

    button.addEventListener("click", async () => {
        const endpoint = panel.dataset.endpoint;
        const orderCode = panel.dataset.orderCode;
        if (!endpoint || !orderCode) {
            status.textContent = "Payment intent endpoint metadata is missing.";
            return;
        }

        button.disabled = true;
        status.textContent = "Creating payment intent...";
        const body = new URLSearchParams({ order_code: orderCode });

        try {
            const response = await window.fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "X-CSRFToken": getCsrfToken(),
                },
                body: body.toString(),
            });
            const payload = await response.json();
            if (!response.ok) {
                status.textContent = payload.error || "Unable to create payment intent.";
                button.disabled = false;
                return;
            }

            status.textContent = `Payment intent ready via ${payload.provider}. Continue checkout in the payment flow.`;
            button.textContent = "Payment intent created";
        } catch (error) {
            status.textContent = "Failed to create payment intent. Try again.";
            button.disabled = false;
        }
    });
}

function initStripeElementsPanel() {
    const panel = document.querySelector("#stripe-elements-panel");
    const button = document.querySelector("#stripe-pay-btn");
    const status = document.querySelector("#stripe-pay-status");
    const cardElementContainer = document.querySelector("#card-element");
    if (!panel || !button || !status || !cardElementContainer) {
        return;
    }
    if (!window.Stripe) {
        status.textContent = "Stripe.js failed to load. Refresh the page and try again.";
        return;
    }

    const publishableKey = panel.dataset.publishableKey || "";
    const endpoint = panel.dataset.endpoint;
    const statusEndpoint = panel.dataset.statusEndpoint;
    const orderCode = panel.dataset.orderCode;
    if (!publishableKey || !endpoint || !statusEndpoint || !orderCode) {
        status.textContent = "Stripe configuration is incomplete for this environment.";
        return;
    }

    const stripe = window.Stripe(publishableKey);
    const elements = stripe.elements();
    const card = elements.create("card", {
        hidePostalCode: true,
    });
    card.mount("#card-element");

    const pollFinalStatus = async () => {
        for (let attempt = 0; attempt < 12; attempt += 1) {
            try {
                const url = new URL(statusEndpoint, window.location.origin);
                url.searchParams.set("order_code", orderCode);
                const response = await window.fetch(url.toString(), {
                    method: "GET",
                    headers: {
                        "X-CSRFToken": getCsrfToken(),
                    },
                });
                const payload = await response.json();
                if (response.ok && payload.finalized && payload.redirect_url) {
                    window.location.assign(payload.redirect_url);
                    return true;
                }
                if (payload.payment_status === "failed") {
                    status.textContent = "Payment failed during finalization. Please try again.";
                    return false;
                }
            } catch (error) {
                // Continue polling for transient errors.
            }
            await new Promise((resolve) => window.setTimeout(resolve, 1500));
        }
        status.textContent = "Payment submitted, but final confirmation is still processing. Refresh this page in a moment.";
        return false;
    };

    button.addEventListener("click", async () => {
        button.disabled = true;
        status.textContent = "Preparing secure payment...";

        let payload;
        try {
            const response = await window.fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "X-CSRFToken": getCsrfToken(),
                },
                body: new URLSearchParams({ order_code: orderCode }).toString(),
            });
            payload = await response.json();
            if (!response.ok) {
                status.textContent = payload.error || "Unable to create payment intent.";
                button.disabled = false;
                return;
            }
        } catch (error) {
            status.textContent = "Unable to start payment right now. Try again.";
            button.disabled = false;
            return;
        }

        status.textContent = "Confirming card details...";
        const result = await stripe.confirmCardPayment(payload.client_secret, {
            payment_method: { card },
        });

        if (result.error) {
            status.textContent = result.error.message || "Payment failed. Please try another card.";
            button.disabled = false;
            return;
        }

        status.textContent = "Payment submitted. Finalizing order...";
        const finalized = await pollFinalStatus();
        if (!finalized) {
            button.disabled = false;
        }
    });
}

function getCheckedLabels(form, fieldName) {
    return Array.from(form.querySelectorAll(`input[name="${fieldName}"]:checked`))
        .map(
            (input) =>
                input.closest("label")?.querySelector(".choice-card__label")?.textContent?.trim() ||
                input.closest("label")?.textContent?.trim() ||
                ""
        )
        .filter(Boolean);
}

function getCheckedValues(form, fieldName) {
    return Array.from(form.querySelectorAll(`input[name="${fieldName}"]:checked`)).map(
        (input) => input.value
    );
}

function getSelectedValue(form, fieldName) {
    const radio = form.querySelector(`input[name="${fieldName}"]:checked`);
    if (radio) {
        return radio.value;
    }
    const input = form.querySelector(`[name="${fieldName}"]`);
    if (!input) {
        return "";
    }
    if (input.tagName === "SELECT") {
        return input.value;
    }
    return input.value || "";
}

function getSelectedLabel(form, fieldName) {
    const checkedInput = form.querySelector(`input[name="${fieldName}"]:checked`);
    if (checkedInput) {
        return (
            checkedInput.closest("label")?.querySelector(".choice-card__label")?.textContent?.trim() ||
            checkedInput.closest("label")?.textContent?.trim() ||
            ""
        );
    }
    const select = form.querySelector(`select[name="${fieldName}"]`);
    return select?.selectedOptions?.[0]?.textContent?.trim() || "";
}

function readJsonScript(scriptId) {
    const node = document.getElementById(scriptId);
    if (!node) {
        return null;
    }
    try {
        return JSON.parse(node.textContent);
    } catch (error) {
        return null;
    }
}

function formatCurrency(value) {
    return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
    }).format(value || 0);
}

function resolveCupTone(sodaValue) {
    if (!sodaValue) {
        return "berry";
    }
    if (["coke", "diet-coke", "coke-zero", "dr-pepper", "diet-dr-pepper", "pepsi", "diet-pepsi"].includes(sodaValue)) {
        return "cola";
    }
    if (["sprite", "sprite-zero", "lemon-lime", "club-soda"].includes(sodaValue)) {
        return "citrus";
    }
    if (["root-beer"].includes(sodaValue)) {
        return "root";
    }
    if (["cream-soda"].includes(sodaValue)) {
        return "cream";
    }
    if (["orange-soda", "mountain-dew", "diet-mountain-dew"].includes(sodaValue)) {
        return "sun";
    }
    return "berry";
}

function summarizeStyle({ hasFloat, hasFresh, syrupCount, sodaValue }) {
    if (hasFloat) {
        return "Creamy float";
    }
    if (hasFresh) {
        return "Bright + fresh";
    }
    if (["coke", "diet-coke", "coke-zero", "dr-pepper", "diet-dr-pepper", "pepsi", "diet-pepsi"].includes(sodaValue)) {
        return "Classic soda shop";
    }
    if (syrupCount >= 2) {
        return "Flavor layered";
    }
    return "Balanced build";
}

function syncBuilderSelection(form, selection) {
    if (selection.size) {
        const input = form.querySelector(`input[name="size"][value="${selection.size}"]`);
        if (input) {
            input.checked = true;
        }
    }
    if (selection.soda) {
        const input = form.querySelector(`input[name="soda"][value="${selection.soda}"]`);
        if (input) {
            input.checked = true;
        }
    }

    syncCheckboxGroup(form, "syrups", selection.syrups || []);
    syncCheckboxGroup(form, "add_ins", selection.add_ins || []);

    const iceCreamInputs = form.querySelectorAll('input[name="ice_cream"]');
    iceCreamInputs.forEach((input) => {
        input.checked = input.value === (selection.ice_cream || "");
    });
}

function syncCheckboxGroup(form, fieldName, selectedValues) {
    const selected = new Set(selectedValues);
    form.querySelectorAll(`input[name="${fieldName}"]`).forEach((input) => {
        input.checked = selected.has(input.value);
    });
}
