from typing import Literal

from pydantic import Field

from picnic_api.models.common import PicnicModel

type ConsentType = Literal["CONSENT_REQUEST", "CONSENT_SETTING", "CONSENT_PUSH"]

type ConsentTopicsStrategy = Literal["WIDE", "NARROW"]

type ConsentTopic = str


class ConsentSettingText(PicnicModel):
    title: str
    text: str
    dissent_text: str | None = None
    timestamp: str


class ConsentSetting(PicnicModel):
    type: ConsentType
    id: str
    text_id: str
    text_locale: str
    text: ConsentSettingText
    established_decision: bool
    initial_state: bool


class ConsentDeclaration(PicnicModel):
    consent_request_text_id: str
    consent_request_locale: str
    agreement: bool


class SetConsentSettingsInput(PicnicModel):
    consent_declarations: list[ConsentDeclaration]


class SetConsentSettingsResult(PicnicModel):
    consent_request_text_ids: list[str]


class ConsentFormattedContent(PicnicModel):
    text_html: str | None = Field(default=None, alias="text/html")
    text_plain: str | None = Field(default=None, alias="text/plain")
    dialog_flow: str | None = None


class ConsentRequest(PicnicModel):
    type: ConsentType
    id: str
    text_id: str
    text_locale: str
    formatted_content: ConsentFormattedContent | None = None
    timestamp: str | None = None


class SetGeneralConsentsInput(PicnicModel):
    consent_declarations: list[ConsentDeclaration]
    general_consent: bool
