from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Campaign, User
from app.schemas import (
    Campaign as CampaignSchema,
    CampaignCreate,
    CampaignUpdate,
    CampaignWithDetails,
    CampaignJoin,
)
from app.services.permissions import (
    can_view_campaign,
    can_edit_campaign,
    get_user_campaigns,
)

router = APIRouter()


@router.post("/", response_model=CampaignSchema, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new campaign. Authenticated user becomes the GM."""
    db_campaign = Campaign(
        name=campaign.name,
        description=campaign.description,
        gm_id=current_user.id,
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign


@router.get("/", response_model=list[CampaignSchema])
async def list_campaigns(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List campaigns the user has access to (as GM or player)."""
    # Get campaign IDs user has access to
    user_campaign_ids = get_user_campaigns(current_user)

    # Query campaigns user has access to
    campaigns = (
        db.query(Campaign)
        .filter(Campaign.id.in_(user_campaign_ids))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return campaigns


@router.get("/{campaign_id}", response_model=CampaignWithDetails)
async def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific campaign by ID. Requires GM or player access."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with id {campaign_id} not found",
        )

    # Check if user has access to this campaign
    if not can_view_campaign(current_user, campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this campaign",
        )

    return campaign


@router.patch("/{campaign_id}", response_model=CampaignSchema)
async def update_campaign(
    campaign_id: int,
    campaign_update: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a campaign. GM only."""
    db_campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not db_campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with id {campaign_id} not found",
        )

    # Check if current user is the GM
    if not can_edit_campaign(current_user, db_campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the GM can update this campaign",
        )

    # Update only provided fields
    update_data = campaign_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_campaign, field, value)

    db.commit()
    db.refresh(db_campaign)
    return db_campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a campaign. GM only."""
    db_campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not db_campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with id {campaign_id} not found",
        )

    # Check if current user is the GM
    if not can_edit_campaign(current_user, db_campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the GM can delete this campaign",
        )

    db.delete(db_campaign)
    db.commit()
    return None


@router.post("/join", response_model=CampaignSchema)
async def join_campaign(
    campaign_join: CampaignJoin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Join a campaign using an invite code."""
    campaign = (
        db.query(Campaign)
        .filter(Campaign.invite_code == campaign_join.invite_code)
        .first()
    )
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite code"
        )

    # Check if user is already in campaign
    if current_user in campaign.players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this campaign",
        )

    # Check if user is the GM
    if campaign.gm_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are the GM of this campaign",
        )

    # Add user to campaign players
    campaign.players.append(current_user)
    db.commit()
    db.refresh(campaign)

    return campaign
