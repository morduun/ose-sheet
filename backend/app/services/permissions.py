"""Permission and authorization service for access control."""

from app.models import User, Campaign, Character, Item, CharacterClass, Monster


def is_admin(user: User) -> bool:
    """
    Check if user has admin privileges.

    Args:
        user: User to check

    Returns:
        True if user is an admin, False otherwise
    """
    return user.is_admin


def can_create_default_content(user: User) -> bool:
    """
    Check if user can create default items/spells. Admin-only.

    Args:
        user: User to check

    Returns:
        True if user can create defaults, False otherwise
    """
    return is_admin(user)


def is_campaign_gm(user: User, campaign: Campaign) -> bool:
    """
    Check if user is the GM (Game Master) of a campaign.

    Args:
        user: User to check
        campaign: Campaign to check against

    Returns:
        True if user is the campaign GM, False otherwise
    """
    return campaign.gm_id == user.id


def is_campaign_member(user: User, campaign: Campaign) -> bool:
    """
    Check if user is a member (player) of a campaign.

    Args:
        user: User to check
        campaign: Campaign to check against

    Returns:
        True if user is in the campaign's players list, False otherwise
    """
    return user in campaign.players


def can_view_campaign(user: User, campaign: Campaign) -> bool:
    """
    Check if user can view a campaign (either GM or member).

    Args:
        user: User to check
        campaign: Campaign to check against

    Returns:
        True if user can view the campaign, False otherwise
    """
    return is_campaign_gm(user, campaign) or is_campaign_member(user, campaign)


def can_edit_campaign(user: User, campaign: Campaign) -> bool:
    """
    Check if user can edit a campaign (must be GM).

    Args:
        user: User to check
        campaign: Campaign to check against

    Returns:
        True if user can edit the campaign, False otherwise
    """
    return is_campaign_gm(user, campaign)


def is_character_owner(user: User, character: Character) -> bool:
    """
    Check if user owns a character.

    Args:
        user: User to check
        character: Character to check against

    Returns:
        True if user owns the character, False otherwise
    """
    return character.player_id == user.id


def can_edit_character(user: User, character: Character) -> bool:
    """
    Check if user can edit a character (either owner or campaign GM).

    Args:
        user: User to check
        character: Character to check against

    Returns:
        True if user can edit the character, False otherwise
    """
    return is_character_owner(user, character) or is_campaign_gm(
        user, character.campaign
    )


def can_view_character(user: User, character: Character) -> bool:
    """
    Check if user can view a character (owner, GM, or campaign member).

    Args:
        user: User to check
        character: Character to check against

    Returns:
        True if user can view the character, False otherwise
    """
    return (
        is_character_owner(user, character)
        or is_campaign_gm(user, character.campaign)
        or is_campaign_member(user, character.campaign)
    )


def can_edit_item(user: User, item: Item) -> bool:
    """
    Check if user can edit an item.

    For default items: No one can edit (admin-only, not implemented in Phase 2)
    For campaign items: Must be campaign GM

    Args:
        user: User to check
        item: Item to check against

    Returns:
        True if user can edit the item, False otherwise
    """
    if item.is_default:
        # Default items are admin-only
        return is_admin(user)

    if item.campaign_id is None:
        # Orphaned item, no one can edit
        return False

    return is_campaign_gm(user, item.campaign)


def can_view_item_full(user: User, item: Item) -> bool:
    """
    Check if user can view full item details (including GM description).

    Args:
        user: User to check
        item: Item to check against

    Returns:
        True if user can view full details, False otherwise
    """
    if item.is_default:
        # Anyone can view default items (player-visible parts)
        return False

    if item.campaign_id is None:
        return False

    return is_campaign_gm(user, item.campaign)


def can_assign_item_to_character(user: User, character: Character) -> bool:
    """
    Check if user can assign items to a character.

    Args:
        user: User to check
        character: Character receiving the item

    Returns:
        True if user can assign items to the character, False otherwise
    """
    return can_edit_character(user, character)



def can_edit_monster(user: User, monster: Monster) -> bool:
    """
    Check if user can edit a monster.

    For default monsters: Admin-only
    For campaign monsters: Must be campaign GM

    Args:
        user: User to check
        monster: Monster to check against

    Returns:
        True if user can edit the monster, False otherwise
    """
    if monster.is_default:
        return is_admin(user)

    if monster.campaign_id is None:
        return False

    return is_campaign_gm(user, monster.campaign)


def can_edit_character_class(user: User, character_class: CharacterClass) -> bool:
    """
    Check if user can edit a character class.

    For default classes: Admin-only
    For campaign classes: Must be campaign GM

    Args:
        user: User to check
        character_class: CharacterClass to check against

    Returns:
        True if user can edit the character class, False otherwise
    """
    if character_class.is_default:
        # Default classes are admin-only
        return is_admin(user)

    if character_class.campaign_id is None:
        # Orphaned class, no one can edit
        return False

    return is_campaign_gm(user, character_class.campaign)


def get_user_campaigns(user: User) -> list:
    """
    Get all campaigns a user has access to (as GM or player).

    Args:
        user: User to get campaigns for

    Returns:
        List of campaign IDs the user has access to
    """
    campaign_ids = []

    # Campaigns where user is GM
    for campaign in user.campaigns_as_gm:
        campaign_ids.append(campaign.id)

    # Campaigns where user is player
    for campaign in user.campaigns_as_player:
        if campaign.id not in campaign_ids:
            campaign_ids.append(campaign.id)

    return campaign_ids
