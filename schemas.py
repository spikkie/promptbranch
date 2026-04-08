from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: int
    username: str
    otp_enabled: bool

    class Config:
        from_attributes = True


class ReceiptItemSchema(BaseModel):
    id: int
    receipt_id: int
    description: str
    currency: str
    quantity: int
    unit_price: float
    total_price: float

    class Config:
        from_attributes = True


class ReceiptSchema(BaseModel):
    id: int
    uri: str
    type: str
    is_receipt: bool
    file_name: str
    shop_name: str
    shop_address: Optional[str] = None
    # datetime: datetime
    # datetime: Optional[datetime] = None
    scan_datetime: datetime
    receipt_datetime: Optional[datetime]
    receipt_number: str
    subtotal: Optional[float] = None
    total: Optional[float] = None
    payment_method: Optional[str] = None
    items: List[ReceiptItemSchema]

    class Config:
        from_attributes = True


class UserToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# class APIError(BaseModel):
#     success: bool = False
#     error: str
#
#
# class APISuccess(BaseModel):
#     success: bool = True
#     message: Optional[str] = None
#
#
# class APIDuplicate(BaseModel):
#     success: bool = False
#     duplicate: bool = True
#     message: Optional[str] = "Duplicate receipt detected. Skipping save"
#     receicp_id: Optional[int] = None


class APIResponse(BaseModel):
    success: bool
    code: str  # "success", "error", "duplicate"
    message: Optional[str] = None
    error: Optional[str] = None
    duplicate: Optional[bool] = None
    receipt_id: Optional[int] = None
    data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = Field(
        default=None, description="Additional payload data"
    )




class ChatGPTLoginCheckSuccess(APIResponse):
    data: Optional[Dict[str, Any]] = None


class ChatGPTAskSuccess(APIResponse):
    answer: Union[Dict[str, Any], str, List[Any]]
    data: Optional[Dict[str, Any]] = None


class UploadReceiptSuccess(APIResponse):
    extracted_text: str
    receipt_items_json: Dict[str, Any]


class RegisterSuccess(APIResponse):
    pass  # just message


class LogoutSuccess(APIResponse):
    pass  # just message


class GetUsersSuccess(APIResponse):
    users: List[UserOut]


class ReceiptsSuccess(APIResponse):
    receipts: List[ReceiptSchema]


class ReceiptItemsSuccess(APIResponse):
    receipts: List[ReceiptSchema]


class TwoFASetupSuccess(APIResponse):
    otpauth_url: str


class TwoFAVerifySuccess(APIResponse):
    message: str = "2FA verified"


class ProtectedSuccess(APIResponse):
    message: str
