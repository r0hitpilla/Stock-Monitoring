from pydantic import BaseModel


class OtpRequestSchema(BaseModel):
    phone_number: str


class OtpVerifySchema(BaseModel):
    phone_number: str
    code: str


class RefreshRequestSchema(BaseModel):
    refresh_token: str


class TokenPairSchema(BaseModel):
    access_token: str
    refresh_token: str
