import datetime
import logging
import os
import shutil
from typing import Any, Optional, Union

import pyotp
from chatgpt_automation import (
    ChatGPTAutomationService,
    ChatGPTAutomationSettings,
    ask_chatgpt,
)
from config import Settings
from database import (
    SessionLocal,  # Your SQLAlchemy session factory
    engine,
)
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import ExpiredSignatureError, JWTError, jwt

# Assuming models.py defines your Base and classes
from models import Base, Receipt, ReceiptItem, User
from passlib.context import CryptContext
from schemas import (
    APIResponse,
    ChatGPTAskSuccess,
    ChatGPTLoginCheckSuccess,
    GetUsersSuccess,
    LogoutSuccess,
    ProtectedSuccess,
    ReceiptItemsSuccess,
    ReceiptSchema,
    ReceiptsSuccess,
    RefreshTokenRequest,
    RegisterSuccess,
    TwoFASetupSuccess,
    TwoFAVerifySuccess,
    UploadReceiptSuccess,
    UserToken,
)
from sqlalchemy import String, and_, asc, desc, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

Base.metadata.create_all(bind=engine)

app = FastAPI()
settings = Settings()

UPLOAD_DIR = settings.get("UPLOAD_DIR")
os.makedirs(UPLOAD_DIR, exist_ok=True)
SECRET_KEY = settings.get("SECRET_KEY")
ALGORITHM = "HS256"
CHATGPT_PROJECT_URL = settings.get("CHATGPT_PROJECT_URL")
EMAIL = settings.get("EMAIL")
PASSWORD = settings.get("PASSWORD")
CHATGPT_PROFILE_DIR = settings.get("PROMPTBRANCH_PROFILE_DIR") or settings.get("CHATGPT_PROFILE_DIR", "/app/.pb_profile")
CHATGPT_HEADLESS = str(settings.get("CHATGPT_HEADLESS", "0")).strip().lower() in {"1", "true", "yes", "on"}
CHATGPT_USE_PATCHRIGHT = str(settings.get("CHATGPT_USE_PATCHRIGHT", "1")).strip().lower() in {"1", "true", "yes", "on"}
CHATGPT_BROWSER_CHANNEL = settings.get("CHATGPT_BROWSER_CHANNEL", "chrome")
CHATGPT_PASSWORD_FILE = settings.get("CHATGPT_PASSWORD_FILE")
CHATGPT_DISABLE_FEDCM = str(settings.get("CHATGPT_DISABLE_FEDCM", "1")).strip().lower() in {"1", "true", "yes", "on"}
CHATGPT_FILTER_NO_SANDBOX = str(settings.get("CHATGPT_FILTER_NO_SANDBOX", "0")).strip().lower() in {"1", "true", "yes", "on"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

chatgpt_browser_service = ChatGPTAutomationService(
    ChatGPTAutomationSettings(
        project_url=CHATGPT_PROJECT_URL,
        email=EMAIL,
        password=PASSWORD,
        profile_dir=CHATGPT_PROFILE_DIR,
        headless=CHATGPT_HEADLESS,
        use_patchright=CHATGPT_USE_PATCHRIGHT,
        browser_channel=CHATGPT_BROWSER_CHANNEL,
        password_file=CHATGPT_PASSWORD_FILE,
        disable_fedcm=CHATGPT_DISABLE_FEDCM,
        filter_no_sandbox=CHATGPT_FILTER_NO_SANDBOX,
        max_retries=int(settings.get("CHATGPT_MAX_RETRIES", 2)),
        retry_backoff_seconds=float(settings.get("CHATGPT_RETRY_BACKOFF_SECONDS", 2.0)),
    )
)


def _build_receipt_prompt(file_name: str, current_date: datetime.datetime) -> str:
    return f"""
[#image:{file_name}]
{current_date}

You are an OCR-to-JSON conversion assistant. Your goal is to produce exactly one machine-readable JSON object matching the receipt model below.

STRICT RULES:
- The top-level JSON must contain the key "receipt".
- Field names must match this structure exactly:
  receipt.is_receipt
  receipt.file_name
  receipt.shop_name
  receipt.shop_address
  receipt.scan_datetime
  receipt.receipt_datetime
  receipt.subtotal
  receipt.total
  receipt.payment_method
  receipt.items[]
  receipt.items[].description
  receipt.items[].currency
  receipt.items[].quantity
  receipt.items[].unit_price
  receipt.items[].total_price
- shop_name must be short and replace spaces with underscores.
- Include every detected item on the receipt.
- If no item lines are readable, return one fallback item with zero values.
- All datetime fields must use the format %Y-%m-%dT%H:%M:%S.
- Do not return prose. Return JSON only.
"""


def _chatgpt_error_response(exc: Exception) -> APIResponse:
    error_text = str(exc)
    lower = error_text.lower()
    if "manual login" in lower or "saved session" in lower:
        return api_error(
            "ChatGPT browser session is not logged in. Run the login-check route in headed mode first to seed the persistent profile."
        )
    if "cloudflare" in lower or "challenge" in lower:
        return api_error(
            "ChatGPT browser automation hit a browser challenge. Retry in headed mode or reuse an already authenticated profile."
        )
    return api_error(f"ChatGPT browser automation failed: {exc}")


def replace_dots_with_underscores(input_str: Optional[str]) -> str:
    value = "" if input_str is None else str(input_str)
    return value.replace(".", "_")


def _safe_string(value, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_float(value, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _normalize_receipt_items(items_value):
    if not isinstance(items_value, list):
        return []

    normalized_items = []
    for item in items_value:
        if not isinstance(item, dict):
            continue
        normalized_items.append(
            {
                "description": _safe_string(item.get("description"), "unknown_item"),
                "currency": _safe_string(item.get("currency"), "EUR"),
                "quantity": _safe_int(item.get("quantity"), 1),
                "unit_price": _safe_float(item.get("unit_price"), 0.0),
                "total_price": _safe_float(item.get("total_price"), 0.0),
            }
        )
    return normalized_items


def normalize_chatgpt_receipt_payload(payload: dict, file_name: str, scan_dt: datetime.datetime) -> dict:
    if not isinstance(payload, dict):
        payload = {}

    receipt_payload = payload.get("receipt") if isinstance(payload.get("receipt"), dict) else None

    if receipt_payload is None:
        looks_like_item = any(
            key in payload for key in ("description", "quantity", "unit_price", "total_price")
        )
        if looks_like_item:
            receipt_payload = {
                "is_receipt": False,
                "file_name": file_name,
                "shop_name": "unknown",
                "shop_address": "unknown",
                "scan_datetime": scan_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "receipt_datetime": scan_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "subtotal": _safe_float(payload.get("total_price"), 0.0),
                "total": _safe_float(payload.get("total_price"), 0.0),
                "payment_method": "",
                "items": [
                    {
                        "description": _safe_string(payload.get("description"), "unknown_item"),
                        "currency": _safe_string(payload.get("currency"), "EUR"),
                        "quantity": _safe_int(payload.get("quantity"), 1),
                        "unit_price": _safe_float(payload.get("unit_price"), 0.0),
                        "total_price": _safe_float(payload.get("total_price"), 0.0),
                    }
                ],
            }
        else:
            receipt_payload = payload

    if not isinstance(receipt_payload, dict):
        receipt_payload = {}

    normalized = {
        "is_receipt": bool(receipt_payload.get("is_receipt", False)),
        "file_name": _safe_string(receipt_payload.get("file_name"), file_name),
        "shop_name": _safe_string(receipt_payload.get("shop_name"), "unknown"),
        "shop_address": _safe_string(receipt_payload.get("shop_address"), "unknown"),
        "scan_datetime": _safe_string(
            receipt_payload.get("scan_datetime"), scan_dt.strftime("%Y-%m-%dT%H:%M:%S")
        ),
        "receipt_datetime": _safe_string(
            receipt_payload.get("receipt_datetime"), scan_dt.strftime("%Y-%m-%dT%H:%M:%S")
        ),
        "subtotal": _safe_float(receipt_payload.get("subtotal"), 0.0),
        "total": _safe_float(receipt_payload.get("total"), 0.0),
        "payment_method": _safe_string(receipt_payload.get("payment_method"), ""),
        "items": _normalize_receipt_items(receipt_payload.get("items")),
    }

    if not normalized["items"]:
        normalized["items"] = [
            {
                "description": "unknown_item",
                "currency": "EUR",
                "quantity": 1,
                "unit_price": 0.0,
                "total_price": 0.0,
            }
        ]

    return {"receipt": normalized}


def set_receipt_datetime(dt_string):
    # Define the strict format
    # strict_format = "%Y-%m-%d %H:%M:%S"  # Example: 2025-07-12 14:30:00
    # strict_format = "%Y-%m-%d %H:%M"  # Example: 2025-07-12 14:30:00
    strict_format = "%Y-%m-%dT%H:%M:%S"

    # Validate the date format
    try:
        return datetime.datetime.strptime(dt_string, strict_format)
    except ValueError:
        raise ValueError(f"Incorrect date format, should be {strict_format}")


def api_success(
    message: Optional[str] = None, data: Optional[dict] = None, **kwargs
) -> APIResponse:
    logger.debug(
        f"api_success called with message={message!r}, data={data!r}, kwargs={kwargs!r}"
    )
    response = APIResponse(
        success=True, code="success", message=message, data=data, **kwargs
    )
    logger.debug(f"api_success returning response: {response.json()}")
    return response


def api_error(error: str, **kwargs) -> APIResponse:
    logger.debug(f"api_error called with error={error!r}, kwargs={kwargs!r}")
    response = APIResponse(success=False, code="error", error=error, **kwargs)
    logger.debug(f"api_error returning response: {response.json()}")
    return response


def api_duplicate(
    message: Optional[str] = "Duplicate receipt detected. Skipping save.",
    receipt_id: Optional[int] = None,
    **kwargs,
) -> APIResponse:
    logger.debug(
        f"api_duplicate called with message={message!r}, receipt_id={receipt_id!r}, kwargs={kwargs!r}"
    )
    response = APIResponse(
        success=False,
        code="duplicate",
        duplicate=True,
        message=message,
        receipt_id=receipt_id,
        **kwargs,
    )
    logger.debug(f"api_duplicate returning response: {response.json()}")
    return response


def is_dir_empty(dir_path):
    """Return True if directory exists and is empty."""
    return os.path.isdir(dir_path) and not os.listdir(dir_path)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None):
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + (
        expires_delta or datetime.timedelta(minutes=15)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        logger.info(f"get_current_user token {token}")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.error("get_current_user error no User found")
            raise credentials_exception
    except JWTError as e:
        logger.error(f"Error get_current_user:  {e}")
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    return user


@app.get("/secrets")
def get_secrets(current_user: User = Depends(get_current_user)):
    # Obfuscate secret values for demo purposes
    secrets = settings.all()
    obfuscated = {k: "*" * len(v) if v else None for k, v in secrets.items()}
    return obfuscated


@app.get("/", response_model=dict)
def read_root():
    return {"message": "Receipt backend is up ver 0.0.2!"}


@app.post("/register", response_model=Union[RegisterSuccess, APIResponse])
def register(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(User.username == form_data.username).first()
        if user:
            return api_error("User already exists")
        hashed_pw = hash_password(form_data.password)
        new_user = User(username=form_data.username, hashed_password=hashed_pw)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return api_success(message="User registered successfully")
    except Exception as e:
        logger.exception("Registration failed")
        return api_error(e)


@app.post("/login", response_model=Union[UserToken, APIResponse])
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            return api_error("Invalid credentials")
        access_token = create_access_token({"sub": user.username})
        refresh_token = create_refresh_token({"sub": user.username})

        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

        logger.debug(data)
        return api_success("Login successful", data=data)
    except Exception as e:
        logger.exception("Login failed")
        return api_error(e)


@app.post("/token/refresh", response_model=Union[UserToken, APIResponse])
def refresh_token(request: RefreshTokenRequest):
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return api_error("Invalid refresh token")
        new_access_token = create_access_token({"sub": username})
        new_refresh_token = create_refresh_token({"sub": username})
        return api_success(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )
    except ExpiredSignatureError:
        logger.exception("Refresh token expired")
        return api_error("Refresh token expired")
    except JWTError:
        logger.exception("Invalid refresh token")
        return api_error("Invalid refresh token")
    except Exception as e:
        logger.exception("Unexpected error in token refresh")
        return api_error(e)


@app.post("/logout", response_model=Union[LogoutSuccess, APIResponse])
def logout(current_user: User = Depends(get_current_user)):
    try:
        return api_success(message="Logged out successfully")
    except Exception as e:
        logger.exception("Logout failed")
        return api_error(e)


@app.post("/2fa/setup", response_model=Union[TwoFASetupSuccess, APIResponse])
def setup_2fa(username: str, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return api_error("User not found")
        secret = pyotp.random_base32()
        user.otp_enabled = True
        user.otp_secret = secret
        db.commit()
        uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username, issuer_name="MyApp"
        )
        return api_success(message="2FA setup successful", otpauth_url=uri)
    except Exception as e:
        logger.exception("2FA setup failed")
        return api_error(e)


@app.post("/2fa/verify", response_model=Union[TwoFAVerifySuccess, APIResponse])
def verify_2fa(username: str, otp: str, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.otp_secret:
            raise HTTPException(status_code=404, detail="2FA not set up")
        totp = pyotp.TOTP(user.otp_secret)
        if totp.verify(otp):
            return api_success(message="2FA verified")
        else:
            return api_error("Invalid OTP")
    except Exception as e:
        logger.exception("2FA verification failed")
        return api_error(e)


@app.get("/protected", response_model=Union[ProtectedSuccess, APIResponse])
def protected_route(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return api_success(message=f"Hello, {username}. This is a protected route!")
    except ExpiredSignatureError:
        logger.exception("Access token expired")
        return api_error("Access token expired")
    except JWTError:
        logger.exception("Invalid access token")
        return api_error("Invalid access token")
    except Exception as e:
        logger.exception("Protected route error")
        return api_error(e)


@app.get("/users", response_model=Union[GetUsersSuccess, APIResponse])
def get_all_users(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    try:
        users = db.query(User).all()
        return api_success(users=users)
    except Exception as e:
        logger.exception("Fetching users failed")
        return api_error(e)


@app.post("/chatgpt/browser/login-check", response_model=Union[ChatGPTLoginCheckSuccess, APIResponse])
async def chatgpt_browser_login_check(
    current_user: User = Depends(get_current_user),
    keep_open: bool = Query(False),
):
    try:
        result = await chatgpt_browser_service.run_login_check(keep_open=keep_open)
        return ChatGPTLoginCheckSuccess(
            success=True,
            code="success",
            message="ChatGPT browser login check completed.",
            data=result,
        )
    except Exception as e:
        logger.exception("ChatGPT browser login check failed")
        return _chatgpt_error_response(e)


@app.post("/chatgpt/browser/ask", response_model=Union[ChatGPTAskSuccess, APIResponse])
async def chatgpt_browser_ask(
    current_user: User = Depends(get_current_user),
    prompt: str = Form(...),
    expect_json: bool = Form(False),
    keep_open: bool = Form(False),
    file: Optional[UploadFile] = File(None),
):
    temp_file_path: Optional[str] = None
    try:
        if file and file.filename:
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
            temp_file_name = f"chatgpt_browser_{timestamp}_{file.filename}"
            temp_file_path = os.path.join(UPLOAD_DIR, temp_file_name)
            with open(temp_file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

        answer = await chatgpt_browser_service.ask_question(
            prompt=prompt,
            file_path=temp_file_path,
            expect_json=expect_json,
            keep_open=keep_open,
        )
        return ChatGPTAskSuccess(
            success=True,
            code="success",
            message="ChatGPT browser ask completed.",
            answer=answer,
            data={
                "used_file": bool(temp_file_path),
                "expect_json": expect_json,
            },
        )
    except Exception as e:
        logger.exception("ChatGPT browser ask failed")
        return _chatgpt_error_response(e)
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.post("/receipt/upload", response_model=Union[UploadReceiptSuccess, APIResponse])
async def upload_receipt(
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    file_location = os.path.join(UPLOAD_DIR, f"{file.filename}")

    # Save file to disk
    try:
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        logger.exception("Failed to save uploaded file")
        return api_error(f"Failed to save file: {e}")

    current_date = datetime.datetime.now(datetime.timezone.utc)

    request_question = _build_receipt_prompt(file.filename, current_date)

    try:
        receipt_items_json = await chatgpt_browser_service.ask_question(
            prompt=request_question,
            file_path=file_location,
            expect_json=True,
        )
        print("returned receipt_items_json bt ask_chatgpt")
        print(receipt_items_json)
    except Exception as e:
        logger.exception("Error in ask_chatgpt")
        os.remove(file_location)
        return _chatgpt_error_response(e)

    # Check valid structure
    if not receipt_items_json:
        os.remove(file_location)
        return api_error("Failed to extract valid receipt data.")

    receipt_items_json = normalize_chatgpt_receipt_payload(
        receipt_items_json, file.filename, current_date
    )

    receipt_data = receipt_items_json["receipt"]

    if receipt_data.get("receipt_datetime", None):
        receipt_data["receipt_number"] = (
            f"{_safe_string(receipt_data.get('shop_name'), 'unknown')}_{replace_dots_with_underscores(receipt_data.get('total'))}_{set_receipt_datetime(receipt_data.get('receipt_datetime'))}"
        )
    else:
        receipt_data["receipt_number"] = (
            f"{_safe_string(receipt_data.get('shop_name'), 'unknown')}_{replace_dots_with_underscores(receipt_data.get('total'))}"
        )

    try:
        receipt = insert_receipt(
            receipt_data=receipt_items_json, file_name=file.filename, db=db
        )

        if receipt.get("duplicate"):
            return api_duplicate(
                f"Duplicate receipt found (ID: {receipt.get('duplicate_id', None)})",
                receipt_id=receipt.get("duplicate_id", None),
            )

    except Exception as e:
        os.remove(file_location)
        logger.exception("Failed to insert receipt")
        return api_error(f"Failed to insert receipt: {e}")

    # Success!
    return api_success(
        message="File uploaded and receipt saved",
        receipt_id=receipt.get("receipt_id", None),
        receipt_items_json=receipt_items_json,
    )


@app.get("/receipt/download/{file_name}", response_model=Union[None, APIResponse])
def download_receipt(
    file_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(file_name)
    # Ensure file exists in DB
    receipt = db.query(Receipt).filter(Receipt.file_name == file_name).first()
    if not receipt:
        logger.error("File not found in DB")
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "File not found in DB"},
        )

    # Build absolute file path
    file_path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.isfile(file_path):
        logger.error("File not found on disk")
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "File not found on disk"},
        )

    # Success: return file
    return FileResponse(
        file_path, filename=file_name, media_type="application/octet-stream"
    )


@app.get(
    "/receipt/items/{file_name}", response_model=Union[ReceiptItemsSuccess, APIResponse]
)
async def get_receipt_items(
    file_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # todo
    try:
        logger.info("get_receipt_receiptitems")
        logger.info(file_name)
        # Ensure file exists in DB
        receipt = db.query(Receipt).filter(Receipt.file_name == file_name).first()
        if not receipt:
            logger.error("File not found in DB")
            return api_error("File not found in DB")

        # receipt_items_json = await ask_chatgpt_to_get_json_data(file_name, db)
        # logger.info(receipt_items_json)

        # if not receipt_items_json:
        #     return api_error("No receipt items found.")

        # return api_success(items=receipt_items_json)
    except Exception as e:
        logger.exception("Error in get_receipt_items")
        return api_error(e)


@app.get("/receipts", response_model=Union[ReceiptsSuccess, APIResponse])
def get_receipts(
    lookup: Optional[str] = Query(None, description="Global search across all fields"),
    file_name: Optional[str] = Query(None),
    shop_name: Optional[str] = Query(None),
    shop_address: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    min_total: Optional[float] = Query(None),
    max_total: Optional[float] = Query(None),
    from_date: Optional[datetime.datetime] = Query(None, alias="from_date"),
    to_date: Optional[datetime.datetime] = Query(None, alias="to_date"),
    item_description: Optional[str] = Query(None),
    filter: str = Query("", description="Filter for receipt text"),
    sort: Optional[str] = Query(
        None, description="Sort by price/date, e.g., price_low_high, date_newest"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = db.query(Receipt).options(joinedload(Receipt.items))
        filters = []
        item_pattern = None
        # Determine if we need to join ReceiptItem table
        needs_item_join = False

        # --- GLOBAL LOOKUP FILTER (triggers for 3+ chars) ---
        if lookup and len(lookup) >= 1:
            pattern = f"%{lookup}%"
            filters.append(
                or_(
                    Receipt.file_name.ilike(pattern),
                    Receipt.shop_name.ilike(pattern),
                    Receipt.shop_address.ilike(pattern),
                    Receipt.payment_method.ilike(pattern),
                    Receipt.receipt_number.ilike(pattern),
                    Receipt.receipt_datetime.cast(String).ilike(pattern),
                    Receipt.scan_datetime.cast(String).ilike(pattern),
                    Receipt.total.cast(String).ilike(pattern),
                    Receipt.subtotal.cast(String).ilike(pattern),
                    ReceiptItem.description.ilike(pattern),
                )
            )
            needs_item_join = True
            item_pattern = pattern

        # --- FIELD-SPECIFIC FILTERS ---
        if file_name:
            filters.append(Receipt.file_name.ilike(f"%{file_name}%"))
        if shop_name:
            filters.append(Receipt.shop_name.ilike(f"%{shop_name}%"))
        if shop_address:
            filters.append(Receipt.shop_address.ilike(f"%{shop_address}%"))
        if payment_method:
            filters.append(Receipt.payment_method.ilike(f"%{payment_method}%"))
        if min_total is not None:
            filters.append(Receipt.total >= min_total)
        if max_total is not None:
            filters.append(Receipt.total <= max_total)
        if from_date:
            filters.append(Receipt.receipt_datetime >= from_date)
        if to_date:
            filters.append(Receipt.receipt_datetime <= to_date)
        if item_description:
            filters.append(ReceiptItem.description.ilike(f"%{item_description}%"))
            needs_item_join = True
            # override if specific item_description search
            item_pattern = f"%{item_description}%"

        # JOIN ReceiptItem only if needed
        if needs_item_join:
            query = query.outerjoin(Receipt.items)

        # Apply filters
        if filters:
            query = query.filter(and_(*filters))

        # --- SORTING ---
        if sort == "price_low_high":
            query = query.order_by(asc(Receipt.total))
        elif sort == "price_high_low":
            query = query.order_by(desc(Receipt.total))
        elif sort == "date_newest":
            query = query.order_by(desc(Receipt.receipt_datetime))
        elif sort == "date_oldest":
            query = query.order_by(asc(Receipt.receipt_datetime))
        elif sort == "scan_date_newest":
            query = query.order_by(desc(Receipt.scan_datetime))
        elif sort == "scan_date_oldest":
            query = query.order_by(asc(Receipt.scan_datetime))
        else:
            # Default: newest first
            query = query.order_by(desc(Receipt.receipt_datetime))

        receipts = query.all()

        # --- Filter items on each receipt if needed ---
        if item_pattern:

            def matches(desc: str, pat: str) -> bool:
                # pattern is e.g. %foo%
                return desc and pat[1:-1].lower() in desc.lower()

            filtered_receipts = []
            for receipt in receipts:
                original_items = receipt.items or []
                receipt.items = [
                    item
                    for item in original_items
                    if matches(item.description, item_pattern)
                ]
                if receipt.items:  # Only keep receipts with at least one matching item
                    filtered_receipts.append(receipt)
            receipts = filtered_receipts

        for receipt in receipts:
            logger.info(
                {k: v for k, v in receipt.__dict__.items() if k != "_sa_instance_state"}
            )

        return api_success(data=[ReceiptSchema.from_orm(r).dict() for r in receipts])
        # return api_success(data=receipts)

    except SQLAlchemyError as e:
        # Log the actual error internally (e.g., using logging module)
        logger.error(f"Database error: {e}")
        # Return generic error message to client
        return api_error("An internal database error occurred. Please try again later.")

    except Exception as e:
        # Catch-all for unexpected issues
        logger.error(f"Unexpected error: {e}")
        return api_error("An unexpected error occurred. Please contact support.")


def insert_receipt(receipt_data: dict, file_name: str, db: Session):
    logger.info(f"insert_receipt {file_name}")
    logger.info(f"receipt_data {receipt_data}")
    try:
        data = receipt_data["receipt"]
        receipt_number = data.get("receipt_number")

        # Check if similar receipt exists
        query = db.query(Receipt).filter(
            Receipt.receipt_number == receipt_number,
        )

        existing = query.first()

        if existing:
            logger.info(
                f"✅ Duplicate receipt found (ID: {existing.id}), skipping insert."
            )
            return {
                "success": False,
                "duplicate": True,
                "duplicate_id": existing.id,
            }  # Skip insert

        logger.info("going to create receipt data")
        # Create the Receipt object

        new_receipt = Receipt(
            is_receipt=data.get("is_receipt"),
            file_name=data.get("file_name"),
            shop_name=data.get("shop_name"),
            shop_address=data.get("shop_address"),
            receipt_datetime=data.get("receipt_datetime", ""),
            scan_datetime=data.get("scan_datetime", ""),
            receipt_number=data.get("receipt_number"),
            subtotal=data.get("subtotal"),
            total=data.get("total"),
            payment_method=data.get("payment_method"),
            uri=f"{UPLOAD_DIR}/{file_name}",
            type="image/jpeg",
        )
        db.add(new_receipt)
        db.flush()

        # Create ReceiptItem objects and link them
        for item_data in data.get("items", []):
            item = ReceiptItem(
                receipt_id=new_receipt.id,
                description=item_data["description"],
                currency=item_data["currency"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                total_price=item_data["total_price"],
            )
            logger.info(item)
            db.add(item)

        db.commit()
        db.refresh(new_receipt)
        logger.info(
            f"Inserted new receipt with ID: {new_receipt.id} for file {file_name}"
        )

        return {"receipt_id": new_receipt.id, "success": True, "duplicate": False}

    except Exception as e:
        db.rollback()
        logger.info(f"❌ Failed to insert receipt: {e}")


# --------------------------------------------------------------------
# --------------------------------------------------------------------
# -- archive
# --------------------------------------------------------------------
# --------------------------------------------------------------------
