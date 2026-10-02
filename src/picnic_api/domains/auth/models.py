from picnic_api.models.common import PicnicModel


class LoginResult(PicnicModel):
    user_id: str
    second_factor_authentication_required: bool
    show_second_factor_authentication_intro: bool
    auth_key: str


class Verify2FAResult(PicnicModel):
    auth_key: str
