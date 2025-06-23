import os
import shutil
import uuid
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, APIRouter, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestFormStrict
from datetime import datetime, timedelta, timezone, date, time
from jose import jwt, JWTError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from passlib.context import CryptContext

# Assuming models are in database.py.
from .database import (
    create_db_and_tables,
    engine,
    User,
    UserCreate,
    UserRead, UserReadWithClientProfile,
    ClientProfile,
    ClientProfileCreate,
    ClientProfileUpdate,
    MyProfileUpdate,
    Sale, SaleCreate, SaleUpdate, SaleBase,
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
    SiteConfiguration, #SiteConfigurationUpdate, SiteConfigurationRead,
    Tag, TagRead, TagCreate,
    Category, CategoryCreate, CategoryRead, CategoryReadWithProducts,
    CatalogEntry, CatalogEntryCreate, CatalogEntryUpdate, CatalogEntryApiResponse,
    GiftItem, GiftItemCreate, GiftItemUpdate, GiftItemRead,
    RedemptionRequest, RedemptionRequestCreate, RedemptionRequestRead, RedemptionRequestStatusEnum, RedemptionActionPayload,
    SaleItem, SaleItemCreate, SaleItemRead,
    SaleStatusEnum
)

# Redefine SaleRead here as it depends on SaleItemRead and UserRead
class SaleRead(SaleBase):
    id: int
    user_id: int
    sale_date: datetime
    updated_at: datetime
    items: List[SaleItemRead] = []
    total_amount: float
    points_earned: int
    user: Optional[UserRead] = None

import json # For product_details_snapshot

app = FastAPI()

# --- Static Files Setup ---
# Ensure these directories are relative to where main.py is if running directly,
# or adjust if running from a parent directory.
# If running `uvicorn backend.main:app` from parent of `backend/`,
# these paths should be "backend/static/..." or StaticFiles(directory="backend/static")
os.makedirs("static/product_images", exist_ok=True)
os.makedirs("static/profile_images", exist_ok=True)
os.makedirs("static/site_logos", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Dependency for DB Session ---
def get_session():
    with Session(engine) as session:
        yield session

# --- Authentication Helpers ---
SECRET_KEY = "your-super-secret-key-that-should-be-in-env-var" # TODO: Move to env var
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

async def get_current_active_superuser(current_user: User = Depends(get_current_active_user)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return current_user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# --- App Event Handlers ---
def initialize_site_configuration(session: Session): # Renamed from _initialize_site_configuration
    db_config = session.get(SiteConfiguration, 1)
    if not db_config:
        print("No site configuration found, creating one with default values...")
        new_config = SiteConfiguration() # Uses defaults from model
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

def create_default_admin_if_none(session: Session): # Renamed from _create_default_admin_if_none
    existing_superuser = session.exec(select(User).where(User.is_superuser == True)).first()
    if not existing_superuser:
        print("INFO:     No superuser found. Creating default admin user...")
        DEFAULT_ADMIN_EMAIL = "admin@example.com"
        DEFAULT_ADMIN_PASSWORD = "adminpass" # TODO: Make this more secure or configurable via env
        hashed_password = get_password_hash(DEFAULT_ADMIN_PASSWORD)
        default_admin_user = User(
            email=DEFAULT_ADMIN_EMAIL,
            full_name="Administrador Principal",
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=True,
            is_seller=False
        )
        default_admin_client_profile = ClientProfile() # Create a default client profile
        default_admin_user.client_profile = default_admin_client_profile
        session.add(default_admin_user)
        try:
            session.commit()
            session.refresh(default_admin_user)
            if default_admin_user.client_profile: session.refresh(default_admin_user.client_profile)
            print("INFO:     Default admin user created successfully.")
            print(f"INFO:     Admin Email: {DEFAULT_ADMIN_EMAIL}")
            print(f"INFO:     Admin Password: {DEFAULT_ADMIN_PASSWORD} (Change this in a production environment!)")
        except Exception as e:
            session.rollback()
            print(f"ERROR:    Failed to create default admin user: {e}")
    else:
        print("INFO:     Superuser already exists. Default admin creation skipped.")

@app.on_event("startup")
def on_app_startup():
    create_db_and_tables()
    with Session(engine) as session:
        initialize_site_configuration(session)
        create_default_admin_if_none(session)

# --- Root Endpoint ---
@app.get("/")
async def read_root():
    return {"message": "Hello World from Showroom Natura OjitOs API"}

# --- Authentication Endpoint ---
class Token(BaseModel):
    access_token: str
    token_type: str

@app.post("/token", response_model=Token, tags=["Authentication"])
async def login_for_access_token_endpoint(form_data: OAuth2PasswordRequestFormStrict = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not user.hashed_password or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# --- User Creation (Admin only) ---
@app.post("/users/", response_model=UserReadWithClientProfile, tags=["Users"], status_code=status.HTTP_201_CREATED)
def create_user_and_profile(user_in: UserCreate, session: Session = Depends(get_session), current_creator: User = Depends(get_current_active_superuser)):
    existing_user = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    hashed_password = get_password_hash(user_in.password)
    user_data_for_db = user_in.model_dump(exclude={"password"})
    db_user = User(**user_data_for_db, hashed_password=hashed_password)
    db_client_profile = ClientProfile() # Create an empty client profile
    db_user.client_profile = db_client_profile
    session.add(db_user)
    try:
        session.commit()
        session.refresh(db_user)
        if db_user.client_profile: session.refresh(db_user.client_profile)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Data conflict, possibly duplicate user or profile issue.")
    except Exception:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating user.")
    return db_user

# --- Dashboard Router ---
dashboard_router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
class CardData(BaseModel): # Specific to dashboard response
    title: str
    value: str

@dashboard_router.get("/ventas-entregadas", response_model=CardData)
def get_dashboard_ventas_entregadas(session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    if not current_user.is_superuser:
        count = session.exec(select(func.count(Sale.id)).where(Sale.status == SaleStatusEnum.ENTREGADO, Sale.user_id == current_user.id)).one_or_none() or 0
    else:
        count = session.exec(select(func.count(Sale.id)).where(Sale.status == SaleStatusEnum.ENTREGADO)).one_or_none() or 0
    return CardData(title="Ventas Entregadas", value=str(count))

@dashboard_router.get("/a-entregar", response_model=CardData)
def get_dashboard_a_entregar(session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
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
    if not current_user.is_superuser:
        total = session.exec(select(func.sum(Sale.total_amount)).where(
            Sale.status == SaleStatusEnum.ENTREGADO, # A cobrar las que ya se entregaron pero no se marcaron como cobradas
            Sale.user_id == current_user.id
        )).one_or_none() or 0.0
    else:
        total = session.exec(select(func.sum(Sale.total_amount)).where(
            Sale.status == SaleStatusEnum.ENTREGADO
        )).one_or_none() or 0.0
    return CardData(title="A Cobrar", value=f"S/. {total:.2f}")

# --- Products Router ---
products_router = APIRouter(prefix="/api/products", tags=["Products"])

@products_router.post("/", response_model=ProductRead)
async def create_product_endpoint(product_in: ProductCreate = Depends(), image: Optional[UploadFile] = File(None), session: Session = Depends(get_session), current_user: User = Depends(get_current_active_superuser)):
    image_url_for_db = None
    if image:
        if image.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file type.")
        filename = f"{uuid.uuid4()}_{image.filename.replace('..', '')}" # Basic sanitization
        file_path = os.path.join("static/product_images", filename)
        with open(file_path, "wb") as buffer: shutil.copyfileobj(image.file, buffer)
        image_url_for_db = f"/static/product_images/{filename}" # Use relative path for URL

    db_product_args = product_in.model_dump(exclude={"tag_names", "category_id"}) # Exclude fields handled separately

    validated_category_id: Optional[int] = None
    if product_in.category_id is not None:
        category = session.get(Category, product_in.category_id)
        if not category: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Category with ID {product_in.category_id} not found.")
        validated_category_id = product_in.category_id

    db_product = Product(**db_product_args, image_url=image_url_for_db, category_id=validated_category_id)

    if product_in.tag_names:
        processed_tags = []
        for tag_name in product_in.tag_names:
            tag_name_stripped = tag_name.strip()
            if not tag_name_stripped: continue
            tag_name_lower = tag_name_stripped.lower()
            db_tag = session.exec(select(Tag).where(func.lower(Tag.name) == tag_name_lower)).first()
            if not db_tag:
                db_tag = Tag(name=tag_name_stripped)
                session.add(db_tag) # Add new tag to session
            processed_tags.append(db_tag)
        db_product.tags = processed_tags

    try:
        session.add(db_product)
        session.commit()
        session.refresh(db_product)
        if db_product.category_obj is not None: session.refresh(db_product.category_obj)
        for tag_item in db_product.tags: session.refresh(tag_item) # Refresh each tag
        return db_product
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Data integrity error: {e}")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")

@products_router.get("/", response_model=List[ProductRead])
def read_products_filtered(skip: int = 0, limit: int = 100, search_term: Optional[str] = None, category_id: Optional[int] = None, low_stock: Optional[bool] = None, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_superuser)):
    query = select(Product).options(selectinload(Product.category_obj), selectinload(Product.tags))
    if search_term:
        query = query.where(or_(Product.name.ilike(f"%{search_term}%"), Product.description.ilike(f"%{search_term}%")))
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    if low_stock is True:
        query = query.where(Product.stock_actual <= Product.stock_critico).where(Product.stock_critico > 0)
    query = query.order_by(Product.id).offset(skip).limit(limit)
    products = session.exec(query).all()
    return products

@products_router.get("/{product_id}", response_model=ProductRead)
def read_product_endpoint(product_id: int, session: Session = Depends(get_session)): # No superuser needed for public read
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    # Eager load relationships if not automatically handled by ProductRead or if needed.
    # session.refresh(product, ["tags", "category_obj"]) # May not be needed if ProductRead handles it
    return product

@products_router.put("/{product_id}", response_model=ProductRead)
async def update_product_endpoint(product_id: int, product_update_data: ProductUpdate = Depends(), image: Optional[UploadFile] = File(None), session: Session = Depends(get_session), current_user: User = Depends(get_current_active_superuser)):
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    update_data = product_update_data.model_dump(exclude_unset=True, exclude={"tag_names", "category_id"}) # Exclude fields handled separately

    if image:
        if image.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file type.")
        if db_product.image_url: # Remove old image if it exists
            old_image_path = db_product.image_url.lstrip('/') # Assuming stored as /static/...
            if os.path.exists(old_image_path): os.remove(old_image_path)

        filename = f"{uuid.uuid4()}_{image.filename.replace('..', '')}"
        file_path = os.path.join("static/product_images", filename)
        with open(file_path, "wb") as buffer: shutil.copyfileobj(image.file, buffer)
        update_data["image_url"] = f"/static/product_images/{filename}"
    elif "image_url" in product_update_data.model_fields_set and product_update_data.image_url is None: # Explicitly setting image to null
        if db_product.image_url:
            old_image_path = db_product.image_url.lstrip('/')
            if os.path.exists(old_image_path): os.remove(old_image_path)
        update_data["image_url"] = None

    if "category_id" in product_update_data.model_fields_set: # product_update_data.category_id is explicitly passed
        new_category_id = product_update_data.category_id
        if new_category_id is not None:
            category = session.get(Category, new_category_id)
            if not category: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Category with ID {new_category_id} not found.")
            db_product.category_id = new_category_id
        else: # Explicitly unsetting category
            db_product.category_id = None

    for key, value in update_data.items():
        setattr(db_product, key, value)

    if product_update_data.tag_names is not None: # Explicitly passed, even if empty list
        if not product_update_data.tag_names:
            db_product.tags.clear()
        else:
            updated_tags_list = []
            for tag_name in product_update_data.tag_names:
                tag_name_stripped = tag_name.strip()
                if not tag_name_stripped: continue
                tag_name_lower = tag_name_stripped.lower()
                db_tag = session.exec(select(Tag).where(func.lower(Tag.name) == tag_name_lower)).first()
                if not db_tag:
                    db_tag = Tag(name=tag_name_stripped)
                    session.add(db_tag)
                updated_tags_list.append(db_tag)
            db_product.tags = updated_tags_list

    try:
        session.add(db_product)
        session.commit()
        session.refresh(db_product)
        if db_product.category_id is not None and db_product.category_obj is None: session.refresh(db_product, ["category_obj"])
        elif db_product.category_id is None: db_product.category_obj = None # Ensure it's cleared if ID is None

        session.refresh(db_product, ["tags"]) # Refresh tags collection
        return db_product
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Data integrity error: {e}")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating product: {str(e)}")

@products_router.delete("/{product_id}", response_model=dict)
def delete_product_endpoint(product_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_superuser)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if product.image_url:
        image_file_path = product.image_url.lstrip('/')
        if os.path.exists(image_file_path): os.remove(image_file_path)
    session.delete(product)
    session.commit()
    return {"message": "Product deleted successfully"}

# --- Admin Client Profiles Router ---
admin_clients_router = APIRouter(prefix="/api/admin/client-profiles", tags=["Admin - Client Profiles"], dependencies=[Depends(get_current_active_superuser)])

@admin_clients_router.get("/", response_model=List[UserReadWithClientProfile])
def read_all_client_profiles_admin_filtered(skip: int = 0, limit: int = 100, search_term: Optional[str] = None, client_level: Optional[str] = None, is_active: Optional[bool] = None, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_superuser)):
    query = select(User).options(selectinload(User.client_profile)) # Eager load client_profile
    if search_term:
        # Ensure ClientProfile is joined to filter on its fields
        query = query.join(ClientProfile, User.id == ClientProfile.user_id, isouter=True).where(
            or_(
                User.full_name.ilike(f"%{search_term}%"),
                User.email.ilike(f"%{search_term}%"),
                ClientProfile.nickname.ilike(f"%{search_term}%")
            )
        )
    if client_level:
        # Ensure ClientProfile is joined if not already
        if ClientProfile not in [e.entity for e in query.column_descriptions if hasattr(e, 'entity')]: # Check if join exists
             query = query.join(ClientProfile, User.id == ClientProfile.user_id, isouter=True)
        query = query.where(ClientProfile.client_level == client_level)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    query = query.order_by(User.id).offset(skip).limit(limit)
    users = session.exec(query).all()
    return users
# TODO: Implement other admin client profile endpoints: GET /{id}, PUT /{id}, POST /{id}/image, DELETE /{id}/image, POST /, DELETE /{id}

# --- My Profile Router ---
my_profile_router = APIRouter(prefix="/api/me/profile", tags=["My Profile"], dependencies=[Depends(get_current_active_user)])

@my_profile_router.get("/", response_model=UserReadWithClientProfile)
async def read_my_profile(current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    # Ensure client_profile is loaded for the response
    if current_user.client_profile is None:
        session.refresh(current_user, ["client_profile"])
    return current_user
# TODO: Implement other my profile endpoints: PUT /, POST /image, DELETE /image

# --- Tags Router (Admin) ---
tags_router = APIRouter(prefix="/api/tags", tags=["Tags Management"], dependencies=[Depends(get_current_active_superuser)])
# TODO: Implement all tag endpoints: POST /, GET /, GET /{id}, PUT /{id}, DELETE /{id}

# --- Categories Router (Admin) ---
categories_router = APIRouter(prefix="/api/categories", tags=["Categories Management"], dependencies=[Depends(get_current_active_superuser)])
# TODO: Implement all category endpoints: POST /, GET /, GET /{id}, PUT /{id}, DELETE /{id}

# --- Catalog Admin Router ---
catalog_admin_router = APIRouter(prefix="/api/admin/catalog", tags=["Admin - Catalog Management"], dependencies=[Depends(get_current_active_superuser)])
# TODO: Implement all catalog admin endpoints for CatalogEntry: POST, GET, PUT, DELETE

# --- Public Catalog Router ---
catalog_public_router = APIRouter(prefix="/api/catalog", tags=["Public Catalog"])
# TODO: Implement all public catalog endpoints: GET /, GET /{id}

# --- Admin Gift Items Router ---
gift_items_admin_router = APIRouter(prefix="/api/admin/gift-items", tags=["Admin - Gift Items Management"], dependencies=[Depends(get_current_active_superuser)])
# TODO: Implement all gift item admin endpoints: POST, GET, PUT, DELETE

# --- Admin Redemption Requests Router ---
redemption_admin_router = APIRouter(
    prefix="/api/admin/redemption-requests",
    tags=["Admin - Redemption Requests"],
    dependencies=[Depends(get_current_active_superuser)]
)

@redemption_admin_router.get("/", response_model=List[RedemptionRequestRead])
def list_redemption_requests_admin(skip: int = 0, limit: int = 100, user_id_filter: Optional[int] = None, status_filter: Optional[RedemptionRequestStatusEnum] = None, date_from: Optional[date] = None, date_to: Optional[date] = None, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_superuser)):
    query = select(RedemptionRequest).options(
        selectinload(RedemptionRequest.user).selectinload(User.client_profile),
        selectinload(RedemptionRequest.gift_item).selectinload(GiftItem.product)
    )
    if user_id_filter is not None: query = query.where(RedemptionRequest.user_id == user_id_filter)
    if status_filter is not None: query = query.where(RedemptionRequest.status == status_filter)
    if date_from is not None: query = query.where(RedemptionRequest.requested_at >= datetime.combine(date_from, time.min))
    if date_to is not None: query = query.where(RedemptionRequest.requested_at <= datetime.combine(date_to, time.max))
    query = query.order_by(RedemptionRequest.requested_at.desc(), RedemptionRequest.id.desc()).offset(skip).limit(limit)
    redemption_requests = session.exec(query).all()
    return redemption_requests

@redemption_admin_router.get("/{request_id}", response_model=RedemptionRequestRead)
def read_single_redemption_request_admin(request_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_superuser)):
    query = select(RedemptionRequest).where(RedemptionRequest.id == request_id).options(
        selectinload(RedemptionRequest.user).selectinload(User.client_profile),
        selectinload(RedemptionRequest.gift_item).selectinload(GiftItem.product)
    )
    db_redemption_request = session.exec(query).first()
    if not db_redemption_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redemption request not found")
    return db_redemption_request

@redemption_admin_router.post("/{request_id}/approve", response_model=RedemptionRequestRead)
def approve_redemption_request_admin(request_id: int, payload: Optional[RedemptionActionPayload] = None, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_superuser)):
    db_request = session.exec(select(RedemptionRequest).where(RedemptionRequest.id == request_id).options(
        selectinload(RedemptionRequest.user).selectinload(User.client_profile),
        selectinload(RedemptionRequest.gift_item).selectinload(GiftItem.product))).first()
    if not db_request: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redemption request not found")
    if db_request.status != RedemptionRequestStatusEnum.PENDIENTE_APROBACION:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request not pending approval. Status: {db_request.status.value}")

    if not db_request.user or not db_request.user.client_profile or not db_request.gift_item or not db_request.gift_item.product:
        # Refresh to ensure all related objects are loaded if they weren't by the initial query options (should be though)
        session.refresh(db_request, ["user", "gift_item"])
        if db_request.user: session.refresh(db_request.user, ["client_profile"])
        if db_request.gift_item: session.refresh(db_request.gift_item, ["product"])
        if not db_request.user or not db_request.user.client_profile or not db_request.gift_item or not db_request.gift_item.product:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Critical data missing for approval (user, profile, or gift item).")

    client_profile = db_request.user.client_profile
    gift_item_to_redeem = db_request.gift_item

    rejection_reason = None
    if not gift_item_to_redeem.is_active_as_gift: rejection_reason = "El regalo ya no está activo."
    elif gift_item_to_redeem.stock_available_for_redeem <= 0: rejection_reason = "Stock de regalo agotado."
    elif client_profile.available_points < db_request.points_at_request: rejection_reason = "Puntos insuficientes del cliente."

    if rejection_reason:
        db_request.status = RedemptionRequestStatusEnum.RECHAZADO
        db_request.admin_notes = f"Rechazado automáticamente: {rejection_reason} {payload.admin_notes if payload and payload.admin_notes else ''}".strip()
        db_request.updated_at = datetime.now(timezone.utc)
        session.add(db_request); session.commit(); session.refresh(db_request)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=rejection_reason)

    client_profile.available_points -= db_request.points_at_request
    gift_item_to_redeem.stock_available_for_redeem -= 1
    db_request.status = RedemptionRequestStatusEnum.APROBADO_POR_ENTREGAR
    if payload and payload.admin_notes: db_request.admin_notes = payload.admin_notes
    db_request.updated_at = datetime.now(timezone.utc)
    gift_item_to_redeem.updated_at = datetime.now(timezone.utc) # Update gift item's timestamp

    session.add(client_profile); session.add(gift_item_to_redeem); session.add(db_request)
    try:
        session.commit()
        session.refresh(db_request); session.refresh(client_profile); session.refresh(gift_item_to_redeem)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error during approval commit: {str(e)}")
    return db_request

@redemption_admin_router.post("/{request_id}/reject", response_model=RedemptionRequestRead)
def reject_redemption_request_admin(request_id: int, payload: Optional[RedemptionActionPayload] = None, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_superuser)):
    db_request = session.exec(select(RedemptionRequest).where(RedemptionRequest.id == request_id).options(
        selectinload(RedemptionRequest.user).selectinload(User.client_profile),
        selectinload(RedemptionRequest.gift_item).selectinload(GiftItem.product))).first()
    if not db_request: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redemption request not found")
    if db_request.status != RedemptionRequestStatusEnum.PENDIENTE_APROBACION:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request not pending approval. Status: {db_request.status.value}")

    db_request.status = RedemptionRequestStatusEnum.RECHAZADO
    if payload and payload.admin_notes is not None: db_request.admin_notes = payload.admin_notes
    else: db_request.admin_notes = db_request.admin_notes or "Rechazado por administrador." # Default note if none provided
    db_request.updated_at = datetime.now(timezone.utc)
    session.add(db_request)
    try:
        session.commit(); session.refresh(db_request)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error rejecting request: {str(e)}")
    return db_request

@redemption_admin_router.post("/{request_id}/deliver", response_model=RedemptionRequestRead)
def mark_redemption_request_delivered_admin(request_id: int, payload: Optional[RedemptionActionPayload] = None, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_superuser)):
    db_request = session.exec(select(RedemptionRequest).where(RedemptionRequest.id == request_id).options(
        selectinload(RedemptionRequest.user).selectinload(User.client_profile),
        selectinload(RedemptionRequest.gift_item).selectinload(GiftItem.product))).first()
    if not db_request: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redemption request not found")
    if db_request.status != RedemptionRequestStatusEnum.APROBADO_POR_ENTREGAR:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Request not approved for delivery. Status: {db_request.status.value}")

    db_request.status = RedemptionRequestStatusEnum.ENTREGADO
    if payload and payload.admin_notes is not None: db_request.admin_notes = payload.admin_notes
    db_request.updated_at = datetime.now(timezone.utc)
    session.add(db_request)
    try:
        session.commit(); session.refresh(db_request)
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error marking request delivered: {str(e)}")
    return db_request

# --- User Specific Data Router (e.g., sales history for a user) ---
user_data_router = APIRouter(prefix="/api/users", tags=["User Data"])

@user_data_router.get("/{user_id}/sales/", response_model=List[SaleRead])
async def get_user_sales_history(user_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user), skip: int = 0, limit: int = 100 ):
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this sales history")
    target_user = session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    sales_query = select(Sale).where(Sale.user_id == user_id).options(
        selectinload(Sale.items).selectinload(SaleItem.product).selectinload(Product.tags), # Eager load deep for SaleRead
        selectinload(Sale.items).selectinload(SaleItem.product).selectinload(Product.category_obj)
    ).order_by(Sale.sale_date.desc()).offset(skip).limit(limit)
    sales_history = session.exec(sales_query).all()
    return sales_history

# --- Shopping Cart Router ---
cart_router = APIRouter(prefix="/api/me/cart", tags=["My Cart"], dependencies=[Depends(get_current_active_user)])

def get_or_create_cart(user_id: int, session: Session) -> Cart:
    cart = session.exec(select(Cart).where(Cart.user_id == user_id).options(selectinload(Cart.items).selectinload(CartItem.product))).first()
    if not cart:
        cart = Cart(user_id=user_id)
        session.add(cart)
        session.commit()
        session.refresh(cart) # Ensure items list is present even if empty
        # session.refresh(cart, ["items"]) # Alternative way to ensure items is loaded
    return cart

@cart_router.get("/", response_model=CartRead)
def get_my_cart(current_user: User = Depends(get_current_active_user), session: Session = Depends(get_session)):
    cart = get_or_create_cart(user_id=current_user.id, session=session)
    # The CartRead model with its computed_field will handle total calculation.
    # Ensure items and their products are loaded by get_or_create_cart's options.
    return cart
# TODO: Implement other cart endpoints: POST /items/, PUT /items/{id}, DELETE /items/{id}, DELETE /

# --- My Redemptions Router (Client facing) ---
redeem_router = APIRouter(prefix="/api/me/redeem", tags=["My Redemptions"], dependencies=[Depends(get_current_active_user)])

@redeem_router.get("/requests/", response_model=List[RedemptionRequestRead])
def get_my_redemption_requests(skip: int = 0, limit: int = 50, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    query = (
        select(RedemptionRequest)
        .where(RedemptionRequest.user_id == current_user.id)
        .options(
            selectinload(RedemptionRequest.user), # UserRead doesn't need client_profile for this view
            selectinload(RedemptionRequest.gift_item).selectinload(GiftItem.product) # Load gift item and its product
        )
        .order_by(RedemptionRequest.requested_at.desc(), RedemptionRequest.id.desc())
        .offset(skip)
        .limit(limit)
    )
    my_requests = session.exec(query).all()
    return my_requests

@redeem_router.post("/requests/", response_model=RedemptionRequestRead, status_code=status.HTTP_201_CREATED)
def create_redemption_request(request_in: RedemptionRequestCreate, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    gift_item = session.get(GiftItem, request_in.gift_item_id)
    if not gift_item: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift item not found.")
    if not gift_item.is_active_as_gift: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gift not available for redemption.")
    if gift_item.stock_available_for_redeem <= 0: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gift out of stock for redemption.")

    client_profile = current_user.client_profile
    if not client_profile: # Should not happen if user creation ensures profile, but good check.
        session.refresh(current_user, ["client_profile"])
        client_profile = current_user.client_profile
    if not client_profile: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client profile not found.") # Should be 500 if system error

    if client_profile.available_points < gift_item.points_required:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough points.")

    if not gift_item.product: session.refresh(gift_item, ["product"]) # Ensure product is loaded for snapshot
    if not gift_item.product: raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve product details for gift snapshot.")

    snapshot_dict = {"name": gift_item.product.name, "description": gift_item.product.description, "price_revista": gift_item.product.price_revista}
    snapshot_str = json.dumps(snapshot_dict)
    if len(snapshot_str) > 1024: # Basic truncation if snapshot is too long
        snapshot_dict["description"] = (snapshot_dict.get("description") or "")[:500] + "..."
        snapshot_str = json.dumps(snapshot_dict)
        if len(snapshot_str) > 1024: snapshot_str = snapshot_str[:1021] + "..."

    db_request = RedemptionRequest(
        user_id=current_user.id,
        gift_item_id=gift_item.id,
        points_at_request=gift_item.points_required,
        product_details_at_request=snapshot_str,
        status=RedemptionRequestStatusEnum.PENDIENTE_APROBACION
    )
    session.add(db_request)
    try:
        session.commit()
        session.refresh(db_request)
        # Ensure relationships are loaded for the response model if not already via options
        if not db_request.gift_item: session.refresh(db_request, ["gift_item"])
        if db_request.gift_item and not db_request.gift_item.product: session.refresh(db_request.gift_item, ["product"])
        if not db_request.user: session.refresh(db_request, ["user"])
        return db_request
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not create redemption request: {str(e)}")

# --- Sales Router ---
sales_router = APIRouter(prefix="/api/sales", tags=["Sales"])
# TODO: Implement POST / for creating sales. Requires careful stock and points handling.
# TODO: Implement GET / and GET /{id} for sales with appropriate permissions.

@sales_router.put("/{sale_id}", response_model=SaleRead)
def update_sale_details(sale_id: int, sale_update: SaleUpdate, session: Session = Depends(get_session), current_user: User = Depends(get_current_active_superuser)):
    db_sale = session.get(Sale, sale_id)
    if not db_sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")

    previous_status = db_sale.status
    update_data = sale_update.model_dump(exclude_unset=True)

    if "discount_amount" in update_data and update_data["discount_amount"] is not None:
        db_sale.discount_amount = update_data["discount_amount"]
        # Recalculate total_amount and points_earned based on new discount
        current_items_total = sum(item.subtotal for item in db_sale.items if item.subtotal is not None)
        db_sale.total_amount = round(current_items_total - (db_sale.discount_amount or 0.0), 2)
        if db_sale.total_amount < 0: db_sale.total_amount = 0.0 # Ensure not negative
        # Assuming points are based on final total_amount. Adjust if based on pre-discount.
        # Also assuming SiteConfiguration holds points_per_currency_unit
        site_config = session.get(SiteConfiguration, 1) # Get site config for points calculation
        points_per_unit = site_config.system_param_points_per_currency_unit if site_config else 0.1
        db_sale.points_earned = int(db_sale.total_amount * points_per_unit)


    if "status" in update_data and update_data["status"] is not None:
        new_status_str = update_data["status"]
        try:
            new_status = SaleStatusEnum(new_status_str)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid sale status: {new_status_str}")

        # Logic for stock adjustment on cancellation
        if new_status == SaleStatusEnum.CANCELADO and previous_status != SaleStatusEnum.CANCELADO:
            for item in db_sale.items:
                product = session.get(Product, item.product_id)
                if product:
                    product.stock_actual += item.quantity
                    session.add(product)

        db_sale.status = new_status

    # Logic for points accumulation when sale is marked as COBRADO
    if db_sale.status == SaleStatusEnum.COBRADO and previous_status != SaleStatusEnum.COBRADO:
        if db_sale.user_id and db_sale.points_earned is not None and db_sale.points_earned > 0:
            if not db_sale.user: session.refresh(db_sale, ["user"]) # Ensure user is loaded
            if db_sale.user:
                client_profile_to_update = db_sale.user.client_profile
                if not client_profile_to_update: # Ensure client_profile is loaded
                    user_with_profile = session.exec(select(User).where(User.id == db_sale.user_id).options(selectinload(User.client_profile))).first()
                    if user_with_profile: client_profile_to_update = user_with_profile.client_profile

                if client_profile_to_update:
                    client_profile_to_update.available_points += db_sale.points_earned
                    session.add(client_profile_to_update)
                else:
                    # This case should ideally not happen if users always have profiles. Log a warning.
                    print(f"WARNING: ClientProfile not found for user ID {db_sale.user_id} during points accumulation for sale ID {db_sale.id}.")

    db_sale.updated_at = datetime.now(timezone.utc)
    session.add(db_sale)
    try:
        session.commit()
        session.refresh(db_sale)
        # Eager load for response model
        session.refresh(db_sale, ["items", "user"])
        if db_sale.user: session.refresh(db_sale.user, ["client_profile"])
        for item_in_sale in db_sale.items:
            session.refresh(item_in_sale, ["product"])
            if item_in_sale.product:
                session.refresh(item_in_sale.product, ["tags", "category_obj"])

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return db_sale

# --- Include all routers ---
app.include_router(dashboard_router)
app.include_router(products_router)
app.include_router(admin_clients_router)
app.include_router(my_profile_router)
app.include_router(tags_router)
app.include_router(categories_router)
app.include_router(catalog_admin_router)
app.include_router(catalog_public_router)
app.include_router(gift_items_admin_router)
app.include_router(redeem_router) # Client-facing gift redemption
app.include_router(sales_router)
app.include_router(user_data_router)
app.include_router(cart_router)
app.include_router(redemption_admin_router)

# TODO: Add Site Configuration Router
# site_config_router = APIRouter(prefix="/api/site-config", tags=["Site Configuration"])
# Implement GET, PUT (admin), POST /logo (admin)
# app.include_router(site_config_router)
