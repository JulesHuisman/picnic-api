from pydantic import TypeAdapter

from picnic_api.domains.payment.models import PaymentProfile, WalletTransaction, WalletTransactionDetails
from picnic_api.http_client import HttpClient

WALLET_TRANSACTIONS = TypeAdapter(list[WalletTransaction])


class PaymentService:
    """Payment profile and wallet transactions."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    async def get_payment_profile(self) -> PaymentProfile:
        """Returns the payment profile."""
        return PaymentProfile.model_validate(
            obj=await self._http.send_request(method="GET", path="/payment-profile", include_picnic_headers=True)
        )

    async def get_wallet_transactions(self, page_number: int) -> list[WalletTransaction]:
        """Returns a page of wallet transactions. Pages start at 1."""
        return WALLET_TRANSACTIONS.validate_python(
            await self._http.send_request(method="POST", path="/wallet/transactions", data={"page_number": page_number})
        )

    async def get_wallet_transaction_details(self, wallet_transaction_id: str) -> WalletTransactionDetails:
        """Returns the details of a wallet transaction."""
        return WalletTransactionDetails.model_validate(
            obj=await self._http.send_request(method="GET", path=f"/wallet/transactions/{wallet_transaction_id}")
        )
