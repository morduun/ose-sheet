"""Currency management for OSE.

Currency lives as CharacterItem/StashItem instances with item_type='currency'.
State holds denominations: {cp: int, sp: int, ep: int, gp: int, pp: int}.
Weight = sum of all coins (1 coin = 1 cn).
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from sqlalchemy.orm.attributes import flag_modified

DENOMINATIONS = ["cp", "sp", "ep", "gp", "pp"]
# Character model field names for each denomination (used during migration only)
CHAR_FIELDS = {"cp": "copper", "sp": "silver", "ep": "electrum", "gp": "gold", "pp": "platinum"}


def _get_coins_item_id(db: "Session") -> int:
    """Get the default Coins item ID."""
    from app.models.item import Item
    coins = db.query(Item).filter(Item.name == "Coins", Item.item_type == "currency", Item.is_default == True).first()
    if not coins:
        raise RuntimeError("Default 'Coins' item not found — run seed script")
    return coins.id


def _coin_state(cp=0, sp=0, ep=0, gp=0, pp=0) -> dict:
    """Build a coin state dict, omitting zero values for cleanliness."""
    return {k: v for k, v in {"cp": cp, "sp": sp, "ep": ep, "gp": gp, "pp": pp}.items() if v}


def coin_weight_from_state(state: dict | None) -> int:
    """Compute weight in cn from a currency state dict."""
    if not state:
        return 0
    return sum(state.get(d, 0) for d in DENOMINATIONS)


def get_currency_instances(character_id: int, db: "Session"):
    """Get all currency CharacterItem instances for a character."""
    from app.models.item import CharacterItem, Item
    return (
        db.query(CharacterItem)
        .join(Item, CharacterItem.item_id == Item.id)
        .filter(
            CharacterItem.character_id == character_id,
            Item.item_type == "currency",
        )
        .all()
    )


def get_coin_totals(character_id: int, db: "Session") -> dict:
    """Sum all denominations across all currency instances for a character."""
    instances = get_currency_instances(character_id, db)
    totals = {d: 0 for d in DENOMINATIONS}
    for ci in instances:
        for d in DENOMINATIONS:
            totals[d] += (ci.state or {}).get(d, 0)
    return totals


def add_coins(character_id: int, amounts: dict, db: "Session", container_id: int | None = None):
    """
    Add coins to a character's inventory.

    If a loose (no container) currency instance exists and container_id is None,
    adds to it. Otherwise creates a new instance.
    """
    from app.models.item import CharacterItem

    # Only add if there's actually something to add
    total = sum(amounts.get(d, 0) for d in DENOMINATIONS)
    if total <= 0:
        return

    coins_item_id = _get_coins_item_id(db)

    # Look for existing currency instance in the target location
    if container_id is not None:
        existing = (
            db.query(CharacterItem)
            .filter(
                CharacterItem.character_id == character_id,
                CharacterItem.item_id == coins_item_id,
                CharacterItem.container_id == container_id,
            )
            .first()
        )
    else:
        existing = (
            db.query(CharacterItem)
            .filter(
                CharacterItem.character_id == character_id,
                CharacterItem.item_id == coins_item_id,
                CharacterItem.container_id.is_(None),
                CharacterItem.stashed == False,
            )
            .first()
        )

    if existing:
        state = dict(existing.state or {})
        for d in DENOMINATIONS:
            state[d] = state.get(d, 0) + amounts.get(d, 0)
        existing.state = state
        flag_modified(existing, "state")
    else:
        ci = CharacterItem(
            character_id=character_id,
            item_id=coins_item_id,
            quantity=1,
            container_id=container_id,
            state=_coin_state(**{d: amounts.get(d, 0) for d in DENOMINATIONS}),
        )
        db.add(ci)


def spend_coins(character_id: int, amounts: dict, db: "Session") -> bool:
    """
    Spend coins from a character's inventory.

    Drains from loose piles first, then smallest-capacity containers first.
    Returns True if successful, False if insufficient funds for any denomination.
    Does NOT make change between denominations.
    """
    from app.models.item import CharacterItem, Item

    instances = get_currency_instances(character_id, db)
    if not instances:
        return False

    # Check totals first
    totals = {d: 0 for d in DENOMINATIONS}
    for ci in instances:
        for d in DENOMINATIONS:
            totals[d] += (ci.state or {}).get(d, 0)

    for d in DENOMINATIONS:
        if amounts.get(d, 0) > totals[d]:
            return False

    # Sort: loose first (container_id is None), then by container capacity ascending
    def sort_key(ci):
        if ci.container_id is None:
            return (0, 0)
        # Get container's capacity for sorting
        container = db.query(CharacterItem).filter(CharacterItem.id == ci.container_id).first()
        if container:
            container_item = db.query(Item).filter(Item.id == container.item_id).first()
            capacity = (container_item.item_metadata or {}).get("capacity", 9999) if container_item else 9999
        else:
            capacity = 9999
        return (1, capacity)

    sorted_instances = sorted(instances, key=sort_key)

    # Drain each denomination
    for d in DENOMINATIONS:
        remaining = amounts.get(d, 0)
        if remaining <= 0:
            continue
        for ci in sorted_instances:
            state = dict(ci.state or {})
            available = state.get(d, 0)
            if available <= 0:
                continue
            take = min(available, remaining)
            state[d] = available - take
            remaining -= take
            ci.state = state
            flag_modified(ci, "state")
            if remaining <= 0:
                break

    # Clean up empty currency instances
    for ci in sorted_instances:
        if coin_weight_from_state(ci.state) == 0:
            db.delete(ci)

    return True


def get_stash_currency(campaign_id: int, db: "Session"):
    """Get the campaign's treasury currency StashItem instance (or None)."""
    from app.models.item import StashItem, Item
    return (
        db.query(StashItem)
        .join(Item, StashItem.item_id == Item.id)
        .filter(
            StashItem.campaign_id == campaign_id,
            Item.item_type == "currency",
            StashItem.container_id.is_(None),
        )
        .first()
    )


def get_stash_coin_totals(campaign_id: int, db: "Session") -> dict:
    """Get total treasury coins for a campaign."""
    from app.models.item import StashItem, Item
    rows = (
        db.query(StashItem)
        .join(Item, StashItem.item_id == Item.id)
        .filter(
            StashItem.campaign_id == campaign_id,
            Item.item_type == "currency",
        )
        .all()
    )
    totals = {d: 0 for d in DENOMINATIONS}
    for row in rows:
        for d in DENOMINATIONS:
            totals[d] += (row.state or {}).get(d, 0)
    return totals


def add_stash_coins(campaign_id: int, amounts: dict, db: "Session"):
    """Add coins to the campaign treasury. Creates instance if needed."""
    from app.models.item import StashItem

    total = sum(amounts.get(d, 0) for d in DENOMINATIONS)
    if total <= 0:
        return

    coins_item_id = _get_coins_item_id(db)
    existing = get_stash_currency(campaign_id, db)

    if existing:
        state = dict(existing.state or {})
        for d in DENOMINATIONS:
            state[d] = state.get(d, 0) + amounts.get(d, 0)
        existing.state = state
        flag_modified(existing, "state")
    else:
        si = StashItem(
            campaign_id=campaign_id,
            item_id=coins_item_id,
            quantity=1,
            state=_coin_state(**{d: amounts.get(d, 0) for d in DENOMINATIONS}),
        )
        db.add(si)


def take_stash_coins(campaign_id: int, amounts: dict, db: "Session") -> bool:
    """
    Remove coins from the campaign treasury.
    Returns True if successful, False if insufficient.
    """
    totals = get_stash_coin_totals(campaign_id, db)
    for d in DENOMINATIONS:
        if amounts.get(d, 0) > totals[d]:
            return False

    existing = get_stash_currency(campaign_id, db)
    if not existing:
        return False

    state = dict(existing.state or {})
    for d in DENOMINATIONS:
        state[d] = state.get(d, 0) - amounts.get(d, 0)
    existing.state = state
    flag_modified(existing, "state")

    if coin_weight_from_state(state) == 0:
        db.delete(existing)

    return True
