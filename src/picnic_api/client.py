import httpx

from picnic_api.domains.app.service import AppService
from picnic_api.domains.auth.service import AuthService
from picnic_api.domains.cart.service import CartService
from picnic_api.domains.catalog.service import CatalogService
from picnic_api.domains.consent.service import ConsentService
from picnic_api.domains.content.service import ContentService
from picnic_api.domains.customer_service.service import CustomerServiceService
from picnic_api.domains.delivery.service import DeliveryService
from picnic_api.domains.payment.service import PaymentService
from picnic_api.domains.recipe.service import RecipeService
from picnic_api.domains.user.service import UserService
from picnic_api.domains.user_onboarding.service import UserOnboardingService
from picnic_api.http_client import DEFAULT_AGENT, DEFAULT_API_VERSION, DEFAULT_DEVICE_ID, HttpClient
from picnic_api.models.common import CountryCode


class PicnicClient(HttpClient):
    """Async client for the Picnic API, grouping the endpoints into domain services.

    All options are optional. `auth_key` skips the login step, `url` overrides the default
    `https://storefront-prod.<country>.picnicinternational.com/api/<api_version>`, `device_id` and `agent` set
    the `x-picnic-did` and `x-picnic-agent` headers, and `session` injects a custom `httpx.AsyncClient`.
    """

    def __init__(
        self,
        *,
        country_code: CountryCode = "NL",
        api_version: str = DEFAULT_API_VERSION,
        auth_key: str | None = None,
        url: str | None = None,
        device_id: str = DEFAULT_DEVICE_ID,
        agent: str = DEFAULT_AGENT,
        session: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            country_code=country_code,
            api_version=api_version,
            auth_key=auth_key,
            url=url,
            device_id=device_id,
            agent=agent,
            session=session,
        )
        self.app = AppService(http=self)
        self.auth = AuthService(http=self)
        self.user = UserService(http=self)
        self.catalog = CatalogService(http=self)
        self.cart = CartService(http=self)
        self.delivery = DeliveryService(http=self)
        self.payment = PaymentService(http=self)
        self.consent = ConsentService(http=self)
        self.customer_service = CustomerServiceService(http=self)
        self.content = ContentService(http=self)
        self.user_onboarding = UserOnboardingService(http=self)
        self.recipe = RecipeService(http=self)
