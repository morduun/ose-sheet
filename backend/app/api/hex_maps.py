"""API endpoints for hex map management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Campaign
from app.models.hex_map import HexMap, HexCell
from app.schemas.hex_map import (
    HexMapCreate,
    HexMapUpdate,
    HexMapSummary,
    HexMapResponse,
    HexMapPlayerResponse,
    HexCellCreate,
    HexCellUpdate,
    HexCellResponse,
    HexCellPlayerResponse,
    HexCellBatchRequest,
    PartyMoveRequest,
)
from app.services.permissions import can_view_campaign, is_campaign_gm


router = APIRouter()


def _get_campaign_or_404(db: Session, campaign_id: int) -> Campaign:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")
    return campaign


def _check_view(user: User, campaign: Campaign):
    if not can_view_campaign(user, campaign):
        raise HTTPException(status_code=403, detail="Not a member of this campaign")


def _check_gm(user: User, campaign: Campaign):
    if not is_campaign_gm(user, campaign):
        raise HTTPException(status_code=403, detail="Only the GM can manage hex maps")


def _get_map_or_404(db: Session, campaign_id: int, map_id: int) -> HexMap:
    hex_map = db.query(HexMap).filter(
        HexMap.id == map_id, HexMap.campaign_id == campaign_id
    ).first()
    if not hex_map:
        raise HTTPException(status_code=404, detail="Hex map not found")
    return hex_map


# --- Map CRUD ---

@router.get("/", response_model=list[HexMapSummary])
async def list_hex_maps(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all hex maps in a campaign."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_view(current_user, campaign)

    maps = db.query(HexMap).filter(HexMap.campaign_id == campaign_id).order_by(HexMap.name).all()
    result = []
    for m in maps:
        cell_count = db.query(HexCell).filter(HexCell.hex_map_id == m.id).count()
        result.append(HexMapSummary(
            id=m.id,
            campaign_id=m.campaign_id,
            name=m.name,
            width=m.width,
            height=m.height,
            hex_size_miles=m.hex_size_miles,
            party_col=m.party_col,
            party_row=m.party_row,
            cell_count=cell_count,
        ))
    return result


@router.post("/", response_model=HexMapResponse, status_code=status.HTTP_201_CREATED)
async def create_hex_map(
    campaign_id: int,
    req: HexMapCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new hex map."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    hex_map = HexMap(
        campaign_id=campaign_id,
        name=req.name,
        width=req.width,
        height=req.height,
        hex_size_miles=req.hex_size_miles,
    )
    db.add(hex_map)
    db.commit()
    db.refresh(hex_map)
    return hex_map


@router.get("/{map_id}", response_model=HexMapResponse)
async def get_hex_map(
    campaign_id: int,
    map_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a hex map with all cells (GM view)."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)
    return _get_map_or_404(db, campaign_id, map_id)


@router.get("/{map_id}/player", response_model=HexMapPlayerResponse)
async def get_hex_map_player(
    campaign_id: int,
    map_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get hex map player view — only visited cells, no GM notes."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_view(current_user, campaign)

    hex_map = _get_map_or_404(db, campaign_id, map_id)
    visited_cells = [c for c in hex_map.cells if c.visited]

    return HexMapPlayerResponse(
        id=hex_map.id,
        campaign_id=hex_map.campaign_id,
        name=hex_map.name,
        width=hex_map.width,
        height=hex_map.height,
        hex_size_miles=hex_map.hex_size_miles,
        party_col=hex_map.party_col,
        party_row=hex_map.party_row,
        cells=[HexCellPlayerResponse(
            id=c.id,
            hex_map_id=c.hex_map_id,
            col=c.col,
            row=c.row,
            terrain_type=c.terrain_type,
            name=c.name,
            description=c.description,
            pois=c.pois or [],
        ) for c in visited_cells],
    )


@router.patch("/{map_id}", response_model=HexMapResponse)
async def update_hex_map(
    campaign_id: int,
    map_id: int,
    req: HexMapUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update hex map metadata."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    hex_map = _get_map_or_404(db, campaign_id, map_id)

    if req.name is not None:
        hex_map.name = req.name
    if req.width is not None:
        hex_map.width = req.width
    if req.height is not None:
        hex_map.height = req.height
    if req.hex_size_miles is not None:
        hex_map.hex_size_miles = req.hex_size_miles

    db.commit()
    db.refresh(hex_map)
    return hex_map


@router.delete("/{map_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hex_map(
    campaign_id: int,
    map_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a hex map and all its cells."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    hex_map = _get_map_or_404(db, campaign_id, map_id)
    db.delete(hex_map)
    db.commit()


# --- Cell operations ---

@router.post("/{map_id}/cells", response_model=HexCellResponse, status_code=status.HTTP_201_CREATED)
async def create_cell(
    campaign_id: int,
    map_id: int,
    req: HexCellCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a single hex cell."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    hex_map = _get_map_or_404(db, campaign_id, map_id)

    if req.col < 0 or req.col >= hex_map.width or req.row < 0 or req.row >= hex_map.height:
        raise HTTPException(status_code=400, detail="Cell coordinates out of bounds")

    existing = db.query(HexCell).filter(
        HexCell.hex_map_id == map_id, HexCell.col == req.col, HexCell.row == req.row
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Cell already exists at this position")

    cell = HexCell(
        hex_map_id=map_id,
        col=req.col,
        row=req.row,
        terrain_type=req.terrain_type,
        name=req.name,
        description=req.description,
        notes=req.notes,
        pois=[p.model_dump() for p in req.pois] if req.pois else [],
        visited=req.visited,
    )
    db.add(cell)
    db.commit()
    db.refresh(cell)
    return cell


@router.put("/{map_id}/cells/batch", response_model=list[HexCellResponse])
async def batch_upsert_cells(
    campaign_id: int,
    map_id: int,
    req: HexCellBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch upsert cells — create or update by (col, row) coordinates."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    hex_map = _get_map_or_404(db, campaign_id, map_id)

    # Load existing cells into a lookup
    existing = db.query(HexCell).filter(HexCell.hex_map_id == map_id).all()
    cell_lookup = {(c.col, c.row): c for c in existing}

    results = []
    for entry in req.cells:
        if entry.col < 0 or entry.col >= hex_map.width or entry.row < 0 or entry.row >= hex_map.height:
            continue  # skip out-of-bounds silently

        cell = cell_lookup.get((entry.col, entry.row))
        if cell:
            # Update existing
            cell.terrain_type = entry.terrain_type
            if entry.name is not None:
                cell.name = entry.name
            if entry.description is not None:
                cell.description = entry.description
            if entry.notes is not None:
                cell.notes = entry.notes
            if entry.pois is not None:
                from sqlalchemy.orm.attributes import flag_modified
                cell.pois = [p.model_dump() for p in entry.pois]
                flag_modified(cell, "pois")
            if entry.visited is not None:
                cell.visited = entry.visited
        else:
            # Create new
            cell = HexCell(
                hex_map_id=map_id,
                col=entry.col,
                row=entry.row,
                terrain_type=entry.terrain_type,
                name=entry.name,
                description=entry.description,
                notes=entry.notes,
                pois=[p.model_dump() for p in entry.pois] if entry.pois else [],
                visited=entry.visited or False,
            )
            db.add(cell)
            cell_lookup[(entry.col, entry.row)] = cell

        results.append(cell)

    db.commit()
    for c in results:
        db.refresh(c)
    return results


@router.patch("/{map_id}/cells/{cell_id}", response_model=HexCellResponse)
async def update_cell(
    campaign_id: int,
    map_id: int,
    cell_id: int,
    req: HexCellUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a single hex cell."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)
    _get_map_or_404(db, campaign_id, map_id)

    cell = db.query(HexCell).filter(
        HexCell.id == cell_id, HexCell.hex_map_id == map_id
    ).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")

    if req.terrain_type is not None:
        cell.terrain_type = req.terrain_type
    if req.name is not None:
        cell.name = req.name
    if req.description is not None:
        cell.description = req.description
    if req.notes is not None:
        cell.notes = req.notes
    if req.pois is not None:
        from sqlalchemy.orm.attributes import flag_modified
        cell.pois = [p.model_dump() for p in req.pois]
        flag_modified(cell, "pois")
    if req.visited is not None:
        cell.visited = req.visited

    db.commit()
    db.refresh(cell)
    return cell


@router.delete("/{map_id}/cells/{cell_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cell(
    campaign_id: int,
    map_id: int,
    cell_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a hex cell (clear it from the map)."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)
    _get_map_or_404(db, campaign_id, map_id)

    cell = db.query(HexCell).filter(
        HexCell.id == cell_id, HexCell.hex_map_id == map_id
    ).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")

    db.delete(cell)
    db.commit()


# --- Party position ---

@router.post("/{map_id}/party", response_model=HexMapResponse)
async def move_party(
    campaign_id: int,
    map_id: int,
    req: PartyMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move party token to a hex. Automatically marks the hex as visited."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    hex_map = _get_map_or_404(db, campaign_id, map_id)

    if req.col < 0 or req.col >= hex_map.width or req.row < 0 or req.row >= hex_map.height:
        raise HTTPException(status_code=400, detail="Coordinates out of bounds")

    hex_map.party_col = req.col
    hex_map.party_row = req.row

    # Auto-visit the destination cell if it exists
    cell = db.query(HexCell).filter(
        HexCell.hex_map_id == map_id, HexCell.col == req.col, HexCell.row == req.row
    ).first()
    if cell and not cell.visited:
        cell.visited = True

    db.commit()
    db.refresh(hex_map)
    return hex_map


# --- Visibility ---

@router.post("/{map_id}/cells/{cell_id}/visit", response_model=HexCellResponse)
async def toggle_cell_visited(
    campaign_id: int,
    map_id: int,
    cell_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle a cell's visited state."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)
    _get_map_or_404(db, campaign_id, map_id)

    cell = db.query(HexCell).filter(
        HexCell.id == cell_id, HexCell.hex_map_id == map_id
    ).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")

    cell.visited = not cell.visited
    db.commit()
    db.refresh(cell)
    return cell
