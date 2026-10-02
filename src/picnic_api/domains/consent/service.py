from urllib.parse import urlencode

from pydantic import TypeAdapter

from picnic_api.domains.consent.models import (
    ConsentRequest,
    ConsentSetting,
    ConsentTopic,
    ConsentTopicsStrategy,
    SetConsentSettingsInput,
    SetConsentSettingsResult,
    SetGeneralConsentsInput,
)
from picnic_api.http_client import HttpClient

CONSENT_SETTINGS = TypeAdapter(list[ConsentSetting])
CONSENT_REQUESTS = TypeAdapter(list[ConsentRequest])


class ConsentService:
    """Consent settings and GDPR declarations."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def get_consent_settings(self, general: bool = False) -> list[ConsentSetting]:
        """Returns the consent settings, or only the general ones when `general` is set."""
        path = "/consents/general/settings-page" if general else "/consents/settings-page"
        return CONSENT_SETTINGS.validate_python(self._http.send_request(method="GET", path=path))

    def set_consent_settings(self, consent_settings: SetConsentSettingsInput) -> SetConsentSettingsResult:
        """Sets one or more consent declarations."""
        return SetConsentSettingsResult.model_validate(
            obj=self._http.send_request(method="PUT", path="/consents", data=consent_settings.model_dump())
        )

    def get_consents(self, consent_topics: list[ConsentTopic], strategy: ConsentTopicsStrategy) -> list[ConsentRequest]:
        """Returns the consent requests for the given topic keys and strategy."""
        query = urlencode(query=[("consent_topics", topic) for topic in consent_topics] + [("strategy", strategy)])
        return CONSENT_REQUESTS.validate_python(self._http.send_request(method="GET", path=f"/consents?{query}"))

    def get_general_consents(self) -> ConsentRequest:
        """Returns the general consent request."""
        return ConsentRequest.model_validate(obj=self._http.send_request(method="GET", path="/consents/general"))

    def set_general_consents(self, declarations: SetGeneralConsentsInput) -> None:
        """Updates the general consent declarations."""
        self._http.send_request(method="PUT", path="/consents/general", data=declarations.model_dump())
