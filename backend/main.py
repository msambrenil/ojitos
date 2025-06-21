import os
import shutil
import uuid
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, APIRouter, status # Added status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, OAuth2PasswordRequestFormStrict
from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy import or_, func # Added func
from sqlalchemy.exc import IntegrityError # Added IntegrityError
from sqlalchemy.orm import selectinload # Added for eager loading
# typing.Optional is already imported at the top

from passlib.context import CryptContext

from .database import SaleStatusEnum # Ensure SaleStatusEnum is available for dashboard logic

# JWT Configuration
SECRET_KEY = "your-super-secret-key-that-should-be-in-env-var"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 Scheme (used by FastAPI for security dependencies)
# The tokenUrl should match the actual endpoint that provides the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token") # Defined oauth2_scheme

class TokenData(BaseModel):
    email: Optional[str] = None # Changed from username to email to match User model

# JWT Utility function to create access tokens
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Use ACCESS_TOKEN_EXPIRE_MINUTES for default if no delta provided
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=401, # Unauthorized
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
        # TokenData can be used here for more stringent validation of payload if needed
        # token_data = TokenData(email=email)
    except JWTError: # Catches various JWT errors
        raise credentials_exception

    user = session.exec(select(User).where(User.email == email)).first()
    if user is None:
        raise credentials_exception # User not found for the email in token
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user") # Or 403 Forbidden
    return current_user

# Assuming models are in database.py. Adjust if you created a separate models.py
from .database import (
    create_db_and_tables,
    engine,
    User,
    UserCreate,
    UserReadWithClientProfile,
    ClientProfile,
    ClientProfileCreate,
    ClientProfileUpdate,
    MyProfileUpdate,
    Sale,
    SaleRead,
    WishlistItem,
    WishlistItemCreate,
    WishlistItemRead,
    Cart,                      # Added
    CartItem,                  # Added
    CartRead,                  # Added
    CartItemCreate,            # Added
    CartItemUpdate,            # Added
    Product,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    SiteConfiguration,  # Added SiteConfiguration import
    Tag, TagRead,        # Added Tag and TagRead for product tag management
    Category, CategoryCreate, CategoryRead, # Added Category models
    CatalogEntry, CatalogEntryCreate, CatalogEntryUpdate, CatalogEntryApiResponse, # Added CatalogEntry models
    GiftItem, GiftItemCreate, GiftItemUpdate, GiftItemRead # Added GiftItem models
)


app = FastAPI()

# --- Static Files Setup ---
os.makedirs("static/product_images", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Dependency for DB Session ---
def get_session():
    with Session(engine) as session:
        yield session

# Site Configuration Initialization
def initialize_site_configuration(session: Session):
    db_config = session.get(SiteConfiguration, 1) # ID is fixed to 1

    if not db_config:
        print("No site configuration found, creating one with default values...")
        new_config = SiteConfiguration() # Defaults are set in the model
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
def on_app_startup(): # Renamed
    create_db_and_tables() # Creates all tables, including SiteConfiguration

    # Initialize site configuration using a new session
    with Session(engine) as session: # engine is imported from .database
        initialize_site_configuration(session)

# Pydantic model for card data (remains from previous step)
class CardData(BaseModel):
    title: str
    value: str

@app.get("/")
async def read_root():
    return {"message": "Hello World"}

# Endpoints for dashboard cards (remain from previous step)
@app.get("/api/dashboard/ventas-entregadas", response_model=CardData)
def get_dashboard_ventas_entregadas(session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    if not current_user.is_superuser:
        count = session.exec(select(func.count(Sale.id)).where(Sale.status == SaleStatusEnum.ENTREGADO, Sale.user_id == current_user.id)).one_or_none() or 0
    else:
        count = session.exec(select(func.count(Sale.id)).where(Sale.status == SaleStatusEnum.ENTREGADO)).one_or_none() or 0
    return CardData(title="Ventas Entregadas", value=str(count))

@app.get("/api/dashboard/a-entregar", response_model=CardData)
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

@app.get("/api/dashboard/por-armar", response_model=CardData)
def get_dashboard_por_armar(session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    if not current_user.is_superuser:
        count = session.exec(select(func.count(Sale.id)).where(
            Sale.status == SaleStatusEnum.PENDIENTE_PREPARACION,
            Sale.user_id == current_user.id
        )).one_or_none() or 0
    else:
        count = session.exec(select(func.count(Sale.id)).where(Sale.status == SaleStatusEnum.PENDIENTE_PREPARACION)).one_or_none() or 0
    return CardData(title="Por Armar", value=str(count))

@app.get("/api/dashboard/cobradas", response_model=CardData)
def get_dashboard_cobradas(session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
    if not current_user.is_superuser:
        total = session.exec(select(func.sum(Sale.total_amount)).where(
            Sale.status == SaleStatusEnum.COBRADO,
            Sale.user_id == current_user.id
        )).one_or_none() or 0.0
    else:
        total = session.exec(select(func.sum(Sale.total_amount)).where(Sale.status == SaleStatusEnum.COBRADO)).one_or_none() or 0.0
    return CardData(title="Cobradas", value=f"S/. {total:.2f}")

@app.get("/api/dashboard/a-cobrar", response_model=CardData)
def get_dashboard_a_cobrar(session: Session = Depends(get_session), current_user: User = Depends(get_current_active_user)):
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




# --- Products Router ---
products_router = APIRouter(prefix="/api/products", tags=["Products"])

@products_router.post("/", response_model=ProductRead)
async def create_product_endpoint(
    product_in: ProductCreate = Depends(),
    image: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session)
):
    image_url_for_db = None
    if image:
        # Ensure the filename is somewhat safe and unique
        filename = f"{uuid.uuid4()}_{image.filename.replace('..', '')}"
        file_path = f"static/product_images/{filename}"

        # Basic check for common web image types
        if image.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            raise HTTPException(status_code=400, detail="Invalid image file type. Please upload jpeg, png, gif, or webp.")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url_for_db = f"/{file_path}" # Store path relative to static mount

    # ProductCreate model already calculated derived prices if needed
    # ProductCreate includes category_id, which model_dump will pick up.
    product_data_for_db_instance = product_in.model_dump(exclude={"tag_names"}) # Exclude tag_names as it's handled by relationship

    # Validate category_id if provided
    validated_category_id: Optional[int] = None
    if product_in.category_id is not None:
        category = session.get(Category, product_in.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with ID {product_in.category_id} not found."
            )
        validated_category_id = product_in.category_id

    # Prepare data for Product model instance, ensuring category_id is correctly set
    # and image_url is added.
    # Fields from ProductCreate (inheriting ProductBase) are: name, description, image_url (added here),
    # price_revista, price_showroom, price_feria, stock_actual, stock_critico, category_id.

    # Create the Product DB model instance
    # Explicitly pass validated_category_id. Other fields come from product_in via ProductBase.
    db_product_args = product_in.model_dump(exclude={"tag_names", "category_id"})
    db_product = Product(**db_product_args, image_url=image_url_for_db, category_id=validated_category_id)

    # Handle tags
    if product_in.tag_names:
        processed_tags = []
        for tag_name in product_in.tag_names:
            tag_name_stripped = tag_name.strip()
            if not tag_name_stripped:
                continue

            tag_name_lower = tag_name_stripped.lower()
            db_tag = session.exec(select(Tag).where(func.lower(Tag.name) == tag_name_lower)).first()

            if not db_tag:
                # Tag does not exist, create it
                # Perform a final check within the transaction if strict unique handling is needed for concurrent requests
                # For simplicity here, we rely on the initial check and potential IntegrityError on commit.
                db_tag = Tag(name=tag_name_stripped) # Using original stripped name for storage
                session.add(db_tag)
                # Note: If Tag name has a unique constraint, commit might fail if another request created it.
                # The main endpoint's try-except should handle this.
            processed_tags.append(db_tag)
        db_product.tags = processed_tags

    try:
        session.add(db_product)
        session.commit()
        session.refresh(db_product)
        # Ensure relationships are loaded for ProductRead serialization
        if db_product.category_obj is not None:
            session.refresh(db_product.category_obj) # Explicitly refresh to load CategoryRead data
        # Accessing .tags triggers the load of the list if not already loaded.
        # Refreshing each tag ensures its data is current for TagRead serialization.
        for tag_item in db_product.tags:
            session.refresh(tag_item)
        return db_product
    except IntegrityError as e:
        session.rollback()
        # Check if it's a tag name conflict (if we hadn't checked before or due to race condition)
        if "tag.name" in str(e).lower() and "UNIQUE constraint failed" in str(e):
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A tag name caused a conflict. Ensure tag names are unique. Error: {e}")
        # Could also be product name unique constraint if one was added to Product model
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Data integrity error, possibly duplicate entry. Error: {e}")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@products_router.get("/", response_model=List[ProductRead])
def read_products_filtered( # Renamed
    skip: int = 0, limit: int = 100,
    search_term: Optional[str] = None,
    category: Optional[str] = None,
    low_stock: Optional[bool] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user) # Added for protection
):
    # Admin Protection
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access products list for admin"
        )

    query = select(Product)

    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.where(or_(Product.name.ilike(search_pattern), Product.description.ilike(search_pattern)))

    if category:
        # Assuming category filter should be case-insensitive and partial match
        category_pattern = f"%{category}%"
        query = query.where(Product.category.ilike(category_pattern))

    if low_stock is True:
        # Ensure stock_critico is positive to avoid filtering items not managed by critical stock.
        query = query.where(Product.stock_actual <= Product.stock_critico).where(Product.stock_critico > 0)

    query = query.order_by(Product.id) # Consistent ordering
    final_query = query.offset(skip).limit(limit)
    products = session.exec(final_query).all()
    return products

@products_router.get("/{product_id}", response_model=ProductRead)
def read_product_endpoint(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@products_router.put("/{product_id}", response_model=ProductRead)
async def update_product_endpoint(
    product_id: int,
    product_update_data: ProductUpdate = Depends(), # Use ProductUpdate for input
    image: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session)
):
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get data from ProductUpdate model, excluding unset values
    update_data = product_update_data.model_dump(exclude_unset=True)

    if image:
        # Basic check for common web image types
        if image.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
            raise HTTPException(status_code=400, detail="Invalid image file type. Please upload jpeg, png, gif, or webp.")

        # Delete old image if it exists and is different
        if db_product.image_url:
            old_image_path = db_product.image_url.lstrip('/')
            if os.path.exists(old_image_path):
                try:
                    os.remove(old_image_path)
                except OSError as e:
                    print(f"Error deleting old image {old_image_path}: {e}") # Log error

        # Save new image
        filename = f"{uuid.uuid4()}_{image.filename.replace('..', '')}"
        file_path = f"static/product_images/{filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        update_data["image_url"] = f"/{file_path}"
    elif "image_url" in update_data and update_data["image_url"] is None:
        # If image_url is explicitly set to null, delete the existing image
        if db_product.image_url:
            old_image_path = db_product.image_url.lstrip('/')
            if os.path.exists(old_image_path):
                try:
                    os.remove(old_image_path)
                except OSError as e:
                    print(f"Error deleting image {old_image_path}: {e}") # Log error
        update_data["image_url"] = None


    # Apply updates to the database product object
    # Handle category_id separately for validation
    if "category_id" in update_data:
        new_category_id = update_data.pop("category_id") # Remove so it's not processed in the loop
        if new_category_id is not None:
            category = session.get(Category, new_category_id)
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category with ID {new_category_id} not found."
                )
            db_product.category_id = new_category_id
        else: # new_category_id is None, so unset the category
            db_product.category_id = None

    for key, value in update_data.items():
        if key == "tag_names": continue # Skip tag_names, handled separately by its own logic below
        setattr(db_product, key, value)

    # Handle tags update (existing logic for tags)
    if product_update_data.tag_names is not None: # Field was provided
        if not product_update_data.tag_names: # Empty list means remove all tags
            db_product.tags.clear()
        else:
            updated_tags_list = []
            for tag_name in product_update_data.tag_names:
                tag_name_stripped = tag_name.strip()
                if not tag_name_stripped:
                    continue

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
        # Ensure relationships are loaded for ProductRead serialization
        if db_product.category_obj is not None:
             session.refresh(db_product.category_obj)
        for tag_item in db_product.tags:
             session.refresh(tag_item)
        return db_product
    except IntegrityError as e:
        session.rollback()
        if "tag.name" in str(e).lower() and "UNIQUE constraint failed" in str(e):
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A tag name caused a conflict during update. Error: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Data integrity error during update. Error: {e}")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred during update: {str(e)}")


@products_router.delete("/{product_id}", response_model=dict)
def delete_product_endpoint(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Delete image file if it exists
    if product.image_url:
        image_file_path = product.image_url.lstrip('/') # Remove leading '/'
        if os.path.exists(image_file_path):
            try:
                os.remove(image_file_path)
            except OSError as e:
                # Log the error, but proceed with deleting the DB record
                print(f"Error deleting image file {image_file_path}: {e}")

    session.delete(product)
    session.commit()
    return {"message": "Product deleted successfully"}

app.include_router(products_router)


# --- Authentication Routes ---
# oauth2_scheme is already defined above after JWT Configuration

class Token(BaseModel): # Define a Pydantic model for the token response
    access_token: str
    token_type: str

@app.post("/token", response_model=Token)
async def login_for_access_token_endpoint( # Renamed for clarity from placeholder
    form_data: OAuth2PasswordRequestFormStrict = Depends(),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.email == form_data.username)).first() # form_data.username is email

    if not user or not user.hashed_password: # Check if user exists and has a password
        raise HTTPException(
            status_code=401, # Corrected status_code to 401 for unauthorized
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active: # Check if user is active
        raise HTTPException(
            status_code=400, # Or 403 Forbidden
            detail="Inactive user",
        )

    if not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401, # Corrected status_code to 401
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Password Hashing Setup (already defined, ensure it's before user creation endpoint)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

@app.post("/users/", response_model=UserReadWithClientProfile)
def create_user_and_profile( # Name kept as per existing function
    user_in: UserCreate,
    session: Session = Depends(get_session),
    current_creator: User = Depends(get_current_active_user) # Added for authorization
):
    # Authorization: Only superusers can create new users
    if not current_creator.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create users"
        )

    # Check if user (email) already exists
    existing_user = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_password = get_password_hash(user_in.password) # get_password_hash should exist

    # UserCreate inherits is_active, is_superuser, is_seller from UserBase.
    # Pydantic will use defaults from UserBase if not provided in user_in.
    user_data_for_db = user_in.model_dump(exclude={"password"})
    # user_data_for_db will contain email, full_name, and values for
    # is_active, is_superuser, is_seller (either from payload or UserBase defaults).

    db_user = User(**user_data_for_db, hashed_password=hashed_password)

    # Create an empty ClientProfile and associate it
    # SQLModel should handle linking db_client_profile to db_user if relationship is set up correctly
    # and db_user is added to session. Let's ensure it's explicit if ClientProfile needs user_id.
    # ClientProfile model has user_id, so it's better to associate after user has ID or link via relationship.
    # Current ClientProfile does not require user_id in its constructor.
    # The relationship `db_user.client_profile = db_client_profile` handles the association.
    db_client_profile = ClientProfile()
    db_user.client_profile = db_client_profile # Associate directly

    session.add(db_user) # Adding user should also schedule client_profile for insert due to relationship

    try:
        session.commit()
        session.refresh(db_user)
        if db_user.client_profile: # Should exist and be linked
            session.refresh(db_user.client_profile)
        else:
            # This would be unexpected if the relationship setup is correct.
            print(f"WARNING: ClientProfile not immediately available after creating user ID {db_user.id}")
            # Attempt to fetch it to be sure, though this indicates a deeper issue if necessary.
            # This part can be removed if confident in SQLModel's relationship handling.
            profile_check = session.exec(select(ClientProfile).where(ClientProfile.user_id == db_user.id)).first()
            if profile_check:
                db_user.client_profile = profile_check # Manually re-associate for the response
                session.refresh(db_user.client_profile)
            else:
                 print(f"CRITICAL: ClientProfile not created or linked for user ID {db_user.id}")

    except IntegrityError as e:
        session.rollback()
        print(f"IntegrityError during user creation: {e}") # Log full error for debugging
        # Check if it's the email unique constraint (though checked above, race condition?)
        if "UNIQUE constraint failed: user.email" in str(e).lower():
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered (race condition or similar).")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Error creating user due to data conflict.")
    except Exception as e:
        session.rollback()
        print(f"Generic error during user creation: {e}") # Log full error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while creating the user.")

    return db_user


@app.get("/users/me", response_model=UserReadWithClientProfile) # Changed to UserReadWithClientProfile for consistency
async def read_users_me(token: str = Depends(oauth2_scheme)): # This is a placeholder for a real "current user" logic
    # In a real app, you'd decode the token to get the current user's ID,
    # then fetch the user and their profile from the DB.
    # For now, return a dummy user with a dummy profile.
    dummy_user_data = {
        "id": 1,
        "email": "currentuser@example.com",
        "full_name": "Current User",
        "is_active": True,
        "is_superuser": False,
        # hashed_password is not part of UserRead or UserReadWithClientProfile
    }
    dummy_profile_data = {
        "id": 1,
        "user_id": 1,
        "nickname": "CurrentNickname",
        "whatsapp_number": "123456789",
        "client_level": "Oro"
    }

    # Constructing the response model structure
    # This is a bit manual for a dummy; real logic would fetch from DB
    from .database import UserRead, ClientProfileRead as ClientProfileReadSchema # Use the Pydantic schema

    user_read_part = UserRead(**dummy_user_data)
    client_profile_read_part = ClientProfileReadSchema(**dummy_profile_data)

    # Create the final response model instance
    # UserReadWithClientProfile expects UserRead fields directly and a client_profile field
    response_user = UserReadWithClientProfile(
        **user_read_part.model_dump(),
        client_profile=client_profile_read_part
    )
    return response_user

# --- Admin Client Profiles Router ---
admin_clients_router = APIRouter(prefix="/api/admin/client-profiles", tags=["Admin - Client Profiles"])

@admin_clients_router.get("/", response_model=List[UserReadWithClientProfile])
def read_all_client_profiles_admin_filtered( # Renamed for clarity, or modify existing
    skip: int = 0,
    limit: int = 100,
    search_term: Optional[str] = None,
    client_level: Optional[str] = None,
    is_active: Optional[bool] = None, # FastAPI handles str "true"/"false" to bool
    session: Session = Depends(get_session),
    # current_admin_user: User = Depends(get_current_active_admin_user) # TODO: Add admin auth if needed
):
    query = select(User).join(ClientProfile, isouter=True) # Start with an outer join to always get profile info if UserReadWithClientProfile needs it

    if search_term:
        search_pattern = f"%{search_term}%"
        # Apply search on User fields and ClientProfile nickname
        query = query.where(
            or_(
                User.full_name.ilike(search_pattern),
                User.email.ilike(search_pattern),
                ClientProfile.nickname.ilike(search_pattern) # Search nickname
            )
        )

    if client_level:
        # If join wasn't done above or needs to be more specific for filtering
        # query = query.join(ClientProfile).where(ClientProfile.client_level == client_level)
        # Since we did an outer join, we can just filter. If no profile, it won't match.
        query = query.where(ClientProfile.client_level == client_level)


    if is_active is not None:
        query = query.where(User.is_active == is_active)

    query = query.order_by(User.id) # Order for consistent pagination

    final_query = query.offset(skip).limit(limit)
    users = session.exec(final_query).all()

    return users

@admin_clients_router.get("/{user_id}", response_model=UserReadWithClientProfile)
def read_single_client_profile_admin(user_id: int, session: Session = Depends(get_session)):
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    # db_user.client_profile will be None if no profile exists, which is handled by UserReadWithClientProfile
    return db_user

@admin_clients_router.put("/{user_id}", response_model=UserReadWithClientProfile)
def update_client_profile_data_admin(user_id: int, profile_update: ClientProfileUpdate, session: Session = Depends(get_session)):
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_client_profile = db_user.client_profile
    if not db_client_profile:
        # If profile doesn't exist, admin should use the POST endpoint to create one first
        raise HTTPException(status_code=404, detail="ClientProfile not found for this user. Use POST to create one.")

    update_data_dict = profile_update.model_dump(exclude_unset=True)
    # Explicitly prevent profile_image_url update through this endpoint
    update_data_dict.pop("profile_image_url", None)

    for key, value in update_data_dict.items():
        setattr(db_client_profile, key, value)

    session.add(db_client_profile)
    session.commit()
    session.refresh(db_client_profile)
    session.refresh(db_user) # Refresh user to ensure the response model gets updated profile
    return db_user

@admin_clients_router.post("/{user_id}/profile-image", response_model=UserReadWithClientProfile)
async def upload_client_profile_image_admin(user_id: int, image: UploadFile = File(...), session: Session = Depends(get_session)):
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_client_profile = db_user.client_profile
    if not db_client_profile:
        # Create a profile if one doesn't exist, or require it to exist first?
        # For this endpoint, let's assume profile should exist or be created if missing.
        # Simplified: Let's require profile to exist. Admin can create one via POST /api/admin/client-profiles/ if needed.
         raise HTTPException(status_code=404, detail="ClientProfile not found. Create profile data first.")

    # Ensure static/profile_images directory exists (already handled by product images, but good practice)
    os.makedirs("static/profile_images", exist_ok=True)

    # Delete old image if it exists
    if db_client_profile.profile_image_url:
        old_image_path = db_client_profile.profile_image_url.lstrip('/')
        if os.path.exists(old_image_path):
            try:
                os.remove(old_image_path)
            except OSError as e:
                print(f"Error deleting old profile image {old_image_path}: {e}") # Log error

    # Save new image
    filename = f"{uuid.uuid4()}_{image.filename.replace('..', '')}"
    file_path = f"static/profile_images/{filename}"

    if image.content_type not in ["image/jpeg", "image/png", "image/gif", "image/webp"]:
        raise HTTPException(status_code=400, detail="Invalid image file type.")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    db_client_profile.profile_image_url = f"/{file_path}"

    session.add(db_client_profile)
    session.commit()
    session.refresh(db_client_profile)
    session.refresh(db_user)
    return db_user

@admin_clients_router.delete("/{user_id}/profile-image", response_model=UserReadWithClientProfile)
def delete_client_profile_image_admin(user_id: int, session: Session = Depends(get_session)):
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_client_profile = db_user.client_profile
    if not db_client_profile or not db_client_profile.profile_image_url:
        raise HTTPException(status_code=404, detail="Profile image not found or client profile does not exist.")

    image_file_path = db_client_profile.profile_image_url.lstrip('/')
    if os.path.exists(image_file_path):
        try:
            os.remove(image_file_path)
        except OSError as e:
            print(f"Error deleting profile image file {image_file_path}: {e}") # Log error, but proceed

    db_client_profile.profile_image_url = None
    session.add(db_client_profile)
    session.commit()
    session.refresh(db_client_profile)
    session.refresh(db_user)
    return db_user

@admin_clients_router.post("/", response_model=UserReadWithClientProfile)
def create_client_profile_for_user_admin(profile_in: ClientProfileCreate, session: Session = Depends(get_session)):
    db_user = session.get(User, profile_in.user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail=f"User with id {profile_in.user_id} not found")

    if db_user.client_profile:
        raise HTTPException(status_code=400, detail="User already has a client profile. Use PUT to update.")

    # Create ClientProfile instance from the input, excluding profile_image_url
    profile_data_dict = profile_in.model_dump()
    profile_data_dict.pop("profile_image_url", None) # Ensure image_url is not set here

    new_profile = ClientProfile(**profile_data_dict) # user_id is in profile_data_dict

    db_user.client_profile = new_profile # Assign to the user
    # session.add(new_profile) # Not strictly needed if db_user is added and cascade persist is on (default)
    session.add(db_user) # Add user, which should cascade to new_profile

    try:
        session.commit()
        session.refresh(db_user)
        if db_user.client_profile: # Should exist now
             session.refresh(db_user.client_profile)
        else: # Should not happen
            raise HTTPException(status_code=500, detail="Failed to create and associate client profile.")
    except Exception as e:
        session.rollback()
        print(f"Error creating client profile for user {profile_in.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not create client profile.")

    return db_user

@admin_clients_router.delete("/{user_id}", response_model=dict)
def delete_client_profile_only_admin(user_id: int, session: Session = Depends(get_session)):
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    client_profile = db_user.client_profile
    if not client_profile:
        raise HTTPException(status_code=404, detail="ClientProfile not found for this user.")

    # Delete associated image file, if any
    if client_profile.profile_image_url:
        image_file_path = client_profile.profile_image_url.lstrip('/')
        if os.path.exists(image_file_path):
            try:
                os.remove(image_file_path)
            except OSError as e:
                print(f"Error deleting profile image file {image_file_path} during profile deletion: {e}")

    session.delete(client_profile)
    session.commit()
    # db_user.client_profile should now be None or an expired instance after commit
    # If you need to return the user object, ensure it's refreshed or handled appropriately.
    return {"message": "ClientProfile deleted successfully. User account remains."}

app.include_router(admin_clients_router)

# --- "My Profile" Router (for logged-in users to manage their own ClientProfile) ---
# This router is already defined and included below.

# --- Wishlist Router ---
wishlist_router = APIRouter(
    prefix="/api/me/wishlist",
    tags=["My Wishlist"],
    dependencies=[Depends(get_current_active_user)]
)

@wishlist_router.post("/", response_model=WishlistItemRead, status_code=status.HTTP_201_CREATED)
def add_item_to_wishlist(
    item_in: WishlistItemCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    product = session.get(Product, item_in.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Check if item already exists to prevent IntegrityError if possible,
    # and to return existing item with 200 OK if that's desired behavior.
    # However, the plan was to let DB constraint handle it and return 409.
    # So, we directly attempt to create.

    wishlist_item = WishlistItem(user_id=current_user.id, product_id=item_in.product_id)

    try:
        session.add(wishlist_item)
        session.commit()
        session.refresh(wishlist_item)
        # Ensure product details are available for the response model
        # Accessing wishlist_item.product should trigger lazy load or use already loaded data if eager loaded.
        # For Pydantic serialization, this is usually handled if relationship is set up.
        if wishlist_item.product:
             pass # Ensures product data is loaded for WishlistItemRead serialization
        return wishlist_item
    except IntegrityError: # Handles unique constraint (user_id, product_id)
        session.rollback()
        # Fetch the existing item to return it, or just raise 409
        existing_item = session.exec(
            select(WishlistItem).where(WishlistItem.user_id == current_user.id, WishlistItem.product_id == item_in.product_id)
        ).first()
        if existing_item:
            # If we want to return the existing item with a different status code (e.g. 200 OK or 303 See Other)
            # we would need to handle the response differently.
            # For a strict "create or fail if exists" API, 409 is appropriate.
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Item already in wishlist")
        else:
            # This case should be rare if IntegrityError was due to uq_user_product_wishlist
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not add item to wishlist after an unexpected conflict.")


@wishlist_router.get("/", response_model=List[WishlistItemRead])
def get_my_wishlist(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    # SQLModel/Pydantic should handle serializing product details in WishlistItemRead
    # based on the relationship if accessed.
    wishlist_items = session.exec(
        select(WishlistItem).where(WishlistItem.user_id == current_user.id)
    ).all()
    return wishlist_items

@wishlist_router.delete("/{product_id}/", status_code=status.HTTP_204_NO_CONTENT)
def remove_item_from_wishlist(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    item_to_delete = session.exec(
        select(WishlistItem).where(WishlistItem.user_id == current_user.id, WishlistItem.product_id == product_id)
    ).first()

    if not item_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found")

    session.delete(item_to_delete)
    session.commit()
    return # FastAPI returns 204 No Content automatically

@wishlist_router.get("/check/{product_id}/", response_model=dict)
def check_if_item_in_wishlist(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    existing_item = session.exec(
        select(WishlistItem).where(WishlistItem.user_id == current_user.id, WishlistItem.product_id == product_id)
    ).first()
    return {"in_wishlist": existing_item is not None}

app.include_router(wishlist_router)


# --- "My Profile" Router (for logged-in users to manage their own ClientProfile) ---
my_profile_router = APIRouter(
    prefix="/api/me/profile",
    tags=["My Profile"],
    dependencies=[Depends(get_current_active_user)]
)

@my_profile_router.get("/", response_model=UserReadWithClientProfile)
async def read_my_profile(current_user: User = Depends(get_current_active_user)):
    # The get_current_active_user dependency already provides the current_user object,
    # which includes the client_profile if eagerly loaded or accessed.
    # SQLModel's default behavior with relationships usually makes client_profile accessible here
    # if it was populated correctly when the User object was created/fetched.
    # The UserReadWithClientProfile response model will handle serializing it.
    return current_user

from .database import MyProfileUpdate # Ensure this specific import is present

@my_profile_router.put("/", response_model=UserReadWithClientProfile)
async def update_my_profile_data(
    profile_update_data: MyProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    db_client_profile = current_user.client_profile

    if not db_client_profile:
        # This case should ideally not be reached if profiles are created on user registration.
        # However, if it can occur, creating one might be an option, or raising an error.
        # For now, let's assume profile must exist (created on user registration).
        raise HTTPException(status_code=404, detail="ClientProfile not found for current user.")

    update_data_dict = profile_update_data.model_dump(exclude_unset=True)

    for key, value in update_data_dict.items():
        setattr(db_client_profile, key, value)

    session.add(db_client_profile)
    try:
        session.commit()
        session.refresh(db_client_profile)
        # Refresh current_user as well, as its client_profile attribute might be a cached version
        # or to ensure any ORM magic related to the session updates the parent object.
        session.refresh(current_user)
    except Exception as e:
        session.rollback()
        # In a real app, log 'e' properly
        print(f"Error updating profile: {e}") # Basic logging
        raise HTTPException(status_code=500, detail="Error updating profile.")

    return current_user

@my_profile_router.delete("/profile-image", response_model=UserReadWithClientProfile)
async def delete_my_profile_image(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    db_client_profile = current_user.client_profile

    if not db_client_profile:
        # Should not happen if profile is auto-created with user
        raise HTTPException(status_code=404, detail="ClientProfile not found for current user.")

    if not db_client_profile.profile_image_url:
        # No image to delete, operation is idempotent.
        return current_user

    image_file_path = db_client_profile.profile_image_url.lstrip('/')

    if os.path.exists(image_file_path):
        try:
            os.remove(image_file_path)
        except Exception as e:
            # Log this error but proceed to nullify DB entry
            print(f"Error deleting image file {image_file_path}: {e}")

    db_client_profile.profile_image_url = None # Set to None in DB

    session.add(db_client_profile)
    try:
        session.commit()
        session.refresh(db_client_profile)
        session.refresh(current_user) # Refresh user to update its client_profile relationship
    except Exception as e:
        session.rollback()
        # Log error e
        # Potentially an inconsistent state if file was deleted but DB update failed.
        print(f"Error updating profile after image deletion: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating profile after image deletion.")

    return current_user

@my_profile_router.post("/profile-image", response_model=UserReadWithClientProfile)
async def upload_my_profile_image(
    image: UploadFile = File(...), # '...' makes it required
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    db_client_profile = current_user.client_profile
    if not db_client_profile:
        # If profile doesn't exist, create one. This is different from admin endpoint.
        # User should always have a profile to update image for.
        # This logic assumes profile is auto-created with user. If not, this might need adjustment
        # or a check earlier in get_current_active_user if profile is essential for an "active" session.
        # For now, matching the admin logic: if profile doesn't exist, it's an issue.
        raise HTTPException(status_code=404, detail="ClientProfile not found for current user. Please contact support if this persists.")

    # Validate image type
    allowed_content_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if image.content_type not in allowed_content_types:
        raise HTTPException(status_code=400, detail="Invalid image type. Allowed: JPEG, PNG, GIF, WebP.")

    upload_dir = "static/profile_images"
    os.makedirs(upload_dir, exist_ok=True)

    # Remove old image if it exists
    if db_client_profile.profile_image_url:
        old_image_path = db_client_profile.profile_image_url.lstrip('/')
        if os.path.exists(old_image_path):
            try:
                os.remove(old_image_path)
            except OSError as e:
                print(f"Error deleting old profile image {old_image_path}: {e}") # Log error

    # Sanitize filename and create a unique name
    filename_prefix = str(uuid.uuid4())
    original_filename_parts = image.filename.split('.')
    original_extension = ""
    if len(original_filename_parts) > 1:
        original_extension = original_filename_parts[-1].lower() # Ensure extension is lower case
        if original_extension not in ["jpg", "jpeg", "png", "gif", "webp"]: # Basic check on extension
             raise HTTPException(status_code=400, detail="Invalid image file extension.")
    else: # No extension found
        raise HTTPException(status_code=400, detail="Image filename must have an extension.")

    safe_filename = f"{filename_prefix}_{current_user.id}.{original_extension}"
    file_path = os.path.join(upload_dir, safe_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
    except Exception as e:
        print(f"Could not save image: {e}") # Log error
        raise HTTPException(status_code=500, detail=f"Could not save image.")
    finally:
        image.file.close() # Ensure file is closed

    db_client_profile.profile_image_url = f"/{file_path}" # Store with leading slash

    session.add(db_client_profile)
    try:
        session.commit()
        session.refresh(db_client_profile)
        session.refresh(current_user) # Refresh user to update its client_profile relationship
    except Exception as e:
        session.rollback()
        print(f"Error updating profile image in DB: {e}") # Log error
        # If commit fails, attempt to delete the just-uploaded file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e_remove:
                 print(f"Failed to remove partially uploaded file {file_path}: {e_remove}")
        raise HTTPException(status_code=500, detail=f"Error updating profile image in DB.")

    return current_user

# Endpoints for my_profile_router will be added in subsequent steps.
# For now, just including the router in the app.
app.include_router(my_profile_router)


# --- Tags Router ---
tags_router = APIRouter(
    prefix="/api/tags",
    tags=["Tags Management"],
    dependencies=[Depends(get_current_active_user)] # Base protection
)

from .database import Tag, TagCreate, TagRead # Ensure these are imported

@tags_router.post("/", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(
    tag_in: TagCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    existing_tag = session.exec(
        select(Tag).where(func.lower(Tag.name) == func.lower(tag_in.name))
    ).first()
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tag name '{tag_in.name}' already exists."
        )

    db_tag = Tag.model_validate(tag_in)
    try:
        session.add(db_tag)
        session.commit()
        session.refresh(db_tag)
        return db_tag
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag name likely already exists (race condition).")

@tags_router.get("/", response_model=List[TagRead])
def read_tags(
    skip: int = 0,
    limit: int = 100,
    name_filter: Optional[str] = None,
    session: Session = Depends(get_session)
):
    query = select(Tag)
    if name_filter:
        query = query.where(Tag.name.ilike(f"%{name_filter}%"))

    query = query.order_by(Tag.name).offset(skip).limit(limit)
    tags = session.exec(query).all()
    return tags

@tags_router.get("/{tag_id}", response_model=TagRead)
def read_tag(
    tag_id: int,
    session: Session = Depends(get_session)
):
    db_tag = session.get(Tag, tag_id)
    if not db_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return db_tag

@tags_router.put("/{tag_id}", response_model=TagRead)
def update_tag(
    tag_id: int,
    tag_in: TagCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    db_tag = session.get(Tag, tag_id)
    if not db_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    if func.lower(db_tag.name) != func.lower(tag_in.name):
        existing_tag_with_new_name = session.exec(
            select(Tag).where(func.lower(Tag.name) == func.lower(tag_in.name))
        ).first()
        if existing_tag_with_new_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Another tag with name '{tag_in.name}' already exists."
            )

    db_tag.name = tag_in.name
    try:
        session.add(db_tag)
        session.commit()
        session.refresh(db_tag)
        return db_tag
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag name likely already exists (race condition).")

@tags_router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    db_tag = session.get(Tag, tag_id)
    if not db_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    session.delete(db_tag)
    session.commit()
    return

app.include_router(tags_router)


# --- Categories Router ---
categories_router = APIRouter(
    prefix="/api/categories",
    tags=["Categories Management"],
    dependencies=[Depends(get_current_active_user)] # Base protection
)

@categories_router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    category_in: CategoryCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    existing_category = session.exec(
        select(Category).where(func.lower(Category.name) == func.lower(category_in.name))
    ).first()
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category name '{category_in.name}' already exists."
        )

    db_category = Category.model_validate(category_in)
    try:
        session.add(db_category)
        session.commit()
        session.refresh(db_category)
        return db_category
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category name likely already exists (race condition).")

@categories_router.get("/", response_model=List[CategoryRead])
def read_categories(
    skip: int = 0,
    limit: int = 100,
    name_filter: Optional[str] = None,
    session: Session = Depends(get_session)
):
    query = select(Category)
    if name_filter:
        query = query.where(Category.name.ilike(f"%{name_filter}%"))

    query = query.order_by(Category.name).offset(skip).limit(limit)
    categories = session.exec(query).all()
    return categories

@categories_router.get("/{category_id}", response_model=CategoryRead)
def read_category(
    category_id: int,
    session: Session = Depends(get_session)
):
    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return db_category

@categories_router.put("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    category_in: CategoryCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if func.lower(db_category.name) != func.lower(category_in.name):
        existing_category_with_new_name = session.exec(
            select(Category).where(func.lower(Category.name) == func.lower(category_in.name))
        ).first()
        if existing_category_with_new_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Another category with name '{category_in.name}' already exists."
            )

    db_category.name = category_in.name
    db_category.description = category_in.description

    try:
        session.add(db_category)
        session.commit()
        session.refresh(db_category)
        return db_category
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category name likely already exists (race condition).")

@categories_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    db_category = session.get(Category, category_id)
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    products_to_update = session.exec(select(Product).where(Product.category_id == category_id)).all()
    for prod in products_to_update:
        prod.category_id = None
        session.add(prod)

    session.delete(db_category)
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting category: {str(e)}")

    return

app.include_router(categories_router)


# --- CatalogEntry Helper Function ---
def _build_catalog_entry_response(db_entry: CatalogEntry, session: Session) -> CatalogEntryApiResponse:
    # Ensure product relationship is loaded for calculations and ProductRead serialization
    # Check if relationship is already loaded; if not, refresh.
    # This check might be version-dependent for SQLModel/SQLAlchemy behavior with relationships.
    # A common way to check if a relationship is loaded without triggering a lazy load
    # is to check if the attribute is in the instance's __dict__.
    # However, session.refresh is more explicit if we are unsure.
    if 'product' not in db_entry.__dict__ or not db_entry.product:
         session.refresh(db_entry, ["product"])

    if not db_entry.product:
        # This case should be rare if FK constraints are active and product was loaded/refreshed.
        # It implies a data integrity issue (e.g., product deleted after catalog entry was made without FK enforcement)
        # or a failure in loading the relationship.
        # For robustness, we might log this and decide how to handle.
        # For now, let's assume if it's still not loaded, something is critically wrong.
        print(f"Critical: Product not loaded for CatalogEntry ID {db_entry.id} even after refresh attempt.")
        # Depending on strictness, could raise 500 or try to build response without product.
        # For now, let's assume product is essential for the response.
        raise HTTPException(status_code=500, detail=f"Associated product data for catalog entry ID {db_entry.id} could not be loaded.")

    eff_price = db_entry.catalog_price if db_entry.catalog_price is not None else db_entry.product.price_revista
    eff_price = round(eff_price if eff_price is not None else 0.0, 2)

    eff_img_url = db_entry.catalog_image_url if db_entry.catalog_image_url and db_entry.catalog_image_url.strip() else db_entry.product.image_url

    product_read_data = ProductRead.model_validate(db_entry.product)

    response_data = CatalogEntryApiResponse(
        id=db_entry.id,
        product_id=db_entry.product_id,
        is_visible_in_catalog=db_entry.is_visible_in_catalog,
        is_sold_out_in_catalog=db_entry.is_sold_out_in_catalog,
        promo_text=db_entry.promo_text,
        display_order=db_entry.display_order,
        created_at=db_entry.created_at,
        updated_at=db_entry.updated_at,
        catalog_price=db_entry.catalog_price,
        catalog_image_url=db_entry.catalog_image_url,
        product=product_read_data,
        effective_price=eff_price,
        effective_image_url=eff_img_url
    )
    return response_data

# --- Catalog Admin Router ---
catalog_admin_router = APIRouter(
    prefix="/api/admin/catalog",
    tags=["Admin - Catalog Management"],
    dependencies=[Depends(get_current_active_user)]
)

@catalog_admin_router.post("/entries/", response_model=CatalogEntryApiResponse, status_code=status.HTTP_201_CREATED)
def create_catalog_entry_admin(
    entry_in: CatalogEntryCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    product = session.get(Product, entry_in.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {entry_in.product_id} not found")

    db_entry = CatalogEntry.model_validate(entry_in)
    try:
        session.add(db_entry)
        session.commit()
        session.refresh(db_entry)
        # Ensure product is loaded for the response builder by explicitly refreshing the relationship
        session.refresh(db_entry, ["product"]) # SQLModel specific way to refresh a relationship
        return _build_catalog_entry_response(db_entry, session)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product already in catalog or other integrity error.")

@catalog_admin_router.get("/entries/", response_model=List[CatalogEntryApiResponse])
def read_catalog_entries_admin(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    entries_query = select(CatalogEntry).options(selectinload(CatalogEntry.product)).order_by(CatalogEntry.display_order, CatalogEntry.id).offset(skip).limit(limit)
    db_entries = session.exec(entries_query).all()

    return [_build_catalog_entry_response(entry, session) for entry in db_entries]

@catalog_admin_router.get("/entries/{entry_id}", response_model=CatalogEntryApiResponse)
def read_single_catalog_entry_admin(
    entry_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    db_entry = session.exec(
        select(CatalogEntry).where(CatalogEntry.id == entry_id).options(selectinload(CatalogEntry.product))
    ).first()
    if not db_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog entry not found")
    return _build_catalog_entry_response(db_entry, session)

@catalog_admin_router.put("/entries/{entry_id}", response_model=CatalogEntryApiResponse)
def update_catalog_entry_admin(
    entry_id: int,
    entry_update: CatalogEntryUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    db_entry = session.get(CatalogEntry, entry_id)
    if not db_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog entry not found")

    update_data = entry_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_entry, key, value)
    db_entry.updated_at = datetime.now(timezone.utc)

    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    session.refresh(db_entry, ["product"]) # Ensure product is loaded for response
    return _build_catalog_entry_response(db_entry, session)

@catalog_admin_router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalog_entry_admin(
    entry_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    db_entry = session.get(CatalogEntry, entry_id)
    if not db_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog entry not found")

    session.delete(db_entry)
    session.commit()
    return

app.include_router(catalog_admin_router)

# --- Public Catalog Router ---
catalog_public_router = APIRouter(
    prefix="/api/catalog",
    tags=["Public Catalog"]
)

@catalog_public_router.get("/entries/", response_model=List[CatalogEntryApiResponse])
def read_public_catalog_entries(
    skip: int = 0,
    limit: int = 20, # Smaller default limit for public
    session: Session = Depends(get_session)
):
    entries_query = select(CatalogEntry).where(CatalogEntry.is_visible_in_catalog == True).options(selectinload(CatalogEntry.product)).order_by(CatalogEntry.display_order, CatalogEntry.id).offset(skip).limit(limit)
    db_entries = session.exec(entries_query).all()
    return [_build_catalog_entry_response(entry, session) for entry in db_entries]

app.include_router(catalog_public_router)


# --- Admin Gift Items Router ---
gift_items_admin_router = APIRouter(
    prefix="/api/admin/gift-items",
    tags=["Admin - Gift Items Management"],
    dependencies=[Depends(get_current_active_user)]
)

@gift_items_admin_router.post("/", response_model=GiftItemRead, status_code=status.HTTP_201_CREATED)
def create_gift_item_admin(
    gift_in: GiftItemCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    product = session.get(Product, gift_in.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {gift_in.product_id} not found."
        )

    db_gift_item = GiftItem.model_validate(gift_in)
    try:
        session.add(db_gift_item)
        session.commit()
        session.refresh(db_gift_item)
        if not db_gift_item.product:
             session.refresh(db_gift_item, ["product"])
        return db_gift_item
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product ID {gift_in.product_id} is already configured as a gift item."
        )

@gift_items_admin_router.get("/", response_model=List[GiftItemRead])
def read_gift_items_admin(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    query = select(GiftItem).options(selectinload(GiftItem.product))

    if is_active is not None:
        query = query.where(GiftItem.is_active_as_gift == is_active)

    query = query.order_by(GiftItem.id).offset(skip).limit(limit)
    gift_items = session.exec(query).all()
    return gift_items

@gift_items_admin_router.get("/{gift_item_id}", response_model=GiftItemRead)
def read_gift_item_admin(
    gift_item_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    db_gift_item = session.exec(
        select(GiftItem).where(GiftItem.id == gift_item_id).options(selectinload(GiftItem.product))
    ).first()

    if not db_gift_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift item not found")
    return db_gift_item

@gift_items_admin_router.put("/{gift_item_id}", response_model=GiftItemRead)
def update_gift_item_admin(
    gift_item_id: int,
    gift_update: GiftItemUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    db_gift_item = session.get(GiftItem, gift_item_id)
    if not db_gift_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift item not found")

    update_data = gift_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_gift_item, key, value)

    db_gift_item.updated_at = datetime.now(timezone.utc)

    session.add(db_gift_item)
    session.commit()
    session.refresh(db_gift_item)
    if not db_gift_item.product:
        session.refresh(db_gift_item, ["product"])
    return db_gift_item

@gift_items_admin_router.delete("/{gift_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gift_item_admin(
    gift_item_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")

    db_gift_item = session.get(GiftItem, gift_item_id)
    if not db_gift_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift item not found")

    session.delete(db_gift_item)
    session.commit()
    return

app.include_router(gift_items_admin_router)


# --- User Specific Data Router (e.g., Sales History) ---
# This router is already defined and included below.

# --- Sales Router (New for creating and managing sales by admin/system) ---
# sales_router is defined below, this is just a marker for the diff.
# The tags_router and its include_router call will be placed before this section.

from .database import SaleCreate, SaleItem, SaleStatusEnum # Tag models are imported with tags_router

@sales_router.post("/", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale(
    sale_in: SaleCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user) # For setting user_id if not admin, or for audit
):
    # Determine the user_id for the sale
    # If an admin can create a sale for another user:
    if current_user.is_superuser and sale_in.user_id is not None:
        target_user_id = sale_in.user_id
        target_user = session.get(User, target_user_id)
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {target_user_id} not found.")
    else: # Regular user creating sale for themselves, or admin creating for self
        target_user_id = current_user.id

    # Validate products and calculate total_amount and points_earned
    calculated_total_amount = 0.0
    calculated_points_earned = 0 # Example: 1 point per 10 S/.

    db_sale_items = []
    for item_create in sale_in.items:
        product = session.get(Product, item_create.product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with id {item_create.product_id} not found.")

        # TODO: Stock check
        # if product.stock_actual < item_create.quantity:
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Not enough stock for product {product.name}.")

        price_at_sale = item_create.price_at_sale if item_create.price_at_sale is not None else product.price_feria # Default to price_feria if not specified
        if price_at_sale is None: # Still None? Fallback to price_revista
            price_at_sale = product.price_revista

        subtotal = item_create.quantity * price_at_sale
        calculated_total_amount += subtotal

        db_item = SaleItem(
            product_id=item_create.product_id,
            quantity=item_create.quantity,
            price_at_sale=price_at_sale,
            subtotal=subtotal
            # sale_id will be set by relationship
        )
        db_sale_items.append(db_item)
        # product.stock_actual -= item_create.quantity # Decrement stock
        # session.add(product) # Add product to session to save stock change

    # Apply discount
    final_total_amount = calculated_total_amount - (sale_in.discount_amount or 0.0)
    if final_total_amount < 0:
        final_total_amount = 0 # Cannot be negative

    calculated_points_earned = int(final_total_amount / 10) # Example points logic

    # Create Sale object
    db_sale = Sale(
        user_id=target_user_id,
        status=sale_in.status or SaleStatusEnum.PENDIENTE_PREPARACION,
        discount_amount=sale_in.discount_amount or 0.0,
        total_amount=final_total_amount,
        points_earned=calculated_points_earned,
        items=db_sale_items, # Assign items to the sale
        sale_date=datetime.now(timezone.utc), # Set current time
        updated_at=datetime.now(timezone.utc)
    )

    session.add(db_sale)
    try:
        session.commit()
        session.refresh(db_sale)
        # Refresh items to get their IDs and correctly link back to sale for response model
        for item_in_db in db_sale.items:
            session.refresh(item_in_db)
            if item_in_db.product: # Ensure product is loaded for SaleItemRead
                pass
        if db_sale.user: # Ensure user is loaded if UserRead is part of SaleRead
            pass
    except IntegrityError as e: # Catch potential DB errors
        session.rollback()
        print(f"IntegrityError creating sale: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sale could not be created due to a data conflict.")
    except Exception as e:
        session.rollback()
        print(f"Generic error creating sale: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while creating the sale.")

    return db_sale


from datetime import date, time # Ensure date and time are explicitly imported

@sales_router.get("/", response_model=List[SaleRead])
def read_sales(
    skip: int = 0,
    limit: int = 100,
    user_id_on_filter: Optional[int] = None,
    status_filter: Optional[SaleStatusEnum] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    query = select(Sale)

    if not current_user.is_superuser:
        if user_id_on_filter is not None and user_id_on_filter != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view sales for this user")
        query = query.where(Sale.user_id == current_user.id)
    elif user_id_on_filter is not None:
        target_user = session.get(User, user_id_on_filter)
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {user_id_on_filter} not found for filtering.")
        query = query.where(Sale.user_id == user_id_on_filter)

    if status_filter is not None:
        query = query.where(Sale.status == status_filter)

    if date_from is not None:
        datetime_from = datetime.combine(date_from, time.min)
        query = query.where(Sale.sale_date >= datetime_from)

    if date_to is not None:
        datetime_to = datetime.combine(date_to, time.max)
        query = query.where(Sale.sale_date <= datetime_to)

    query = query.order_by(Sale.sale_date.desc(), Sale.id.desc()).offset(skip).limit(limit)

    sales = session.exec(query).all()
    return sales

@sales_router.get("/{sale_id}", response_model=SaleRead)
def read_single_sale(
    sale_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    db_sale = session.get(Sale, sale_id)

    if not db_sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")

    # Authorization check
    if not current_user.is_superuser and db_sale.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this sale")

    # Pydantic serialization via SaleRead will handle accessing db_sale.items and db_sale.user
    # Ensure related data is loaded if not automatically by SQLModel/Pydantic for the response model.
    # Accessing them can trigger lazy loads if necessary.
    if db_sale.items: pass
    if db_sale.user: pass

    return db_sale

    from .database import SaleUpdate, SaleStatusEnum, SaleItem, Product, ClientProfile # Ensure these are imported

@sales_router.put("/{sale_id}", response_model=SaleRead)
def update_sale_details(
    sale_id: int,
    sale_update: SaleUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    # Authorization: Only Admin can update sales
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update sales")

    db_sale = session.get(Sale, sale_id)
    if not db_sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")

    previous_status = db_sale.status
    update_data = sale_update.model_dump(exclude_unset=True) # Get only provided fields

    # Update discount first if provided, as it affects total_amount
    if "discount_amount" in update_data and update_data["discount_amount"] is not None:
        db_sale.discount_amount = update_data["discount_amount"]
        # Recalculate total_amount based on existing item subtotals
        current_items_total = sum(item.subtotal for item in db_sale.items if item.subtotal is not None)
        db_sale.total_amount = round(current_items_total - (db_sale.discount_amount or 0.0), 2)
        if db_sale.total_amount < 0: db_sale.total_amount = 0.0 # Ensure not negative

        # Recalculate points based on new total_amount (example logic)
        db_sale.points_earned = int(db_sale.total_amount / 10)

    # Update status
    if "status" in update_data and update_data["status"] is not None:
        new_status_str = update_data["status"]
        try:
            new_status = SaleStatusEnum(new_status_str) # Convert string from Pydantic to Enum
        except ValueError:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid sale status: {new_status_str}")

        if new_status == SaleStatusEnum.CANCELADO and previous_status != SaleStatusEnum.CANCELADO:
            # Revert stock for each item in the sale
            for item in db_sale.items:
                product = session.get(Product, item.product_id)
                if product:
                    product.stock_actual += item.quantity
                    session.add(product)
                else:
                    # Log error: Product associated with sale item not found, cannot revert stock.
                    print(f"Warning: Product ID {item.product_id} for SaleItem ID {item.id} not found. Stock not reverted.")
        db_sale.status = new_status # Assign the enum value

    # --- Points Accumulation Logic ---
    if db_sale.status == SaleStatusEnum.COBRADO and previous_status != SaleStatusEnum.COBRADO:
        if db_sale.user_id and db_sale.points_earned is not None and db_sale.points_earned > 0:
            # Ensure user and client_profile are loaded for points update
            if not db_sale.user: # If relationship not loaded
                 session.refresh(db_sale, ["user"])

            if db_sale.user:
                if not db_sale.user.client_profile:
                    # This attempts to load client_profile if it wasn't loaded with the user.
                    # If using selectinload for User in initial Sale query, this might not be needed.
                    # For safety, or if User was loaded without its profile relation.
                    user_with_profile = session.exec(
                        select(User).where(User.id == db_sale.user_id).options(selectinload(User.client_profile))
                    ).first()
                    if user_with_profile and user_with_profile.client_profile:
                        client_profile_to_update = user_with_profile.client_profile
                    else: # Fallback if explicit load didn't work or no profile
                        client_profile_to_update = None
                else:
                    client_profile_to_update = db_sale.user.client_profile

                if client_profile_to_update:
                    client_profile_to_update.available_points += db_sale.points_earned
                    session.add(client_profile_to_update)
                    print(f"POINTS: User {db_sale.user_id} earned {db_sale.points_earned} points. New total: {client_profile_to_update.available_points}")
                else:
                    print(f"WARNING: ClientProfile not found for user {db_sale.user_id} (Sale ID: {db_sale.id}). Points not added.")
            else:
                print(f"WARNING: User not found for sale {db_sale.id}. Points not added.")
    # --- End Points Accumulation Logic ---

    db_sale.updated_at = datetime.now(timezone.utc)
    session.add(db_sale)

    try:
        session.commit()
        session.refresh(db_sale)
        # Refresh related items and their products for the response model.
        for item_in_sale in db_sale.items:
            session.refresh(item_in_sale)
            if item_in_sale.product:
                session.refresh(item_in_sale.product)
        if db_sale.user:
            session.refresh(db_sale.user)
            if db_sale.user.client_profile: # Also refresh client_profile as its points might have changed
                session.refresh(db_sale.user.client_profile)

    except Exception as e:
        session.rollback()
        print(f"Error updating sale details: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating sale: {str(e)}")

    return db_sale

@sales_router.delete("/{sale_id}", response_model=SaleRead)
def cancel_sale_by_admin(
    sale_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    # Authorization: Only Admin can cancel sales
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to cancel sales")

    db_sale = session.get(Sale, sale_id)
    if not db_sale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")

    if db_sale.status == SaleStatusEnum.CANCELADO:
        # Sale is already cancelled, refresh relations for consistent response and return
        session.refresh(db_sale)
        for item_in_sale in db_sale.items: # Ensure items and their products are loaded
            session.refresh(item_in_sale)
            if item_in_sale.product:
                session.refresh(item_in_sale.product)
        if db_sale.user: # Ensure user is loaded
            session.refresh(db_sale.user)
        return db_sale

    # Stock Management on Cancellation: Revert stock for each item in the sale
    for item in db_sale.items:
        product = session.get(Product, item.product_id)
        if product:
            product.stock_actual += item.quantity
            session.add(product)
        else:
            print(f"Warning: Product ID {item.product_id} for SaleItem ID {item.id} not found during sale cancellation. Stock not reverted for this item.")

    db_sale.status = SaleStatusEnum.CANCELADO
    db_sale.updated_at = datetime.now(timezone.utc)
    session.add(db_sale)

    try:
        session.commit()
        session.refresh(db_sale)
        for item_in_sale in db_sale.items:
            session.refresh(item_in_sale)
            if item_in_sale.product:
                session.refresh(item_in_sale.product)
        if db_sale.user:
            session.refresh(db_sale.user)

    except Exception as e:
        session.rollback()
        print(f"Error cancelling sale: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error cancelling sale: {str(e)}")

    return db_sale

app.include_router(sales_router)

# --- User Specific Data Router (e.g., Sales History) ---
user_data_router = APIRouter(
    prefix="/api/users",
    tags=["User Data"]
    # Consider adding dependencies=[Depends(get_current_active_user)] if all routes here are protected
)

from .database import Sale, SaleRead # This import might be redundant if already imported globally for other routers

@user_data_router.get("/{user_id}/sales/", response_model=List[SaleRead])
async def get_user_sales_history(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user), # For authorization
    skip: int = 0,
    limit: int = 100
):
    # Authorization: Admin can see any user's sales. Regular user can only see their own.
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this resource")

    # Check if the target user exists
    target_user = session.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    sales_query = select(Sale).where(Sale.user_id == user_id).offset(skip).limit(limit)
    sales_history = session.exec(sales_query).all()

    # Sale model instances should be directly compatible with SaleRead if fields match
    return sales_history

app.include_router(user_data_router)


# --- Shopping Cart Router ---
cart_router = APIRouter(
    prefix="/api/me/cart",
    tags=["My Cart"],
    dependencies=[Depends(get_current_active_user)]
)

def get_or_create_cart(user_id: int, session: Session) -> Cart:
    cart = session.exec(select(Cart).where(Cart.user_id == user_id)).first()
    if not cart:
        cart = Cart(user_id=user_id, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
        session.add(cart)
        session.commit()
        session.refresh(cart)
    return cart

@cart_router.get("/", response_model=CartRead)
def get_my_cart(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    cart = get_or_create_cart(user_id=current_user.id, session=session)
    # Access items to ensure they are loaded for CartRead, especially for the computed field.
    # SQLModel's behavior with Pydantic serialization might handle this, but explicit access is safer.
    if cart.items: # This access helps in populating items for the response model
        pass
    return cart

@cart_router.post("/items/", response_model=CartRead)
def add_item_to_cart(
    item_in: CartItemCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    cart = get_or_create_cart(user_id=current_user.id, session=session)

    product = session.get(Product, item_in.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # TODO: Check product stock if stock_actual is relevant for cart addition
    # if product.stock_actual < item_in.quantity:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough stock")

    existing_cart_item = session.exec(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == item_in.product_id)
    ).first()

    if existing_cart_item:
        existing_cart_item.quantity += item_in.quantity # Add to existing quantity
        # price_at_addition remains from the first time it was added.
    else:
        existing_cart_item = CartItem(
            cart_id=cart.id,
            product_id=item_in.product_id,
            quantity=item_in.quantity,
            price_at_addition=product.price_revista, # Store current price_revista
            added_at=datetime.now(timezone.utc)
        )

    # Ensure quantity is positive (gt=0 is on Pydantic model, but defensive check after +=)
    if existing_cart_item.quantity <= 0:
        # This case should not be reached if CartItemCreate.quantity is always > 0
        # and we are only adding. If item_in.quantity could be negative, then this makes sense.
        # For current design, item_in.quantity is positive.
        session.delete(existing_cart_item)
    else:
        session.add(existing_cart_item)

    cart.updated_at = datetime.now(timezone.utc)
    session.add(cart)

    try:
        session.commit()
        session.refresh(cart)
        # Refresh items and their products for the response
        for item_in_cart in cart.items:
            session.refresh(item_in_cart)
            if item_in_cart.product: # Ensure product is loaded for CartItemRead
                pass
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")

    return cart

@cart_router.put("/items/{product_id}/", response_model=CartRead)
def update_cart_item_quantity(
    product_id: int,
    item_update: CartItemUpdate, # Contains new quantity (validated > 0 by Pydantic)
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    cart = get_or_create_cart(user_id=current_user.id, session=session)

    cart_item = session.exec(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product_id)
    ).first()

    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    cart_item.quantity = item_update.quantity # quantity is > 0 due to CartItemUpdate model

    cart.updated_at = datetime.now(timezone.utc)
    session.add(cart_item)
    session.add(cart)
    session.commit()
    session.refresh(cart)
    for item_in_cart in cart.items: session.refresh(item_in_cart) # Ensure items are refreshed
    return cart

@cart_router.delete("/items/{product_id}/", response_model=CartRead)
def remove_cart_item(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    cart = get_or_create_cart(user_id=current_user.id, session=session)

    cart_item = session.exec(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product_id)
    ).first()

    if not cart_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    session.delete(cart_item)
    cart.updated_at = datetime.now(timezone.utc)
    session.add(cart)
    session.commit()
    session.refresh(cart)
    return cart

@cart_router.delete("/", response_model=CartRead)
def clear_my_cart(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    cart = get_or_create_cart(user_id=current_user.id, session=session)

    # Cascade delete for items is set on Cart.items relationship.
    # Deleting items individually and then committing is safer/more explicit for some ORMs or DBs.
    for item in list(cart.items): # Iterate over a copy
        session.delete(item)

    cart.updated_at = datetime.now(timezone.utc)
    # cart.items should be empty now for the response model after refresh
    session.add(cart)
    session.commit()
    session.refresh(cart)
    return cart

app.include_router(cart_router)
