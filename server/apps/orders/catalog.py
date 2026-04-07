from copy import deepcopy
from decimal import Decimal

SIZE_LABELS = {
    "small": "Small",
    "medium": "Medium",
    "large": "Large",
}


def _option(
    label,
    *,
    inventory_sku="",
    price="0.00",
    tags=None,
    description="",
    inventory_name=None,
    inventory_category="other",
    unit_of_measure="unit",
    threshold="8.00",
    is_perishable=False,
    requires_frozen_storage=False,
    inventory_quantity="0.35",
    inventory_quantity_by_size=None,
):
    return {
        "label": label,
        "inventory_sku": inventory_sku,
        "price": Decimal(str(price)),
        "tags": tuple(tags or ()),
        "description": description,
        "inventory_name": inventory_name or label,
        "inventory_category": inventory_category,
        "unit_of_measure": unit_of_measure,
        "threshold": Decimal(str(threshold)),
        "is_perishable": is_perishable,
        "requires_frozen_storage": requires_frozen_storage,
        "inventory_quantity": Decimal(str(inventory_quantity)),
        "inventory_quantity_by_size": inventory_quantity_by_size or {},
    }


SODA_OPTIONS = {
    "coke": _option(
        "Coke",
        inventory_sku="BASE-COKE",
        tags=("cola", "classic", "caffeinated"),
        description="Classic cola finish",
        inventory_name="Coke Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="18.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "diet-coke": _option(
        "Diet Coke",
        inventory_sku="BASE-DIET-COKE",
        tags=("cola", "diet", "zero-sugar", "caffeinated"),
        description="Zero-sugar cola",
        inventory_name="Diet Coke Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="16.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "coke-zero": _option(
        "Coke Zero",
        inventory_sku="BASE-COKE-ZERO",
        tags=("cola", "diet", "zero-sugar", "caffeinated"),
        description="Bold zero-sugar cola",
        inventory_name="Coke Zero Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="16.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "dr-pepper": _option(
        "Dr Pepper",
        inventory_sku="BASE-DR-PEPPER",
        tags=("cola", "spiced", "caffeinated"),
        description="Spiced soda shop classic",
        inventory_name="Dr Pepper Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="16.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "diet-dr-pepper": _option(
        "Diet Dr Pepper",
        inventory_sku="BASE-DIET-DR-PEPPER",
        tags=("cola", "spiced", "diet", "zero-sugar", "caffeinated"),
        description="Spiced zero-sugar option",
        inventory_name="Diet Dr Pepper Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="14.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "pepsi": _option(
        "Pepsi",
        inventory_sku="BASE-PEPSI",
        tags=("cola", "classic", "caffeinated"),
        description="Smooth cola base",
        inventory_name="Pepsi Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="14.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "diet-pepsi": _option(
        "Diet Pepsi",
        inventory_sku="BASE-DIET-PEPSI",
        tags=("cola", "diet", "zero-sugar", "caffeinated"),
        description="Zero-sugar Pepsi base",
        inventory_name="Diet Pepsi Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="12.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "sprite": _option(
        "Sprite",
        inventory_sku="BASE-SPRITE",
        tags=("citrus", "clear", "caffeine-free"),
        description="Bright and bubbly",
        inventory_name="Sprite Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="18.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "sprite-zero": _option(
        "Sprite Zero",
        inventory_sku="BASE-SPRITE-ZERO",
        tags=("citrus", "clear", "diet", "zero-sugar", "caffeine-free"),
        description="Bright zero-sugar citrus",
        inventory_name="Sprite Zero Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="14.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "root-beer": _option(
        "Root Beer",
        inventory_sku="BASE-ROOT-BEER",
        tags=("classic", "float-friendly", "caffeine-free"),
        description="Perfect float base",
        inventory_name="Root Beer Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="14.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "orange-soda": _option(
        "Orange Soda",
        inventory_sku="BASE-ORANGE-SODA",
        tags=("fruit", "citrus", "caffeine-free"),
        description="Bright orange pop",
        inventory_name="Orange Soda Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="12.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "mountain-dew": _option(
        "Mountain Dew",
        inventory_sku="BASE-MOUNTAIN-DEW",
        tags=("citrus", "bold", "caffeinated"),
        description="Bold citrus energy",
        inventory_name="Mountain Dew Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="12.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "diet-mountain-dew": _option(
        "Diet Mountain Dew",
        inventory_sku="BASE-DIET-MOUNTAIN-DEW",
        tags=("citrus", "bold", "diet", "zero-sugar", "caffeinated"),
        description="Zero-sugar citrus energy",
        inventory_name="Diet Mountain Dew Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="10.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "lemon-lime": _option(
        "Lemon-Lime Soda",
        inventory_sku="BASE-LEMON-LIME",
        tags=("citrus", "clear", "caffeine-free"),
        description="Crisp citrus default",
        inventory_name="Lemon Lime Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="18.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "club-soda": _option(
        "Club Soda",
        inventory_sku="BASE-CLUB-SODA",
        tags=("clean", "clear", "caffeine-free", "zero-sugar"),
        description="Clean base for custom builds",
        inventory_name="Club Soda Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="10.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
    "cream-soda": _option(
        "Cream Soda",
        inventory_sku="BASE-CREAM-SODA",
        tags=("creamy", "dessert", "caffeine-free"),
        description="Sweet vanilla-leaning base",
        inventory_name="Cream Soda Base",
        inventory_category="soda",
        unit_of_measure="bag",
        threshold="12.00",
        inventory_quantity_by_size={"small": "0.40", "medium": "0.55", "large": "0.70"},
    ),
}

SODA_GROUPS = [
    {
        "label": "Cola Line",
        "description": "Classic cola bases and zero-sugar variants.",
        "items": [
            "coke",
            "diet-coke",
            "coke-zero",
            "dr-pepper",
            "diet-dr-pepper",
            "pepsi",
            "diet-pepsi",
        ],
    },
    {
        "label": "Citrus + Clear",
        "description": "Brighter bases that keep custom flavors crisp.",
        "items": [
            "sprite",
            "sprite-zero",
            "lemon-lime",
            "club-soda",
            "orange-soda",
            "mountain-dew",
            "diet-mountain-dew",
        ],
    },
    {
        "label": "Float Favorites",
        "description": "Great for richer or dessert-leaning builds.",
        "items": ["root-beer", "cream-soda"],
    },
]

SYRUP_OPTIONS = {
    "vanilla": _option(
        "Vanilla",
        inventory_sku="SYRUP-VANILLA",
        price="0.25",
        tags=("vanilla", "dessert"),
    ),
    "french-vanilla": _option(
        "French Vanilla",
        inventory_sku="SYRUP-FRENCH-VANILLA",
        price="0.25",
        tags=("vanilla", "dessert"),
    ),
    "cherry": _option(
        "Cherry", inventory_sku="SYRUP-CHERRY", price="0.25", tags=("fruit", "bright")
    ),
    "coconut": _option(
        "Coconut",
        inventory_sku="SYRUP-COCONUT",
        price="0.30",
        tags=("tropical", "creamy"),
    ),
    "lime": _option(
        "Lime", inventory_sku="SYRUP-LIME", price="0.25", tags=("citrus", "bright")
    ),
    "lemon": _option(
        "Lemon", inventory_sku="SYRUP-LEMON", price="0.25", tags=("citrus", "bright")
    ),
    "raspberry": _option(
        "Raspberry",
        inventory_sku="SYRUP-RASPBERRY",
        price="0.25",
        tags=("berry", "fruit"),
    ),
    "strawberry": _option(
        "Strawberry",
        inventory_sku="SYRUP-STRAWBERRY",
        price="0.25",
        tags=("berry", "fruit"),
    ),
    "peach": _option(
        "Peach",
        inventory_sku="SYRUP-PEACH",
        price="0.25",
        tags=("stone-fruit", "fruit"),
    ),
    "mango": _option(
        "Mango", inventory_sku="SYRUP-MANGO", price="0.30", tags=("tropical", "fruit")
    ),
    "blackberry": _option(
        "Blackberry",
        inventory_sku="SYRUP-BLACKBERRY",
        price="0.30",
        tags=("berry", "fruit"),
    ),
    "watermelon": _option(
        "Watermelon",
        inventory_sku="SYRUP-WATERMELON",
        price="0.25",
        tags=("fruit", "melon"),
    ),
    "pineapple": _option(
        "Pineapple",
        inventory_sku="SYRUP-PINEAPPLE",
        price="0.30",
        tags=("tropical", "fruit"),
    ),
    "blue-raspberry": _option(
        "Blue Raspberry",
        inventory_sku="SYRUP-BLUE-RASPBERRY",
        price="0.30",
        tags=("berry", "fruit", "playful"),
    ),
    "passion-fruit": _option(
        "Passion Fruit",
        inventory_sku="SYRUP-PASSION-FRUIT",
        price="0.30",
        tags=("tropical", "fruit"),
    ),
    "pomegranate": _option(
        "Pomegranate",
        inventory_sku="SYRUP-POMEGRANATE",
        price="0.30",
        tags=("fruit", "tart"),
    ),
    "hazelnut": _option(
        "Hazelnut",
        inventory_sku="SYRUP-HAZELNUT",
        price="0.30",
        tags=("nutty", "dessert"),
    ),
    "butterscotch": _option(
        "Butterscotch",
        inventory_sku="SYRUP-BUTTERSCOTCH",
        price="0.30",
        tags=("dessert", "caramelized"),
    ),
    "caramel": _option(
        "Caramel",
        inventory_sku="SYRUP-CARAMEL",
        price="0.30",
        tags=("dessert", "caramelized"),
    ),
    "brown-sugar-cinnamon": _option(
        "Brown Sugar Cinnamon",
        inventory_sku="SYRUP-BROWN-SUGAR-CINNAMON",
        price="0.30",
        tags=("spiced", "dessert"),
    ),
    "grapefruit": _option(
        "Grapefruit",
        inventory_sku="SYRUP-GRAPEFRUIT",
        price="0.25",
        tags=("citrus", "tart"),
    ),
    "guava": _option(
        "Guava", inventory_sku="SYRUP-GUAVA", price="0.30", tags=("tropical", "fruit")
    ),
    "orange": _option(
        "Orange", inventory_sku="SYRUP-ORANGE", price="0.25", tags=("citrus", "fruit")
    ),
    "lavender": _option(
        "Lavender",
        inventory_sku="SYRUP-LAVENDER",
        price="0.30",
        tags=("floral", "aromatic"),
    ),
    "cinnamon": _option(
        "Cinnamon",
        inventory_sku="SYRUP-CINNAMON",
        price="0.25",
        tags=("spiced", "warm"),
    ),
}

SYRUP_GROUPS = [
    {
        "label": "Fruit Shop",
        "description": "Bright berry and orchard flavors.",
        "items": [
            "strawberry",
            "cherry",
            "raspberry",
            "blackberry",
            "peach",
            "watermelon",
            "blue-raspberry",
        ],
    },
    {
        "label": "Citrus + Tropical",
        "description": "Crisp and juicy layers for refreshing cups.",
        "items": [
            "lime",
            "lemon",
            "orange",
            "grapefruit",
            "pineapple",
            "mango",
            "guava",
            "passion-fruit",
            "pomegranate",
        ],
    },
    {
        "label": "Dessert Bar",
        "description": "Creamy and cozy soda-shop flavors.",
        "items": [
            "vanilla",
            "french-vanilla",
            "caramel",
            "butterscotch",
            "hazelnut",
            "brown-sugar-cinnamon",
            "cinnamon",
        ],
    },
    {
        "label": "Floral + Signature",
        "description": "A little more adventurous without getting wild.",
        "items": ["lavender", "coconut"],
    },
]

ADD_IN_OPTIONS = {
    "cream": _option(
        "Cream",
        inventory_sku="DAIRY-CREAM",
        price="0.40",
        tags=("creamy", "dairy"),
        inventory_name="Cream",
        inventory_category="dairy",
        unit_of_measure="carton",
        threshold="8.00",
        inventory_quantity="0.20",
    ),
    "coconut-cream": _option(
        "Coconut Cream",
        inventory_sku="DAIRY-COCONUT-CREAM",
        price="0.50",
        tags=("creamy", "tropical", "dairy-free"),
        inventory_name="Coconut Cream",
        inventory_category="add_in",
        unit_of_measure="carton",
        threshold="8.00",
        inventory_quantity="0.20",
    ),
    "half-and-half": _option(
        "Half and Half",
        inventory_sku="DAIRY-HALF-AND-HALF",
        price="0.45",
        tags=("creamy", "dairy"),
        inventory_name="Half and Half",
        inventory_category="dairy",
        unit_of_measure="carton",
        threshold="8.00",
        inventory_quantity="0.20",
    ),
    "whip": _option(
        "Whip",
        inventory_sku="TOPPING-WHIP",
        price="0.45",
        tags=("creamy", "dessert", "dairy"),
        inventory_name="Whipped Topping",
        inventory_category="add_in",
        unit_of_measure="canister",
        threshold="10.00",
        inventory_quantity="0.15",
    ),
    "lime-wedge": _option(
        "Lime Wedge",
        inventory_sku="GARNISH-LIME",
        price="0.20",
        tags=("citrus", "fresh"),
        inventory_name="Lime Wedges",
        inventory_category="add_in",
        unit_of_measure="tray",
        threshold="12.00",
        is_perishable=True,
        inventory_quantity="1.00",
    ),
    "lemon-wedge": _option(
        "Lemon Wedge",
        inventory_sku="GARNISH-LEMON",
        price="0.20",
        tags=("citrus", "fresh"),
        inventory_name="Lemon Wedges",
        inventory_category="add_in",
        unit_of_measure="tray",
        threshold="12.00",
        is_perishable=True,
        inventory_quantity="1.00",
    ),
    "strawberry-puree": _option(
        "Strawberry Puree",
        inventory_sku="PUREE-STRAWBERRY",
        price="0.45",
        tags=("berry", "fruit"),
        inventory_name="Strawberry Puree",
        inventory_category="add_in",
        unit_of_measure="pouch",
        threshold="10.00",
        is_perishable=True,
        inventory_quantity="0.20",
    ),
    "mango-puree": _option(
        "Mango Puree",
        inventory_sku="PUREE-MANGO",
        price="0.45",
        tags=("tropical", "fruit"),
        inventory_name="Mango Puree",
        inventory_category="add_in",
        unit_of_measure="pouch",
        threshold="10.00",
        is_perishable=True,
        inventory_quantity="0.20",
    ),
    "fresh-mint": _option(
        "Fresh Mint",
        inventory_sku="GARNISH-MINT",
        price="0.20",
        tags=("fresh", "mint"),
        inventory_name="Fresh Mint",
        inventory_category="add_in",
        unit_of_measure="bunch",
        threshold="8.00",
        is_perishable=True,
        inventory_quantity="0.10",
    ),
}

ADD_IN_GROUPS = [
    {
        "label": "Creamy Extras",
        "description": "The richest add-ins for dirty sodas and floats.",
        "items": ["cream", "coconut-cream", "half-and-half", "whip"],
    },
    {
        "label": "Fresh Citrus",
        "description": "Small fresh add-ons that brighten the cup.",
        "items": ["lime-wedge", "lemon-wedge", "fresh-mint"],
    },
    {
        "label": "Purees",
        "description": "Fruit-forward extras for more body and color.",
        "items": ["strawberry-puree", "mango-puree"],
    },
]

ICE_CREAM_OPTIONS = {
    "scoop-vanilla": _option(
        "Vanilla",
        inventory_sku="ICECREAM-VANILLA",
        price="0.95",
        tags=("dessert", "float", "dairy"),
        inventory_name="Vanilla Ice Cream",
        inventory_category="ice_cream",
        unit_of_measure="tub",
        threshold="8.00",
        is_perishable=True,
        requires_frozen_storage=True,
        inventory_quantity="1.00",
    ),
    "scoop-chocolate": _option(
        "Chocolate",
        inventory_sku="ICECREAM-CHOCOLATE",
        price="0.95",
        tags=("dessert", "float", "dairy"),
        inventory_name="Chocolate Ice Cream",
        inventory_category="ice_cream",
        unit_of_measure="tub",
        threshold="8.00",
        is_perishable=True,
        requires_frozen_storage=True,
        inventory_quantity="1.00",
    ),
    "scoop-strawberry": _option(
        "Strawberry",
        inventory_sku="ICECREAM-STRAWBERRY",
        price="0.95",
        tags=("dessert", "float", "berry", "dairy"),
        inventory_name="Strawberry Ice Cream",
        inventory_category="ice_cream",
        unit_of_measure="tub",
        threshold="8.00",
        is_perishable=True,
        requires_frozen_storage=True,
        inventory_quantity="1.00",
    ),
}

ICE_CREAM_GROUPS = [
    {
        "label": "Float Scoop",
        "description": "Optional ice cream topper for a fuller float.",
        "items": ["scoop-vanilla", "scoop-chocolate", "scoop-strawberry"],
    }
]

DIETARY_PREFERENCE_OPTIONS = [
    ("dairy-free", "Prefer dairy-free builds"),
    ("caffeine-free", "Avoid caffeine"),
    ("zero-sugar", "Prefer zero-sugar builds"),
    ("citrus-free", "Avoid citrus"),
]

SWEETNESS_PREFERENCE_CHOICES = [
    ("light", "Keep sweetness light"),
    ("balanced", "Balanced sweetness"),
    ("sweet", "Sweet and soda-shop classic"),
    ("extra_sweet", "Go extra sweet"),
]

ADVENTUROUSNESS_PREFERENCE_CHOICES = [
    ("classic", "Mostly classic combinations"),
    ("balanced", "A mix of classics and signature twists"),
    ("adventurous", "Bring in bolder or less expected combos"),
]

MENU_ITEMS = {
    "berry-burst": {
        "slug": "berry-burst",
        "name": "Berry Burst",
        "description": "Bright berry fizz with a crisp, easy-to-love finish.",
        "base_prices": {"small": "2.95", "medium": "3.55", "large": "4.15"},
        "default_soda": "sprite",
        "default_syrups": ["strawberry"],
        "default_add_ins": [],
        "default_ice_cream": "",
        "tags": ["berry", "bright", "refreshing"],
        "home_badge": "Popular",
    },
    "vanilla-sunset": {
        "slug": "vanilla-sunset",
        "name": "Vanilla Sunset",
        "description": "Cola, vanilla, and citrus for a soft soda-shop throwback.",
        "base_prices": {"small": "3.05", "medium": "3.65", "large": "4.25"},
        "default_soda": "coke",
        "default_syrups": ["vanilla"],
        "default_add_ins": ["lime-wedge"],
        "default_ice_cream": "",
        "tags": ["cola", "vanilla", "balanced"],
        "home_badge": "Popular",
    },
    "cache-float": {
        "slug": "cache-float",
        "name": "Cache Float",
        "description": "A smooth float with cola, vanilla, and a classic vanilla scoop.",
        "base_prices": {"small": "3.45", "medium": "4.05", "large": "4.75"},
        "default_soda": "root-beer",
        "default_syrups": ["vanilla"],
        "default_add_ins": ["cream"],
        "default_ice_cream": "scoop-vanilla",
        "tags": ["dessert", "float", "creamy"],
        "home_badge": "Signature",
    },
    "citrus-mint-drive": {
        "slug": "citrus-mint-drive",
        "name": "Citrus Mint Drive",
        "description": "Lemon-lime soda with clean citrus layers and a cool mint finish.",
        "base_prices": {"small": "2.85", "medium": "3.45", "large": "4.05"},
        "default_soda": "lemon-lime",
        "default_syrups": ["lime"],
        "default_add_ins": ["fresh-mint"],
        "default_ice_cream": "",
        "tags": ["citrus", "mint", "refreshing"],
        "home_badge": "Fresh",
    },
    "double-berry-float": {
        "slug": "double-berry-float",
        "name": "Double Berry Float",
        "description": "Berry-heavy soda finished like a rich but still playful float.",
        "base_prices": {"small": "3.55", "medium": "4.20", "large": "4.85"},
        "default_soda": "sprite",
        "default_syrups": ["strawberry", "raspberry"],
        "default_add_ins": ["cream"],
        "default_ice_cream": "scoop-strawberry",
        "tags": ["berry", "dessert", "float"],
        "home_badge": "New",
    },
    "cherry-cola-cruise": {
        "slug": "cherry-cola-cruise",
        "name": "Cherry Cola Cruise",
        "description": "Classic Coke with cherry, vanilla, and a clean citrus finish.",
        "base_prices": {"small": "3.10", "medium": "3.70", "large": "4.30"},
        "default_soda": "coke",
        "default_syrups": ["cherry", "vanilla"],
        "default_add_ins": ["lime-wedge"],
        "default_ice_cream": "",
        "tags": ["coke", "cherry", "classic"],
    },
    "midnight-cola-zero": {
        "slug": "midnight-cola-zero",
        "name": "Midnight Cola Zero",
        "description": "Coke Zero with blackberry and lime for a sharper finish.",
        "base_prices": {"small": "3.00", "medium": "3.60", "large": "4.20"},
        "default_soda": "coke-zero",
        "default_syrups": ["blackberry", "lime"],
        "default_add_ins": [],
        "default_ice_cream": "",
        "tags": ["coke", "zero-sugar", "berry"],
    },
    "pepsi-peach-wave": {
        "slug": "pepsi-peach-wave",
        "name": "Pepsi Peach Wave",
        "description": "Smooth Pepsi with peach and lemon layers for easy sipping.",
        "base_prices": {"small": "3.05", "medium": "3.65", "large": "4.25"},
        "default_soda": "pepsi",
        "default_syrups": ["peach", "lemon"],
        "default_add_ins": [],
        "default_ice_cream": "",
        "tags": ["pepsi", "fruit", "balanced"],
    },
    "pepsi-vanilla-drift": {
        "slug": "pepsi-vanilla-drift",
        "name": "Pepsi Vanilla Drift",
        "description": "Diet Pepsi with vanilla and coconut cream for a lighter dirty-soda profile.",
        "base_prices": {"small": "3.25", "medium": "3.90", "large": "4.50"},
        "default_soda": "diet-pepsi",
        "default_syrups": ["french-vanilla"],
        "default_add_ins": ["coconut-cream"],
        "default_ice_cream": "",
        "tags": ["pepsi", "vanilla", "creamy"],
    },
    "dew-lime-launch": {
        "slug": "dew-lime-launch",
        "name": "Dew Lime Launch",
        "description": "Mountain Dew with lime and pineapple for a bright citrus pop.",
        "base_prices": {"small": "3.10", "medium": "3.75", "large": "4.35"},
        "default_soda": "mountain-dew",
        "default_syrups": ["lime", "pineapple"],
        "default_add_ins": [],
        "default_ice_cream": "",
        "tags": ["mtn-dew", "citrus", "bold"],
    },
    "dew-tropic-rush": {
        "slug": "dew-tropic-rush",
        "name": "Dew Tropic Rush",
        "description": "Diet Mountain Dew layered with mango and guava for a clean tropical profile.",
        "base_prices": {"small": "3.15", "medium": "3.80", "large": "4.40"},
        "default_soda": "diet-mountain-dew",
        "default_syrups": ["mango", "guava"],
        "default_add_ins": [],
        "default_ice_cream": "",
        "tags": ["mtn-dew", "tropical", "zero-sugar"],
    },
    "pepper-cherry-stack": {
        "slug": "pepper-cherry-stack",
        "name": "Pepper Cherry Stack",
        "description": "Dr Pepper with cherry and vanilla for a rich soda-shop combo.",
        "base_prices": {"small": "3.20", "medium": "3.85", "large": "4.45"},
        "default_soda": "dr-pepper",
        "default_syrups": ["cherry", "vanilla"],
        "default_add_ins": [],
        "default_ice_cream": "",
        "tags": ["dr-pepper", "cherry", "classic"],
    },
    "pepper-cream-cloud": {
        "slug": "pepper-cream-cloud",
        "name": "Pepper Cream Cloud",
        "description": "Diet Dr Pepper with coconut cream and vanilla for a smooth finish.",
        "base_prices": {"small": "3.30", "medium": "3.95", "large": "4.55"},
        "default_soda": "diet-dr-pepper",
        "default_syrups": ["vanilla"],
        "default_add_ins": ["coconut-cream"],
        "default_ice_cream": "",
        "tags": ["dr-pepper", "creamy", "zero-sugar"],
    },
    "pepper-berry-lift": {
        "slug": "pepper-berry-lift",
        "name": "Pepper Berry Lift",
        "description": "Dr Pepper with blackberry and lime for a bright, spiced finish.",
        "base_prices": {"small": "3.20", "medium": "3.85", "large": "4.45"},
        "default_soda": "dr-pepper",
        "default_syrups": ["blackberry", "lime"],
        "default_add_ins": [],
        "default_ice_cream": "",
        "tags": ["dr-pepper", "berry", "refreshing"],
    },
    "sprite-garden-fizz": {
        "slug": "sprite-garden-fizz",
        "name": "Sprite Garden Fizz",
        "description": "Sprite Zero with lavender, lemon, and mint for a crisp botanical lift.",
        "base_prices": {"small": "3.05", "medium": "3.65", "large": "4.25"},
        "default_soda": "sprite-zero",
        "default_syrups": ["lavender", "lemon"],
        "default_add_ins": ["fresh-mint"],
        "default_ice_cream": "",
        "tags": ["sprite", "botanical", "zero-sugar"],
    },
    "root-beer-caramel-cream": {
        "slug": "root-beer-caramel-cream",
        "name": "Root Beer Caramel Cream",
        "description": "Root beer with caramel and half-and-half for a richer craft float profile.",
        "base_prices": {"small": "3.50", "medium": "4.10", "large": "4.80"},
        "default_soda": "root-beer",
        "default_syrups": ["caramel"],
        "default_add_ins": ["half-and-half"],
        "default_ice_cream": "",
        "tags": ["root-beer", "caramel", "creamy"],
        "home_badge": "Popular",
    },
    "orange-creamsicle": {
        "slug": "orange-creamsicle",
        "name": "Orange Creamsicle",
        "description": "Orange soda, vanilla syrup, and cream with a vanilla scoop finish.",
        "base_prices": {"small": "3.60", "medium": "4.25", "large": "4.95"},
        "default_soda": "orange-soda",
        "default_syrups": ["vanilla"],
        "default_add_ins": ["cream"],
        "default_ice_cream": "scoop-vanilla",
        "tags": ["orange", "dessert", "float"],
        "home_badge": "Signature",
    },
    "cream-soda-cobbler": {
        "slug": "cream-soda-cobbler",
        "name": "Cream Soda Cobbler",
        "description": "Cream soda with peach and vanilla plus whipped topping.",
        "base_prices": {"small": "3.35", "medium": "4.00", "large": "4.70"},
        "default_soda": "cream-soda",
        "default_syrups": ["peach", "vanilla"],
        "default_add_ins": ["whip"],
        "default_ice_cream": "",
        "tags": ["cream-soda", "peach", "dessert"],
    },
    "club-citrus-cooler": {
        "slug": "club-citrus-cooler",
        "name": "Club Citrus Cooler",
        "description": "Club soda with grapefruit and lime, finished with fresh mint.",
        "base_prices": {"small": "2.95", "medium": "3.55", "large": "4.15"},
        "default_soda": "club-soda",
        "default_syrups": ["grapefruit", "lime"],
        "default_add_ins": ["fresh-mint"],
        "default_ice_cream": "",
        "tags": ["club-soda", "citrus", "clean"],
    },
    "club-berry-spark": {
        "slug": "club-berry-spark",
        "name": "Club Berry Spark",
        "description": "Club soda with blackberry and lemon for a crisp berry sparkle.",
        "base_prices": {"small": "3.00", "medium": "3.60", "large": "4.20"},
        "default_soda": "club-soda",
        "default_syrups": ["blackberry", "lemon"],
        "default_add_ins": [],
        "default_ice_cream": "",
        "tags": ["club-soda", "berry", "refreshing"],
    },
    "club-cucumber-cool": {
        "slug": "club-cucumber-cool",
        "name": "Club Cucumber Cool",
        "description": "Club soda with lime and fresh mint for a crisp, spa-like sip.",
        "base_prices": {"small": "2.95", "medium": "3.55", "large": "4.15"},
        "default_soda": "club-soda",
        "default_syrups": ["lime"],
        "default_add_ins": ["fresh-mint"],
        "default_ice_cream": "",
        "tags": ["club-soda", "mint", "light"],
    },
    "cream-berry-velvet": {
        "slug": "cream-berry-velvet",
        "name": "Cream Berry Velvet",
        "description": "Cream soda with strawberry, vanilla, and a smooth creamy finish.",
        "base_prices": {"small": "3.40", "medium": "4.05", "large": "4.75"},
        "default_soda": "cream-soda",
        "default_syrups": ["strawberry", "vanilla"],
        "default_add_ins": ["half-and-half"],
        "default_ice_cream": "",
        "tags": ["cream-soda", "berry", "creamy"],
    },
    "cream-citrus-silk": {
        "slug": "cream-citrus-silk",
        "name": "Cream Citrus Silk",
        "description": "Cream soda with orange and vanilla plus whip for a silky soda-shop finish.",
        "base_prices": {"small": "3.45", "medium": "4.10", "large": "4.80"},
        "default_soda": "cream-soda",
        "default_syrups": ["orange", "vanilla"],
        "default_add_ins": ["whip"],
        "default_ice_cream": "",
        "tags": ["cream-soda", "citrus", "dessert"],
    },
    "sunset-pineapple-splash": {
        "slug": "sunset-pineapple-splash",
        "name": "Sunset Pineapple Splash",
        "description": "Orange soda with pineapple and passion fruit for a tropical finish.",
        "base_prices": {"small": "3.15", "medium": "3.80", "large": "4.45"},
        "default_soda": "orange-soda",
        "default_syrups": ["pineapple", "passion-fruit"],
        "default_add_ins": [],
        "default_ice_cream": "",
        "tags": ["orange", "tropical", "refreshing"],
    },
    "orange-coconut-cloud": {
        "slug": "orange-coconut-cloud",
        "name": "Orange Coconut Cloud",
        "description": "Orange soda with coconut and cream for a smooth tropical dirty soda.",
        "base_prices": {"small": "3.40", "medium": "4.05", "large": "4.70"},
        "default_soda": "orange-soda",
        "default_syrups": ["coconut"],
        "default_add_ins": ["cream"],
        "default_ice_cream": "",
        "tags": ["orange", "tropical", "creamy"],
    },
    "blackberry-pepsi-night": {
        "slug": "blackberry-pepsi-night",
        "name": "Blackberry Pepsi Night",
        "description": "Pepsi with blackberry and vanilla for a deeper after-dinner profile.",
        "base_prices": {"small": "3.15", "medium": "3.80", "large": "4.40"},
        "default_soda": "pepsi",
        "default_syrups": ["blackberry", "vanilla"],
        "default_add_ins": [],
        "default_ice_cream": "",
        "tags": ["pepsi", "berry", "smooth"],
    },
    "root-beer-cocoa-float": {
        "slug": "root-beer-cocoa-float",
        "name": "Root Beer Cocoa Float",
        "description": "Root beer layered with vanilla and a chocolate scoop for a rich float.",
        "base_prices": {"small": "3.70", "medium": "4.35", "large": "5.05"},
        "default_soda": "root-beer",
        "default_syrups": ["vanilla"],
        "default_add_ins": ["whip"],
        "default_ice_cream": "scoop-chocolate",
        "tags": ["root-beer", "float", "dessert"],
        "home_badge": "New",
    },
    "mountain-berry-stride": {
        "slug": "mountain-berry-stride",
        "name": "Mountain Berry Stride",
        "description": "Mountain Dew with blue raspberry and lime for a bright, crisp finish.",
        "base_prices": {"small": "3.20", "medium": "3.85", "large": "4.50"},
        "default_soda": "mountain-dew",
        "default_syrups": ["blue-raspberry", "lime"],
        "default_add_ins": [],
        "default_ice_cream": "",
        "tags": ["mtn-dew", "berry", "bright"],
    },
}

ALL_INGREDIENT_OPTIONS = {
    **SODA_OPTIONS,
    **SYRUP_OPTIONS,
    **ADD_IN_OPTIONS,
    **ICE_CREAM_OPTIONS,
}

INGREDIENT_LABELS = {
    key: option["label"] for key, option in ALL_INGREDIENT_OPTIONS.items()
}


def get_menu_items():
    return [deepcopy(item) for item in MENU_ITEMS.values()]


def get_menu_item(drink_slug):
    try:
        return deepcopy(MENU_ITEMS[drink_slug])
    except KeyError as exc:
        raise KeyError(f"Unknown menu item '{drink_slug}'.") from exc


def grouped_options(option_map, group_definitions):
    return [
        {
            "label": group["label"],
            "description": group.get("description", ""),
            "items": [
                {
                    "value": key,
                    **deepcopy(option_map[key]),
                }
                for key in group["items"]
            ],
        }
        for group in group_definitions
    ]


def combined_ingredient_choices(
    *,
    include_sodas=True,
    include_syrups=True,
    include_add_ins=True,
    include_ice_cream=True,
):
    choices = []
    if include_sodas:
        choices.extend((key, option["label"]) for key, option in SODA_OPTIONS.items())
    if include_syrups:
        choices.extend((key, option["label"]) for key, option in SYRUP_OPTIONS.items())
    if include_add_ins:
        choices.extend((key, option["label"]) for key, option in ADD_IN_OPTIONS.items())
    if include_ice_cream:
        choices.extend(
            (key, option["label"]) for key, option in ICE_CREAM_OPTIONS.items()
        )
    return choices


def ingredient_label(token):
    return INGREDIENT_LABELS.get(token, token.replace("-", " ").title())


def catalog_inventory_definitions():
    inventory_rows = [
        (
            "CUPS-24OZ",
            "24oz Cups",
            "cups",
            "each",
            "200.00",
            False,
            False,
        ),
        (
            "LIDS-24OZ",
            "24oz Lids",
            "lids",
            "each",
            "200.00",
            False,
            False,
        ),
        (
            "SANITIZER",
            "Sanitizer",
            "cleaning",
            "gallon",
            "5.00",
            False,
            False,
        ),
    ]
    for option in ALL_INGREDIENT_OPTIONS.values():
        if not option["inventory_sku"]:
            continue
        inventory_rows.append(
            (
                option["inventory_sku"],
                option["inventory_name"],
                option["inventory_category"],
                option["unit_of_measure"],
                str(option["threshold"]),
                option["is_perishable"],
                option["requires_frozen_storage"],
            )
        )
    return inventory_rows


def describe_customizations(*, size, soda, syrups, add_ins, ice_cream="", notes=""):
    parts = [SIZE_LABELS.get(size, size.title()), ingredient_label(soda)]
    if syrups:
        parts.append(" + ".join(ingredient_label(syrup) for syrup in syrups))
    if add_ins:
        parts.append(", ".join(ingredient_label(add_in) for add_in in add_ins))
    if ice_cream:
        parts.append(f"{ingredient_label(ice_cream)} ice cream")
    if notes:
        parts.append(notes)
    return " | ".join(parts)


def _inventory_quantity(option, size):
    quantity_by_size = option.get("inventory_quantity_by_size") or {}
    if size in quantity_by_size:
        return quantity_by_size[size]
    return option["inventory_quantity"]


def build_inventory_requirements(*, size, soda, syrups, add_ins, ice_cream=""):
    requirements = [
        {"sku": "CUPS-24OZ", "quantity": "1.00"},
        {"sku": "LIDS-24OZ", "quantity": "1.00"},
    ]

    soda_option = SODA_OPTIONS[soda]
    if soda_option["inventory_sku"]:
        requirements.append(
            {
                "sku": soda_option["inventory_sku"],
                "quantity": str(_inventory_quantity(soda_option, size)),
            }
        )

    for syrup in syrups:
        syrup_option = SYRUP_OPTIONS[syrup]
        if syrup_option["inventory_sku"]:
            requirements.append(
                {
                    "sku": syrup_option["inventory_sku"],
                    "quantity": str(_inventory_quantity(syrup_option, size)),
                }
            )

    for add_in in add_ins:
        add_in_option = ADD_IN_OPTIONS[add_in]
        if add_in_option["inventory_sku"]:
            requirements.append(
                {
                    "sku": add_in_option["inventory_sku"],
                    "quantity": str(_inventory_quantity(add_in_option, size)),
                }
            )

    if ice_cream:
        ice_cream_option = ICE_CREAM_OPTIONS[ice_cream]
        requirements.append(
            {
                "sku": ice_cream_option["inventory_sku"],
                "quantity": str(_inventory_quantity(ice_cream_option, size)),
            }
        )

    return requirements


def calculate_extras_total(*, syrups, add_ins, ice_cream=""):
    syrup_total = sum(SYRUP_OPTIONS[syrup]["price"] for syrup in syrups)
    add_in_total = sum(ADD_IN_OPTIONS[add_in]["price"] for add_in in add_ins)
    ice_cream_total = (
        ICE_CREAM_OPTIONS[ice_cream]["price"] if ice_cream else Decimal("0.00")
    )
    return syrup_total + add_in_total + ice_cream_total


def estimate_item_total(*, drink_slug, size, syrups, add_ins, ice_cream=""):
    menu_item = get_menu_item(drink_slug)
    return Decimal(menu_item["base_prices"][size]) + calculate_extras_total(
        syrups=syrups,
        add_ins=add_ins,
        ice_cream=ice_cream,
    )


def build_cart_item(
    *,
    drink_slug,
    size,
    soda,
    syrups,
    add_ins,
    ice_cream="",
    quantity=1,
    notes="",
):
    menu_item = get_menu_item(drink_slug)
    base_price = Decimal(menu_item["base_prices"][size])
    extras_total = calculate_extras_total(
        syrups=syrups,
        add_ins=add_ins,
        ice_cream=ice_cream,
    )
    return {
        "menu_key": drink_slug,
        "display_name": menu_item["name"],
        "size": size,
        "base_price": str(base_price),
        "extras_total": str(extras_total),
        "quantity": quantity,
        "description": describe_customizations(
            size=size,
            soda=soda,
            syrups=syrups,
            add_ins=add_ins,
            ice_cream=ice_cream,
            notes=notes,
        ),
        "customizations": {
            "soda": soda,
            "syrups": syrups,
            "add_ins": add_ins,
            "ice_cream": ice_cream,
            "notes": notes,
            "inventory_requirements": build_inventory_requirements(
                size=size,
                soda=soda,
                syrups=syrups,
                add_ins=add_ins,
                ice_cream=ice_cream,
            ),
        },
    }
