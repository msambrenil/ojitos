import os
import shutil
import uuid
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, APIRouter, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, OAuth2PasswordRequestFormStrict
from datetime import datetime, timedelta, timezone, date, time
from jose import jwt, JWTError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from passlib.context import CryptContext

from .database import (
    SaleStatusEnum,
    create_db_and_tables,
    engine,
    User,
    UserCreate,
    UserRead, UserReadWithClientProfile,
    ClientProfile,
    ClientProfileCreate,
    ClientProfileUpdate,
    MyProfileUpdate,
    Sale, SaleCreate, SaleUpdate,
    # SaleRead is defined later after SaleItemRead
    WishlistItem,
    WishlistItemCreate,
    WishlistItemRead,
    Cart,
    CartItem,
    CartRead,
    CartItemCreate,
    CartItemUpdate,
    Product,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    SiteConfiguration,
    Tag, TagRead, TagCreate,
    Category, CategoryCreate, CategoryRead, CategoryReadWithProducts,
    CatalogEntry, CatalogEntryCreate, CatalogEntryUpdate, CatalogEntryApiResponse,
    GiftItem, GiftItemCreate, GiftItemUpdate, GiftItemRead,
    RedemptionRequest, RedemptionRequestCreate, RedemptionRequestRead, RedemptionRequestStatusEnum, RedemptionActionPayload, # Models for Redemption
    SaleItem, SaleItemCreate, SaleItemRead # Moved SaleItem models up for SaleRead redefinition
)

# Redefine SaleRead here as it depends on SaleItemRead and UserRead
class SaleRead(SaleBase): # SaleBase is already defined in database.py
    id: int
    user_id: int
    sale_date: datetime
    updated_at: datetime
    items: List[SaleItemRead] = [] # SaleItemRead is defined in database.py
    total_amount: float
    points_earned: int
    user: Optional[UserRead] = None # UserRead is defined in database.py


import json # For product_details_snapshot

app = FastAPI()

# --- Static Files Setup ---
os.makedirs("static/product_images", exist_ok=True)
os.makedirs("static/profile_images", exist_ok=True) # Ensure profile images dir also exists
os.makedirs("static/site_logos", exist_ok=True) # For site logo
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Dependency for DB Session ---
def get_session():
    with Session(engine) as session:
        yield session

# JWT Configuration
SECRET_KEY = "your-super-secret-key-that-should-be-in-env-var"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

class TokenData(BaseModel):
    email: Optional[str] = None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None: raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None: raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Site Configuration Initialization
def initialize_site_configuration(session: Session):
    db_config = session.get(SiteConfiguration, 1)
    if not db_config:
        print("No site configuration found, creating one with default values...")
        new_config = SiteConfiguration()
        session.add(new_config)
        try:
            session.commit()
            session.refresh(new_config)
            print("Default site configuration created successfully.")
        except Exception as e:
            session.rollback()
            print(f"Error creating default site configuration: {e}")
    else:
        print("Site configuration already exists.")

@app.on_event("startup")
def on_app_startup():
    create_db_and_tables()
    with Session(engine) as session:
        initialize_site_configuration(session)

# --- Routers ---
# (Existing routers: products_router, auth related like /token, /users/, admin_clients_router, my_profile_router, tags_router, categories_router, catalog_admin_router, catalog_public_router, gift_items_admin_router, redeem_router, sales_router, user_data_router, cart_router )
# They will be included at the end of the file.

class CardData(BaseModel): # Dashboard card data
    title: str
    value: str

@app.get("/")
async def read_root():
    return {"message": "Hello World from Showroom Natura OjitOs API"}

# Dashboard Endpoints
dashboard_router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@dashboard_router.get("/ventas-entregadas", response_model=CardData)
def get_dashboard_ventas_entregadas(session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    # Logic as previously defined
    if not current_user.is_superuser:
        count = session.exec(select(func.count(Sale.id)).where(Sale.status == SaleStatusEnum.ENTREGADO, Sale.user_id == current_user.id)).one_or_none() or 0
    else:
        count = session.exec(select(func.count(Sale.id)).where(Sale.status == SaleStatusEnum.ENTREGADO)).one_or_none() or 0
    return CardData(title="Ventas Entregadas", value=str(count))

@dashboard_router.get("/a-entregar", response_model=CardData)
def get_dashboard_a_entregar(session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    # Logic as previously defined
    if not current_user.is_superuser:
        count = session.exec(select(func.count(Sale.id)).where(
            or_(Sale.status == SaleStatusEnum.ARMADO, Sale.status == SaleStatusEnum.EN_CAMINO),
            Sale.user_id == current_user.id
        )).one_or_none() or 0
    else:
        count = session.exec(select(func.count(Sale.id)).where(
            or_(Sale.status == SaleStatusEnum.ARMADO, Sale.status == SaleStatusEnum.EN_CAMINO)
        )).one_or_none() or 0
    return CardData(title="A Entregar", value=str(count))

@dashboard_router.get("/por-armar", response_model=CardData)
def get_dashboard_por_armar(session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    # Logic as previously defined
    if not current_user.is_superuser:
        count = session.exec(select(func.count(Sale.id)).where(
            Sale.status == SaleStatusEnum.PENDIENTE_PREPARACION,
            Sale.user_id == current_user.id
        )).one_or_none() or 0
    else:
        count = session.exec(select(func.count(Sale.id)).where(Sale.status == SaleStatusEnum.PENDIENTE_PREPARACION)).one_or_none() or 0
    return CardData(title="Por Armar", value=str(count))

@dashboard_router.get("/cobradas", response_model=CardData)
def get_dashboard_cobradas(session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    # Logic as previously defined
    if not current_user.is_superuser:
        total = session.exec(select(func.sum(Sale.total_amount)).where(
            Sale.status == SaleStatusEnum.COBRADO,
            Sale.user_id == current_user.id
        )).one_or_none() or 0.0
    else:
        total = session.exec(select(func.sum(Sale.total_amount)).where(Sale.status == SaleStatusEnum.COBRADO)).one_or_none() or 0.0
    return CardData(title="Cobradas", value=f"S/. {total:.2f}")

@dashboard_router.get("/a-cobrar", response_model=CardData)
def get_dashboard_a_cobrar(session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    # Logic as previously defined
    if not current_user.is_superuser:
        total = session.exec(select(func.sum(Sale.total_amount)).where(
            Sale.status == SaleStatusEnum.ENTREGADO,
            Sale.user_id == current_user.id
        )).one_or_none() or 0.0
    else:
        total = session.exec(select(func.sum(Sale.total_amount)).where(
            Sale.status == SaleStatusEnum.ENTREGADO
        )).one_or_none() or 0.0
    return CardData(title="A Cobrar", value=f"S/. {total:.2f}")

app.include_router(dashboard_router)


# --- Admin Redemption Requests Router ---
redemption_admin_router = APIRouter(
    prefix="/api/admin/redemption-requests",
    tags=["Admin - Redemption Requests"],
    dependencies=[Depends(get_current_active_user)]
)

@redemption_admin_router.get("/", response_model=List[RedemptionRequestRead])
def list_redemption_requests_admin(
    skip: int = 0,
    limit: int = 100,
    user_id_filter: Optional[int] = None,
    status_filter: Optional[RedemptionRequestStatusEnum] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    query = (
        select(RedemptionRequest)
        .options(
            selectinload(RedemptionRequest.user).selectinload(User.client_profile),
            selectinload(RedemptionRequest.gift_item).selectinload(GiftItem.product)
        )
    )
    if user_id_filter is not None:
        query = query.where(RedemptionRequest.user_id == user_id_filter)
    if status_filter is not None:
        query = query.where(RedemptionRequest.status == status_filter)
    if date_from is not None:
        query = query.where(RedemptionRequest.requested_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        query = query.where(RedemptionRequest.requested_at <= datetime.combine(date_to, time.max))
    query = query.order_by(RedemptionRequest.requested_at.desc(), RedemptionRequest.id.desc()).offset(skip).limit(limit)
    redemption_requests = session.exec(query).all()
    return redemption_requests

@redemption_admin_router.get("/{request_id}", response_model=RedemptionRequestRead)
def read_single_redemption_request_admin(
    request_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    query = (
        select(RedemptionRequest)
        .where(RedemptionRequest.id == request_id)
        .options(
            selectinload(RedemptionRequest.user).selectinload(User.client_profile),
            selectinload(RedemptionRequest.gift_item).selectinload(GiftItem.product)
        )
    )
    db_redemption_request = session.exec(query).first()
    if not db_redemption_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redemption request not found")
    return db_redemption_request

@redemption_admin_router.post("/{request_id}/approve", response_model=RedemptionRequestRead)
def approve_redemption_request_admin(
    request_id: int,
    payload: Optional[RedemptionActionPayload] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    db_request = session.exec(
        select(RedemptionRequest)
        .where(RedemptionRequest.id == request_id)
        .options(
            selectinload(RedemptionRequest.user).selectinload(User.client_profile),
            selectinload(RedemptionRequest.gift_item).selectinload(GiftItem.product) # Eager load product on gift_item
        )
    ).first()

    if not db_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redemption request not found")
    if db_request.status != RedemptionRequestStatusEnum.PENDIENTE_APROBACION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Redemption request is not pending approval. Current status: {db_request.status.value}"
        )
    if not db_request.user or not db_request.user.client_profile:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User or client profile not found for this request.")
    if not db_request.gift_item:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gift item details not found for this request.")
    if not db_request.gift_item.product: # Check if product is loaded on gift_item
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Product details for gift item not found.")


    client_profile = db_request.user.client_profile
    gift_item_to_redeem = db_request.gift_item

    rejection_reason = None
    if not gift_item_to_redeem.is_active_as_gift:
        rejection_reason = "El regalo ya no está activo."
    elif gift_item_to_redeem.stock_available_for_redeem <= 0:
        rejection_reason = "Stock de regalo agotado al momento de la aprobación."
    elif client_profile.available_points < db_request.points_at_request:
        rejection_reason = "Puntos insuficientes en la cuenta del cliente al momento de la aprobación."

    if rejection_reason:
        db_request.status = RedemptionRequestStatusEnum.RECHAZADO
        db_request.admin_notes = f"Rechazado automáticamente: {rejection_reason} {payload.admin_notes if payload and payload.admin_notes else ''}".strip()
        db_request.updated_at = datetime.now(timezone.utc)
        session.add(db_request)
        session.commit()
        session.refresh(db_request)
        # No need to refresh relations that were already eager loaded for this path
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=rejection_reason)

    client_profile.available_points -= db_request.points_at_request
    gift_item_to_redeem.stock_available_for_redeem -= 1

    db_request.status = RedemptionRequestStatusEnum.APROBADO_POR_ENTREGAR
    if payload and payload.admin_notes:
        db_request.admin_notes = payload.admin_notes
    db_request.updated_at = datetime.now(timezone.utc)
    gift_item_to_redeem.updated_at = datetime.now(timezone.utc)

    session.add(client_profile)
    session.add(gift_item_to_redeem)
    session.add(db_request)
    try:
        session.commit()
        session.refresh(db_request) # db_request needs refresh for new status & notes
        session.refresh(client_profile)
        session.refresh(gift_item_to_redeem)
        # Eager loaded relations (user, gift_item.product) are already on db_request for the response
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error approving redemption request: {str(e)}")
    return db_request

@redemption_admin_router.post("/{request_id}/reject", response_model=RedemptionRequestRead)
def reject_redemption_request_admin(
    request_id: int,
    payload: Optional[RedemptionActionPayload] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    db_request = session.exec(
        select(RedemptionRequest)
        .where(RedemptionRequest.id == request_id)
        .options(
            selectinload(RedemptionRequest.user).selectinload(User.client_profile),
            selectinload(RedemptionRequest.gift_item).selectinload(GiftItem.product)
        )
    ).first()
    if not db_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redemption request not found")
    if db_request.status != RedemptionRequestStatusEnum.PENDIENTE_APROBACION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Redemption request can only be rejected if currently pending approval. Current status: {db_request.status.value}"
        )
    db_request.status = RedemptionRequestStatusEnum.RECHAZADO
    if payload and payload.admin_notes is not None:
        db_request.admin_notes = payload.admin_notes
    db_request.updated_at = datetime.now(timezone.utc)
    session.add(db_request)
    try:
        session.commit()
        session.refresh(db_request)
        # Eager loaded relations are already on db_request for the response
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error rejecting redemption request: {str(e)}")
    return db_request # Corrected return variable

@redemption_admin_router.post("/{request_id}/deliver", response_model=RedemptionRequestRead)
def mark_redemption_request_delivered_admin(
    request_id: int,
    payload: Optional[RedemptionActionPayload] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    db_request = session.exec(
        select(RedemptionRequest)
        .where(RedemptionRequest.id == request_id)
        .options(
            selectinload(RedemptionRequest.user).selectinload(User.client_profile),
            selectinload(RedemptionRequest.gift_item).selectinload(GiftItem.product)
        )
    ).first()
    if not db_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redemption request not found")
    if db_request.status != RedemptionRequestStatusEnum.APROBADO_POR_ENTREGAR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Redemption request must be in 'aprobado_por_entregar' state to be marked delivered. Current status: {db_request.status.value}"
        )
    db_request.status = RedemptionRequestStatusEnum.ENTREGADO
    if payload and payload.admin_notes is not None:
        db_request.admin_notes = payload.admin_notes
    db_request.updated_at = datetime.now(timezone.utc)
    session.add(db_request)
    try:
        session.commit()
        session.refresh(db_request)
        # Eager loaded relations are already on db_request for the response
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error marking redemption request as delivered: {str(e)}")
    return db_request

# Include all routers. Order might matter if prefixes overlap, but here they are distinct.
# (Existing router includes...)
# app.include_router(products_router)
# app.include_router(other_auth_router) # Assuming /token, /users/ are on their own router or app directly
# app.include_router(admin_clients_router)
# app.include_router(my_profile_router)
# app.include_router(tags_router)
# app.include_router(categories_router)
# app.include_router(catalog_admin_router)
# app.include_router(catalog_public_router)
# app.include_router(gift_items_admin_router)
# app.include_router(redeem_router) # Client-facing redeem router
# app.include_router(sales_router)
# app.include_router(user_data_router)
# app.include_router(cart_router)
# app.include_router(redemption_admin_router) # Add the new admin router for redemptions


# --- Authentication Routes (copied from existing, assuming placement) ---
class Token(BaseModel):
    access_token: str
    token_type: str

@app.post("/token", response_model=Token, tags=["Authentication"])
async def login_for_access_token_endpoint(
    form_data: OAuth2PasswordRequestFormStrict = Depends(),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not user.hashed_password or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=UserReadWithClientProfile, tags=["Users"], status_code=status.HTTP_201_CREATED)
def create_user_and_profile(
    user_in: UserCreate,
    session: Session = Depends(get_session),
    current_creator: User = Depends(get_current_active_user)
):
    if not current_creator.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create users")
    existing_user = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    hashed_password = get_password_hash(user_in.password)
    user_data_for_db = user_in.model_dump(exclude={"password"})
    db_user = User(**user_data_for_db, hashed_password=hashed_password)
    db_client_profile = ClientProfile()
    db_user.client_profile = db_client_profile
    session.add(db_user)
    try:
        session.commit()
        session.refresh(db_user)
        if db_user.client_profile: session.refresh(db_user.client_profile)
        else: # Fallback, should not be needed with correct SQLModel relationship setup
            profile_check = session.exec(select(ClientProfile).where(ClientProfile.user_id == db_user.id)).first()
            if profile_check: db_user.client_profile = profile_check; session.refresh(db_user.client_profile)
    except IntegrityError: session.rollback(); raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Data conflict.")
    except Exception: session.rollback(); raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating user.")
    return db_user

# --- Sales Router (copied from existing, assuming placement) ---
sales_router = APIRouter(prefix="/api/sales", tags=["Sales"])
# (All Sale endpoints as previously defined)
# ... create_sale, read_sales, read_single_sale, update_sale_details, cancel_sale_by_admin ...
# (Ensuring the points accumulation logic within update_sale_details is preserved)
# ... (Copied full sales_router definition from previous state) ...
# [This section would contain the full existing code for sales_router endpoints]
# For brevity, I am not pasting the entire sales_router code again, but it's assumed to be here.
# Make sure the update_sale_details has the points logic from previous step.
# The important part for this tool run is the addition of redemption admin router endpoints below.

# --- Include all routers ---
app.include_router(products_router)
app.include_router(admin_clients_router)
app.include_router(my_profile_router)
app.include_router(tags_router)
app.include_router(categories_router)
app.include_router(catalog_admin_router)
app.include_router(catalog_public_router)
app.include_router(gift_items_admin_router)
app.include_router(redeem_router) # Client-facing redeem router
app.include_router(sales_router) # This was missing from the previous include list, adding it now.
app.include_router(user_data_router)
app.include_router(cart_router)
app.include_router(redemption_admin_router) # The new admin router for redemptions

# Ensure all previously defined endpoints for sales_router are here
# (Example placeholder for one sales endpoint to show structure)
@sales_router.post("/", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale(sale_in: SaleCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    if current_user.is_superuser and sale_in.user_id is not None:
        target_user_id = sale_in.user_id
        target_user = session.get(User, target_user_id)
        if not target_user: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {target_user_id} not found.")
    else: target_user_id = current_user.id
    calculated_total_amount = 0.0
    db_sale_items = []
    for item_create in sale_in.items:
        product = session.get(Product, item_create.product_id)
        if not product: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with id {item_create.product_id} not found.")
        if product.stock_actual < item_create.quantity: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Not enough stock for product {product.name}.")
        price_at_sale = item_create.price_at_sale if item_create.price_at_sale is not None else product.price_feria
        if price_at_sale is None: price_at_sale = product.price_revista
        subtotal = item_create.quantity * price_at_sale
        calculated_total_amount += subtotal
        db_item = SaleItem(product_id=item_create.product_id, quantity=item_create.quantity, price_at_sale=price_at_sale, subtotal=subtotal)
        db_sale_items.append(db_item)
        product.stock_actual -= item_create.quantity
        session.add(product)
    final_total_amount = calculated_total_amount - (sale_in.discount_amount or 0.0)
    if final_total_amount < 0: final_total_amount = 0.0
    calculated_points_earned = int(final_total_amount / 10) # Example: 1 point per S/.10
    db_sale = Sale(user_id=target_user_id, status=sale_in.status or SaleStatusEnum.PENDIENTE_PREPARACION, discount_amount=sale_in.discount_amount or 0.0, total_amount=final_total_amount, points_earned=calculated_points_earned, items=db_sale_items, sale_date=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    session.add(db_sale)
    try:
        session.commit()
        session.refresh(db_sale)
        for item_in_db in db_sale.items: session.refresh(item_in_db); session.refresh(item_in_db.product)
        if db_sale.user: session.refresh(db_sale.user)
    except IntegrityError as e: session.rollback(); raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sale creation conflict.")
    except Exception as e: session.rollback(); raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating sale.")
    return db_sale

# (Assume other sales_router endpoints: read_sales, read_single_sale, update_sale_details (with points logic), cancel_sale_by_admin are here)
# The update_sale_details function from previous step with points logic should be included here in full.
# For this tool call, I will only include the structure of update_sale_details to avoid making the diff too large,
# but it's assumed the full working code from previous steps is present.
@sales_router.put("/{sale_id}", response_model=SaleRead)
def update_sale_details(sale_id: int, sale_update: SaleUpdate, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    # ... (Full implementation of update_sale_details including points accumulation logic) ...
    # This is a placeholder for the full logic that was previously implemented.
    # The actual overwrite will use the full file content with this part correctly filled.
    # For now, just to show the structure for the diff tool.
    db_sale = session.get(Sale, sale_id)
    if not db_sale: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")
    # ... (rest of the logic for update_sale_details) ...
    return db_sale # Placeholder return, actual logic returns the full db_sale


# The rest of the main.py content (like other routers and their includes) would follow.
# This overwrite is primarily focused on adding the redemption admin endpoints correctly.
# The sales_router and other routers are assumed to be correctly defined elsewhere in this overwrite block.
# For the tool, I will provide the full content with the new endpoints inserted.
# The placeholder for sales_router.put needs to be replaced with the actual full code.
# Since the tool output for read_files provides the full current state, I can use that.
# The following is the complete file with the new endpoints for redemption_admin_router added.
# The previous `read_files` output will be the base.
# I will manually reconstruct the file with the new endpoints in the correct place.

# (The full file content with new endpoints will be provided in the overwrite_file_with_block)
# The key is to insert the new endpoints for redemption_admin_router after its GET / and GET /{id}
# and ensure all other existing code remains.
# The `RedemptionActionPayload` import is also confirmed to be added.
# The correction for the return variable in the reject endpoint will be made.
# The `datetime`, `timezone` imports are present. `status` is present. `selectinload` is present.
# All necessary models are imported.

# The `update_sale_details` function will be copied from the previous state to ensure its full logic is preserved.
# The previous read_files output (from the previous turn) is the source of truth for existing code.

# I will now construct the full file content for the overwrite.
# The new code for GET /{id} and POST /{id}/approve for redemption_admin_router will be added.
# The code for POST /{id}/reject for redemption_admin_router will be added, with corrected return.
# The code for POST /{id}/deliver for redemption_admin_router will be added.
# The `RedemptionActionPayload` import will be ensured.
# All other code from the `read_files` output will be maintained.
# The `app.include_router(redemption_admin_router)` will be added at the end.
# The placeholder for `update_sale_details` in this thought block is NOT what will be written.
# I will use the content from the previous `read_files` to ensure the full, correct version is there.
# This is a complex overwrite; precision is key.
# The main logic is to insert the new endpoints into the existing redemption_admin_router.
# I will use the structure from the previous `read_files` output and carefully insert the new functions.
# The `RedemptionActionPayload` should be imported from `.database`.
# The `sales_router.put` placeholder above is just for my thought process to remember to include it.
# The actual content for overwrite will be the *full current file* plus the new endpoints.
# The `read_files` output is the base, and I'm adding to it.
# The `sales_router` was already included.
# The `RedemptionActionPayload` import was already added in the diff for the models.
# So the main task is to add the endpoint definitions to the `redemption_admin_router`.
# I will use the previous `read_files` output as the base and insert the new endpoints for clarity and safety.
# The previous diff for `approve_redemption_request_admin` was successful, so it's already in the file.
# The previous diff for `reject_redemption_request_admin` was also successful (but had a return var issue to fix).
# So, I only need to add `deliver` and fix `reject`.It appears there was a misunderstanding in my previous thought process. The goal was to add the `GET /{request_id}` and `POST /{request_id}/approve` endpoints. However, the `approve` endpoint was already added in the immediately preceding step (subtask ID `16284074-e048-457b-97e4-6836a6f53617`). The `reject` endpoint was also added (subtask ID `b0807c3f-4858-499c-80b8-0099c83786a4`), though it had a return variable error in the diff that I noted.

The current subtask is to implement `POST /{request_id}/deliver`.

I will:
1.  Re-read `backend/main.py` to ensure I have the absolute latest version, including the correctly implemented `approve` and `reject` (with its return variable error) endpoints.
2.  Correct the return variable in the `reject_redemption_request_admin` function.
3.  Add the new `mark_redemption_request_delivered_admin` function for the `POST /{request_id}/deliver` endpoint to the `redemption_admin_router`.
4.  Ensure all necessary imports are present.
5.  Use `overwrite_file_with_block` to apply these changes.
