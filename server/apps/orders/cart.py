import uuid

from .services import validate_pricing

SESSION_CART_KEY = "codepop_cart"


def get_cart(session):
    cart = session.get(SESSION_CART_KEY)
    if cart is None:
        cart = {"store_code": "", "items": []}
        session[SESSION_CART_KEY] = cart
    return cart


def save_cart(session, cart):
    session[SESSION_CART_KEY] = cart
    session.modified = True


def clear_cart(session):
    save_cart(session, {"store_code": "", "items": []})


def add_cart_item(session, *, store_code, item):
    cart = get_cart(session)
    replaced_store = bool(cart["store_code"] and cart["store_code"] != store_code)
    if replaced_store:
        cart = {"store_code": store_code, "items": []}
    elif not cart["store_code"]:
        cart["store_code"] = store_code

    item = dict(item)
    item["item_id"] = uuid.uuid4().hex
    cart["items"].append(item)
    save_cart(session, cart)
    return cart, replaced_store


def update_cart_item(session, item_id, quantity):
    cart = get_cart(session)
    cart["items"] = [
        {**item, "quantity": quantity} if item["item_id"] == item_id else item
        for item in cart["items"]
        if not (item["item_id"] == item_id and quantity <= 0)
    ]
    if not cart["items"]:
        cart["store_code"] = ""
    save_cart(session, cart)
    return cart


def remove_cart_item(session, item_id):
    cart = get_cart(session)
    cart["items"] = [item for item in cart["items"] if item["item_id"] != item_id]
    if not cart["items"]:
        cart["store_code"] = ""
    save_cart(session, cart)
    return cart


def cart_item_count(cart):
    return sum(int(item.get("quantity", 1)) for item in cart.get("items", []))


def build_cart_pricing(*, cart, store):
    if not cart.get("items"):
        return None
    return validate_pricing(store=store, items=cart["items"])
