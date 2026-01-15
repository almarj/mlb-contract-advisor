"""
Contract database API endpoints.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
import math

from app.models.database import get_db, Contract
from app.models.schemas import ContractListResponse, ContractRecord

router = APIRouter(prefix="/contracts", tags=["Contracts"])


@router.get("", response_model=ContractListResponse)
async def list_contracts(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    position: Optional[str] = Query(None, description="Filter by position"),
    year_min: Optional[int] = Query(None, description="Minimum year signed"),
    year_max: Optional[int] = Query(None, description="Maximum year signed"),
    team: Optional[str] = Query(None, description="Filter by team"),
    sort_by: str = Query("aav", description="Sort field: aav, year, name, length"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    search: Optional[str] = Query(None, description="Search by player name"),
    db: Session = Depends(get_db)
):
    """
    Search and filter historical contracts.

    Features:
    - Pagination (20 per page default)
    - Filter by position, year range, team
    - Sort by AAV, year, name, length
    - Search by player name
    """
    query = db.query(Contract)

    # Apply filters
    if position:
        query = query.filter(Contract.position == position.upper())

    if year_min:
        query = query.filter(Contract.year_signed >= year_min)

    if year_max:
        query = query.filter(Contract.year_signed <= year_max)

    if search:
        query = query.filter(Contract.player_name.ilike(f"%{search}%"))

    # Get total count before pagination
    total = query.count()

    # Apply sorting
    sort_column = {
        'aav': Contract.aav,
        'year': Contract.year_signed,
        'name': Contract.player_name,
        'length': Contract.length,
    }.get(sort_by, Contract.aav)

    if sort_order.lower() == 'asc':
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Apply pagination
    offset = (page - 1) * per_page
    contracts = query.offset(offset).limit(per_page).all()

    # Calculate total pages
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    return ContractListResponse(
        contracts=[ContractRecord.model_validate(c) for c in contracts],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/{contract_id}", response_model=ContractRecord)
async def get_contract(
    contract_id: int,
    db: Session = Depends(get_db)
):
    """Get a single contract by ID."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    return ContractRecord.model_validate(contract)
