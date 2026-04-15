document.addEventListener("DOMContentLoaded", () => {
    document.body.addEventListener("htmx:configRequest", (event) => {
        const csrfInput = document.querySelector("input[name=csrfmiddlewaretoken]");
        if (csrfInput) {
            event.detail.headers["X-CSRFToken"] = csrfInput.value;
        }
    });

    initStoreRecommendation();
    initCheckoutGuestValidation();
    initDrinkBuilder();
    initPreferenceProfile();
    initMenuAiAssistant();
    initQueueRowNavigation();
    initHomeHeroCarousel();
    initHomeDrinkBrowser();
    initPickupDistance();
    initSupportChat();
    initPreferenceSelection();
    initRegistrationPasswordGates();
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

function initCheckoutGuestValidation() {
    const checkoutForm = document.querySelector(
        "#checkout-form[data-checkout-guest-validation='true']"
    );
    if (!checkoutForm) {
        return;
    }

    const guestNameInput = checkoutForm.querySelector("input[name=guest_name]");
    const guestEmailInput = checkoutForm.querySelector("input[name=guest_email]");
    const guestPhoneInput = checkoutForm.querySelector("input[name=guest_phone_number]");

    const validators = [
        {
            input: guestNameInput,
            validate: (value) =>
                value.trim().length > 0 ? "" : "Name is required.",
        },
        {
            input: guestEmailInput,
            validate: (value) => {
                if (!value.trim()) {
                    return "Enter a valid email address.";
                }
                const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                return emailPattern.test(value.trim())
                    ? ""
                    : "Enter a valid email address.";
            },
        },
        {
            input: guestPhoneInput,
            validate: (value) => {
                if (!value.trim()) {
                    return "";
                }
                const digitsOnly = value.replace(/\D/g, "");
                return digitsOnly.length === 10
                    ? ""
                    : "Enter a valid 10-digit phone number.";
            },
        },
    ];

    const setFieldState = (input, errorMessage) => {
        if (!input) {
            return;
        }
        const field = input.closest(".field");
        const errorElement = field?.querySelector(
            `[data-checkout-error-for='${input.name}']`
        );
        const isValid = !errorMessage;

        if (field) {
            field.classList.toggle("field--invalid", !isValid);
        }
        input.setAttribute("aria-invalid", isValid ? "false" : "true");
        input.setCustomValidity(errorMessage);

        if (errorElement) {
            errorElement.textContent = errorMessage;
            errorElement.hidden = isValid;
        }
    };

    const validateInput = ({ input, validate }) => {
        if (!input) {
            return true;
        }
        const errorMessage = validate(input.value);
        setFieldState(input, errorMessage);
        return !errorMessage;
    };

    validators.forEach((validator) => {
        if (!validator.input) {
            return;
        }

        validator.input.addEventListener("blur", () => {
            validator.input.dataset.touched = "true";
            validateInput(validator);
        });

        validator.input.addEventListener("input", () => {
            if (validator.input.dataset.touched === "true") {
                validateInput(validator);
            }
        });
    });
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

function initMenuAiAssistant() {
    const openButton = document.querySelector("#menu-ai-open");
    const closeButton = document.querySelector("#menu-ai-close");
    const panel = document.querySelector("#menu-ai-panel");
    const promptField = document.querySelector("#menu-ai-prompt");

    const openPanel = () => {
        if (!panel) {
            return;
        }
        panel.hidden = false;
        promptField?.focus();
    };

    const closePanel = () => {
        if (!panel) {
            return;
        }
        panel.hidden = true;
    };

    openButton?.addEventListener("click", openPanel);
    closeButton?.addEventListener("click", closePanel);

    document.body.addEventListener("click", (event) => {
        const target = event.target.closest("[data-menu-ai-prompt]");
        if (!target || !promptField || !panel) {
            return;
        }
        openPanel();
        promptField.value = target.getAttribute("data-menu-ai-prompt") || "";
    });
}

function initQueueRowNavigation() {
    document.body.addEventListener("click", (event) => {
        if (
            event.defaultPrevented ||
            event.button !== 0 ||
            event.metaKey ||
            event.ctrlKey ||
            event.shiftKey ||
            event.altKey
        ) {
            return;
        }

        const target = event.target instanceof Element ? event.target : null;
        if (!target) {
            return;
        }

        const row = target.closest("tr.queue-row[data-order-detail-url]");
        if (!row) {
            return;
        }

        if (target.closest("a, button, input, select, textarea, label, form")) {
            return;
        }

        if (target.closest(".queue-actions-cell")) {
            return;
        }

        const detailUrl = row.getAttribute("data-order-detail-url");
        if (detailUrl) {
            window.location.assign(detailUrl);
        }
    });
}

function initHomeHeroCarousel() {
    const carousel = document.querySelector("[data-home-carousel]");
    if (!carousel) {
        return;
    }

    const slides = Array.from(carousel.querySelectorAll("[data-home-slide]"));
    if (!slides.length) {
        return;
    }

    const previousButton = carousel.querySelector("[data-home-carousel-prev]");
    const nextButton = carousel.querySelector("[data-home-carousel-next]");
    const dots = Array.from(carousel.querySelectorAll("[data-home-carousel-dot]"));
    const autoAdvanceMs = 5200;
    carousel.classList.toggle("is-single-slide", slides.length < 2);
    let activeIndex = Math.max(
        0,
        slides.findIndex((slide) => slide.classList.contains("is-active"))
    );
    let autoAdvanceId = null;

    const applyState = (targetIndex) => {
        const safeIndex = ((targetIndex % slides.length) + slides.length) % slides.length;
        activeIndex = safeIndex;

        slides.forEach((slide, index) => {
            const isActive = index === safeIndex;
            slide.classList.toggle("is-active", isActive);
            slide.setAttribute("aria-hidden", isActive ? "false" : "true");
            slide.setAttribute("tabindex", isActive ? "0" : "-1");
        });

        dots.forEach((dot, index) => {
            const isActive = index === safeIndex;
            dot.classList.toggle("is-active", isActive);
            dot.setAttribute("aria-selected", isActive ? "true" : "false");
            dot.setAttribute("tabindex", isActive ? "0" : "-1");
        });
    };

    const goTo = (targetIndex) => {
        applyState(targetIndex);
    };

    const advance = (step) => {
        goTo(activeIndex + step);
    };

    const stopAutoAdvance = () => {
        if (autoAdvanceId !== null) {
            window.clearInterval(autoAdvanceId);
            autoAdvanceId = null;
        }
    };

    const startAutoAdvance = () => {
        if (slides.length < 2 || autoAdvanceId !== null) {
            return;
        }
        autoAdvanceId = window.setInterval(() => {
            if (!document.hidden) {
                advance(1);
            }
        }, autoAdvanceMs);
    };

    const resetAutoAdvance = () => {
        stopAutoAdvance();
        startAutoAdvance();
    };

    previousButton?.addEventListener("click", () => {
        advance(-1);
        resetAutoAdvance();
    });

    nextButton?.addEventListener("click", () => {
        advance(1);
        resetAutoAdvance();
    });

    dots.forEach((dot) => {
        dot.addEventListener("click", () => {
            const dotIndex = Number.parseInt(dot.dataset.homeCarouselDot || "0", 10);
            goTo(Number.isNaN(dotIndex) ? 0 : dotIndex);
            resetAutoAdvance();
        });
    });

    carousel.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") {
            event.preventDefault();
            advance(-1);
            resetAutoAdvance();
            return;
        }
        if (event.key === "ArrowRight") {
            event.preventDefault();
            advance(1);
            resetAutoAdvance();
            return;
        }
        if (event.key === "Home") {
            event.preventDefault();
            goTo(0);
            resetAutoAdvance();
            return;
        }
        if (event.key === "End") {
            event.preventDefault();
            goTo(slides.length - 1);
            resetAutoAdvance();
        }
    });

    carousel.addEventListener("mouseenter", stopAutoAdvance);
    carousel.addEventListener("mouseleave", startAutoAdvance);
    carousel.addEventListener("focusin", stopAutoAdvance);
    carousel.addEventListener("focusout", (event) => {
        if (!carousel.contains(event.relatedTarget)) {
            startAutoAdvance();
        }
    });
    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            stopAutoAdvance();
            return;
        }
        startAutoAdvance();
    });

    applyState(activeIndex);
    startAutoAdvance();
}

function initHomeDrinkBrowser() {
    const navLinks = Array.from(
        document.querySelectorAll("[data-home-nav-link]")
    );
    const basePreviews = Array.from(
        document.querySelectorAll("[data-home-soda-base]")
    );

    basePreviews.forEach((preview) => {
        preview.dataset.soda = resolveCupTone(preview.dataset.homeSodaBase || "");
    });

    if (!navLinks.length) {
        return;
    }

    const navTargets = navLinks
        .map((link) => {
            const hash = link.getAttribute("href") || "";
            if (!hash.startsWith("#")) {
                return null;
            }
            const section = document.getElementById(hash.slice(1));
            if (!section) {
                return null;
            }
            return { hash, section };
        })
        .filter(Boolean);

    if (!navTargets.length) {
        return;
    }

    const setActiveLink = (targetHash) => {
        let foundMatch = false;
        navLinks.forEach((link) => {
            const isActive = link.getAttribute("href") === targetHash;
            link.classList.toggle("is-active", isActive);
            link.setAttribute("aria-current", isActive ? "true" : "false");
            if (isActive) {
                foundMatch = true;
            }
        });
        if (!foundMatch && navLinks[0]) {
            navLinks[0].classList.add("is-active");
            navLinks[0].setAttribute("aria-current", "true");
            navLinks.slice(1).forEach((link) => {
                link.classList.remove("is-active");
                link.setAttribute("aria-current", "false");
            });
        }
    };

    const scrollToHash = (hash) => {
        const section = document.getElementById(hash.replace("#", ""));
        if (!section) {
            return;
        }
        const topbar = document.querySelector(".topbar");
        const subnavPanel = document.querySelector(".home-subnav-panel");
        const topbarHeight = topbar ? topbar.getBoundingClientRect().height : 0;
        const subnavStyles = subnavPanel ? window.getComputedStyle(subnavPanel) : null;
        const subnavIsSticky = subnavPanel && subnavStyles?.position === "sticky";
        const subnavHeight = subnavIsSticky ? subnavPanel.getBoundingClientRect().height : 0;
        const offset = topbarHeight + subnavHeight + 18;
        const top = section.getBoundingClientRect().top + window.scrollY - offset;
        window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
    };

    navLinks.forEach((link) => {
        link.addEventListener("click", (event) => {
            const hash = link.getAttribute("href") || "";
            if (!hash.startsWith("#")) {
                return;
            }
            const section = document.getElementById(hash.slice(1));
            if (!section) {
                return;
            }
            event.preventDefault();
            setActiveLink(hash);
            if (window.location.hash !== hash) {
                window.history.replaceState(null, "", hash);
            }
            scrollToHash(hash);
        });
    });

    if ("IntersectionObserver" in window) {
        const activeEntries = new Map();
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    const hash = `#${entry.target.id}`;
                    if (entry.isIntersecting) {
                        activeEntries.set(hash, entry.intersectionRatio);
                    } else {
                        activeEntries.delete(hash);
                    }
                });

                if (!activeEntries.size) {
                    return;
                }

                const [bestHash] = Array.from(activeEntries.entries()).sort(
                    (a, b) => b[1] - a[1]
                )[0];
                if (bestHash) {
                    setActiveLink(bestHash);
                }
            },
            {
                threshold: [0.12, 0.35, 0.55, 0.75],
                rootMargin: "-28% 0px -52% 0px",
            }
        );

        navTargets.forEach(({ section }) => {
            observer.observe(section);
        });
    } else {
        const updateActiveFromScroll = debounce(() => {
            const currentY = window.scrollY + 190;
            let activeHash = navTargets[0]?.hash || "";
            navTargets.forEach(({ hash, section }) => {
                if (currentY >= section.offsetTop) {
                    activeHash = hash;
                }
            });
            setActiveLink(activeHash);
        }, 80);
        window.addEventListener("scroll", updateActiveFromScroll, { passive: true });
    }

    const knownHashes = new Set(navTargets.map(({ hash }) => hash));
    const initialHash = knownHashes.has(window.location.hash)
        ? window.location.hash
        : navTargets[0]?.hash || "";
    if (initialHash) {
        setActiveLink(initialHash);
    }
    window.addEventListener("hashchange", () => {
        const hash = window.location.hash;
        if (knownHashes.has(hash)) {
            setActiveLink(hash);
        }
    });
}

function initPickupDistance() {
    const distanceNode = document.querySelector("[data-pickup-distance]");
    const enableButton = document.querySelector("[data-pickup-distance-enable]");
    if (!distanceNode) {
        return;
    }

    const setDistanceMessage = (message) => {
        distanceNode.textContent = message;
    };

    const setEnableButtonVisible = (visible) => {
        if (!enableButton) {
            return;
        }
        enableButton.hidden = !visible;
    };

    const setEnableButtonLoading = (loading) => {
        if (!enableButton) {
            return;
        }
        enableButton.disabled = loading;
        enableButton.textContent = loading ? "Locating..." : "Use my location";
    };

    const storeLatitude = Number(distanceNode.dataset.storeLatitude || "");
    const storeLongitude = Number(distanceNode.dataset.storeLongitude || "");
    if (!Number.isFinite(storeLatitude) || !Number.isFinite(storeLongitude)) {
        setDistanceMessage("Distance is unavailable for this store.");
        setEnableButtonVisible(false);
        return;
    }

    if (!navigator.geolocation) {
        setDistanceMessage("Location is unavailable in this browser.");
        setEnableButtonVisible(false);
        return;
    }

    const haversineMiles = (fromLat, fromLng, toLat, toLng) => {
        const toRadians = (value) => (value * Math.PI) / 180;
        const earthRadiusMiles = 3958.8;
        const latDelta = toRadians(toLat - fromLat);
        const lngDelta = toRadians(toLng - fromLng);
        const a =
            Math.sin(latDelta / 2) * Math.sin(latDelta / 2) +
            Math.cos(toRadians(fromLat)) *
                Math.cos(toRadians(toLat)) *
                Math.sin(lngDelta / 2) *
                Math.sin(lngDelta / 2);
        return earthRadiusMiles * 2 * Math.asin(Math.sqrt(a));
    };

    const estimateDriveMinutes = (distanceMiles) => {
        if (distanceMiles <= 1.5) {
            return Math.max(4, Math.round(distanceMiles * 5));
        }
        if (distanceMiles <= 8) {
            return Math.max(8, Math.round((distanceMiles / 24) * 60));
        }
        return Math.max(14, Math.round((distanceMiles / 34) * 60));
    };

    const readPermissionState = async () => {
        try {
            if (!navigator.permissions?.query) {
                return "";
            }
            const result = await navigator.permissions.query({ name: "geolocation" });
            return String(result.state || "");
        } catch (error) {
            return "";
        }
    };

    const requestDistance = async () => {
        setEnableButtonLoading(true);
        setDistanceMessage("Requesting location permission…");

        const permissionState = await readPermissionState();
        if (permissionState === "denied") {
            setDistanceMessage(
                "Location is blocked in browser settings. Enable Location for this site, then tap Use my location again."
            );
            setEnableButtonVisible(true);
            setEnableButtonLoading(false);
            return;
        }

        try {
            setDistanceMessage("Calculating your distance…");
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const miles = haversineMiles(
                        position.coords.latitude,
                        position.coords.longitude,
                        storeLatitude,
                        storeLongitude
                    );
                    const roundedMiles =
                        miles >= 10
                            ? miles.toFixed(0)
                            : miles >= 1
                            ? miles.toFixed(1)
                            : miles.toFixed(2);
                    const driveMinutes = estimateDriveMinutes(miles);
                    setDistanceMessage(
                        `You are ${roundedMiles} miles away (~${driveMinutes} min drive).`
                    );
                    setEnableButtonVisible(false);
                    setEnableButtonLoading(false);
                },
                (error) => {
                    const denied = Number(error?.code) === 1;
                    if (denied) {
                        setDistanceMessage(
                            "Location is off or blocked. Allow location for this site, then tap Use my location."
                        );
                    } else {
                        setDistanceMessage(
                            "We couldn't get your location. Tap Use my location to try again."
                        );
                    }
                    setEnableButtonVisible(true);
                    setEnableButtonLoading(false);
                },
                { enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 }
            );
        } catch (error) {
            setDistanceMessage(
                "Location access is unavailable right now. Check browser settings and try again."
            );
            setEnableButtonVisible(true);
            setEnableButtonLoading(false);
        }
    };

    enableButton?.addEventListener("click", () => {
        void requestDistance();
    });
    void requestDistance();
}

function initPreferenceProfile() {
    const preferencesForm = document.querySelector(".preferences-form");
    if (!preferencesForm) {
        return;
    }

    const syncSelectionState = () => {
        preferencesForm.querySelectorAll(".choice-card").forEach((card) => {
            const input = card.querySelector("input[type='checkbox'], input[type='radio']");
            if (!input) {
                return;
            }
            card.classList.toggle("is-selected", input.checked);
        });
    };

    preferencesForm.addEventListener("change", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLInputElement)) {
            return;
        }
        if (target.type !== "checkbox" && target.type !== "radio") {
            return;
        }
        syncSelectionState();
    });

    syncSelectionState();
}

function initSupportChat() {
    const workspace = document.querySelector("#support-workspace");
    if (!workspace) {
        return;
    }

    let preservedScrollY = null;

    const scrollThreadToBottom = () => {
        const thread = document.querySelector("#support-thread-log");
        if (thread) {
            thread.scrollTop = thread.scrollHeight;
        }
    };

    scrollThreadToBottom();

    document.body.addEventListener("htmx:beforeRequest", (event) => {
        const form = event.target.closest("form[data-support-send-form]");
        if (!form) {
            return;
        }
        preservedScrollY = window.scrollY;
        const status = form.querySelector("[data-support-send-status]");
        if (status) {
            status.hidden = false;
        }
        const submitButton = form.querySelector("button[type='submit']");
        if (submitButton) {
            submitButton.disabled = true;
            if (!submitButton.dataset.originalLabel) {
                submitButton.dataset.originalLabel = submitButton.textContent;
            }
            submitButton.textContent = "Creating message...";
        }
    });

    document.body.addEventListener("htmx:afterSwap", (event) => {
        const target = event.detail?.target;
        if (!target || target.id !== "support-workspace") {
            return;
        }
        if (typeof preservedScrollY === "number") {
            window.scrollTo({ top: preservedScrollY, behavior: "auto" });
        }
        preservedScrollY = null;
        scrollThreadToBottom();
    });
}

function initPreferenceSelection() {
    const form = document.querySelector(".preferences-form");
    if (!form) {
        return;
    }

    const syncInputGroup = (name) => {
        if (!name) {
            return;
        }
        form.querySelectorAll(`.choice-card input[name="${name}"]`).forEach((input) => {
            const card = input.closest(".choice-card");
            if (card) {
                card.classList.toggle("is-selected", input.checked);
            }
        });
    };

    form.querySelectorAll(".choice-card input").forEach((input) => {
        syncInputGroup(input.name);
    });

    form.addEventListener("change", (event) => {
        const input = event.target.closest(".choice-card input");
        if (!input) {
            return;
        }

        const token = input.dataset.token || "";
        const role = input.dataset.prefRole || "";
        if (input.checked && token && role) {
            form.querySelectorAll(".choice-card input[data-token]").forEach((peer) => {
                if (peer === input) {
                    return;
                }
                if (
                    (peer.dataset.token || "") === token &&
                    (peer.dataset.prefRole || "") &&
                    peer.dataset.prefRole !== role
                ) {
                    peer.checked = false;
                    syncInputGroup(peer.name);
                }
            });
        }
        syncInputGroup(input.name);
    });
}

function initRegistrationPasswordGates() {
    const form = document.querySelector(".auth-form");
    if (!form) {
        return;
    }

    const passwordField = form.querySelector("input[name=password1]");
    const confirmField = form.querySelector("input[name=password2]");
    const gates = document.querySelector("#password-gates");
    if (!passwordField || !confirmField || !gates) {
        return;
    }

    const gateNodes = {
        length: gates.querySelector("[data-password-gate=length]"),
        alnum: gates.querySelector("[data-password-gate=alnum]"),
        match: gates.querySelector("[data-password-gate=match]"),
    };

    const setGateState = (node, isComplete, label) => {
        if (!node) {
            return;
        }
        node.textContent = `${isComplete ? "[x]" : "[ ]"} ${label}`;
    };

    const renderGates = () => {
        const passwordValue = passwordField.value || "";
        const confirmValue = confirmField.value || "";
        const hasLength = passwordValue.length >= 8;
        const hasLetterAndNumber = /[A-Za-z]/.test(passwordValue) && /\d/.test(passwordValue);
        const isMatch = Boolean(passwordValue) && passwordValue === confirmValue;

        setGateState(gateNodes.length, hasLength, "At least 8 characters");
        setGateState(
            gateNodes.alnum,
            hasLetterAndNumber,
            "Includes at least one letter and one number"
        );
        setGateState(
            gateNodes.match,
            isMatch,
            "Password and re-entered password match"
        );
    };

    passwordField.addEventListener("input", renderGates);
    confirmField.addEventListener("input", renderGates);
    renderGates();
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
