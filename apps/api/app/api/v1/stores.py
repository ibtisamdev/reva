"""Store CRUD and settings API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select

from app.core.deps import (
    CurrentUser,
    DBSession,
    get_store_by_id,
    get_store_for_user,
    get_user_organization_id,
)
from app.models.store import Store
from app.schemas.store import (
    DEFAULT_WIDGET_SETTINGS,
    StoreCreate,
    StoreListResponse,
    StoreResponse,
    StoreSettingsResponse,
    StoreSettingsUpdate,
    StoreUpdate,
    WidgetSettings,
)

router = APIRouter()


# === Store CRUD Endpoints ===


@router.get(
    "",
    response_model=StoreListResponse,
    summary="List stores",
    description="List all stores for the authenticated user's organization.",
)
async def list_stores(
    user: CurrentUser,
    db: DBSession,
) -> StoreListResponse:
    """List all stores for the user's organization."""
    org_id = get_user_organization_id(user)

    # Get stores for the organization
    query = select(Store).where(
        Store.organization_id == org_id,
    ).order_by(Store.created_at.desc())

    result = await db.execute(query)
    stores = list(result.scalars().all())

    return StoreListResponse(
        items=[StoreResponse.model_validate(store) for store in stores],
        total=len(stores),
    )


@router.post(
    "",
    response_model=StoreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create store",
    description="Create a new store for the authenticated user's organization.",
)
async def create_store(
    data: StoreCreate,
    user: CurrentUser,
    db: DBSession,
) -> StoreResponse:
    """Create a new store."""
    org_id = get_user_organization_id(user)

    store = Store(
        organization_id=org_id,
        name=data.name,
        email=data.email,
    )
    db.add(store)
    await db.commit()
    await db.refresh(store)

    return StoreResponse.model_validate(store)


@router.get(
    "/{store_id}",
    response_model=StoreResponse,
    summary="Get store",
    description="Get a specific store by ID.",
)
async def get_store(
    store_id: UUID,
    user: CurrentUser,
    db: DBSession,
) -> StoreResponse:
    """Get a store by ID."""
    store = await get_store_for_user(store_id, user, db)
    return StoreResponse.model_validate(store)


@router.patch(
    "/{store_id}",
    response_model=StoreResponse,
    summary="Update store",
    description="Update a store's details.",
)
async def update_store(
    store_id: UUID,
    data: StoreUpdate,
    user: CurrentUser,
    db: DBSession,
) -> StoreResponse:
    """Update a store."""
    store = await get_store_for_user(store_id, user, db)

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(store, field, value)

    await db.commit()
    await db.refresh(store)

    return StoreResponse.model_validate(store)


@router.delete(
    "/{store_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete store",
    description="Delete a store (soft delete by setting is_active=False).",
)
async def delete_store(
    store_id: UUID,
    user: CurrentUser,
    db: DBSession,
) -> None:
    """Delete a store (soft delete)."""
    store = await get_store_for_user(store_id, user, db)

    # Soft delete - set is_active to False
    store.is_active = False
    await db.commit()


# === Store Settings Endpoints ===


@router.get(
    "/settings",
    response_model=StoreSettingsResponse,
    summary="Get store settings",
    description="Get the widget and other settings for a store.",
)
async def get_store_settings(
    store: Store = Depends(get_store_by_id),
) -> StoreSettingsResponse:
    """Get store settings including widget configuration."""
    settings = store.settings or {}

    # Merge with defaults
    widget_settings = {
        **DEFAULT_WIDGET_SETTINGS.get("widget", {}),
        **settings.get("widget", {}),
    }

    return StoreSettingsResponse(
        widget=WidgetSettings(**widget_settings),
    )


@router.patch(
    "/settings",
    response_model=StoreSettingsResponse,
    summary="Update store settings",
    description="Partially update store settings. Only provided fields will be updated.",
)
async def update_store_settings(
    data: StoreSettingsUpdate,
    db: DBSession,
    store: Store = Depends(get_store_by_id),
) -> StoreSettingsResponse:
    """Update store settings."""
    current_settings = store.settings or {}

    # Update widget settings if provided
    if data.widget:
        current_widget = current_settings.get("widget", {})
        update_data = data.widget.model_dump(exclude_unset=True)
        current_widget.update(update_data)
        current_settings["widget"] = current_widget

    # Update the store
    store.settings = current_settings
    await db.commit()
    await db.refresh(store)

    # Return merged settings
    widget_settings = {
        **DEFAULT_WIDGET_SETTINGS.get("widget", {}),
        **current_settings.get("widget", {}),
    }

    return StoreSettingsResponse(
        widget=WidgetSettings(**widget_settings),
    )
