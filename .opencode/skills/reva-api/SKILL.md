---
name: reva-api
description: FastAPI patterns and conventions for the Reva backend
---

# Reva API Patterns

Guide for implementing FastAPI endpoints following Reva project conventions.

## Project Structure

```
apps/api/app/
├── api/v1/
│   ├── endpoints/         # Route handlers
│   │   ├── auth.py
│   │   ├── conversations.py
│   │   └── products.py
│   └── __init__.py        # Router aggregation
├── core/
│   ├── config.py          # Settings (Pydantic)
│   ├── database.py        # Async SQLAlchemy setup
│   ├── dependencies.py    # FastAPI dependencies
│   └── security.py        # Auth utilities
├── models/                # SQLAlchemy ORM models
├── schemas/               # Pydantic schemas
├── services/              # Business logic
└── main.py               # FastAPI app
```

## Creating a New Endpoint

### 1. Define Pydantic Schemas

```python
# app/schemas/product.py
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    description: str | None = None
    price: float

class ProductCreate(ProductBase):
    shopify_id: str

class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None

class ProductResponse(ProductBase):
    id: UUID
    organization_id: UUID
    shopify_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### 2. Create Service Layer

```python
# app/services/product_service.py
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate

class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self, 
        product_id: UUID, 
        organization_id: UUID
    ) -> Product | None:
        result = await self.db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    async def list_products(
        self, 
        organization_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> list[Product]:
        result = await self.db.execute(
            select(Product)
            .where(Product.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(
        self, 
        organization_id: UUID, 
        data: ProductCreate
    ) -> Product:
        product = Product(
            organization_id=organization_id,
            **data.model_dump()
        )
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        return product
```

### 3. Create Route Handler

```python
# app/api/v1/endpoints/products.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_db, get_current_user, get_organization
from app.models.user import User
from app.models.organization import Organization
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductResponse])
async def list_products(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    organization: Organization = Depends(get_organization),
):
    """List all products for the current organization."""
    service = ProductService(db)
    products = await service.list_products(organization.id, skip, limit)
    return products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    organization: Organization = Depends(get_organization),
):
    """Get a specific product by ID."""
    service = ProductService(db)
    product = await service.get_by_id(product_id, organization.id)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    organization: Organization = Depends(get_organization),
    current_user: User = Depends(get_current_user),
):
    """Create a new product."""
    service = ProductService(db)
    product = await service.create(organization.id, data)
    return product
```

### 4. Register Router

```python
# app/api/v1/__init__.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth, conversations, products

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(conversations.router)
api_router.include_router(products.router)  # Add new router
```

## Dependencies

### Database Session

```python
# app/core/dependencies.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Current User (Clerk Auth)

```python
async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate Clerk JWT and return user."""
    token = authorization.replace("Bearer ", "")
    
    try:
        payload = verify_clerk_token(token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    clerk_user_id = payload.get("sub")
    user = await get_user_by_clerk_id(db, clerk_user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user
```

### Organization (Multi-Tenant)

```python
async def get_organization(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """Get user's current organization."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with an organization"
        )
    
    org = await get_org_by_id(db, current_user.organization_id)
    return org
```

## Error Handling

### Standard HTTP Exceptions

```python
from fastapi import HTTPException, status

# 400 - Bad Request
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Invalid request data"
)

# 401 - Unauthorized
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentication required"
)

# 403 - Forbidden
raise HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Not authorized to access this resource"
)

# 404 - Not Found
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Resource not found"
)

# 409 - Conflict
raise HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="Resource already exists"
)
```

## Multi-Tenancy

**CRITICAL**: Always scope queries by `organization_id`:

```python
# CORRECT - scoped to organization
result = await db.execute(
    select(Product).where(
        Product.id == product_id,
        Product.organization_id == organization.id  # Always include!
    )
)

# WRONG - data leak across tenants
result = await db.execute(
    select(Product).where(Product.id == product_id)  # Missing org filter!
)
```

## Testing Endpoints

```python
# tests/api/v1/test_products.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_list_products(
    client: AsyncClient,
    auth_headers: dict,
    test_organization: Organization,
):
    response = await client.get(
        "/api/v1/products",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_product(
    client: AsyncClient,
    auth_headers: dict,
):
    response = await client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={
            "name": "Test Product",
            "price": 29.99,
            "shopify_id": "gid://shopify/Product/123"
        }
    )
    
    assert response.status_code == 201
    assert response.json()["name"] == "Test Product"
```
