from typing import Any

from picnic_api.domains.cart.models import OrderLine
from picnic_api.models.common import PicnicModel


class BankInformation(PicnicModel):
    bank_id: str
    name: str


class AvailablePaymentMethod(PicnicModel):
    available_banks: list[BankInformation] | None = None
    payment_method: str


class PaymentMethodBrand(PicnicModel):
    brand: str
    display_name: str
    icon_url: str


class PaymentMethod(PicnicModel):
    brands: list[PaymentMethodBrand]
    data: dict[str, Any]
    display_name: str
    icon_url: str
    payment_method: str
    visibility: str
    visibility_reason: str | None


class StoredPaymentOption(PicnicModel):
    account: str | None
    brand: str
    display_name: str
    icon_url: str
    id: str
    payment_method: str


class PaymentProfile(PicnicModel):
    available_payment_method_item: Any | None
    available_payment_methods: list[AvailablePaymentMethod]
    checkout_banner: Any | None
    payment_methods: list[PaymentMethod]
    preferred_payment_option_id: str
    stored_payment_options: list[StoredPaymentOption]


class WalletTransaction(PicnicModel):
    account: str
    amount_in_cents: int
    brand: str
    display_name: str
    domains: list[str]
    icon_url: str
    id: str
    status: str
    timestamp: int
    transaction_method: str
    transaction_type: str


class ReturnedContainer(PicnicModel):
    localized_name: str
    price: int
    quantity: int
    type: str


class Deposit(PicnicModel):
    count: int
    type: str
    value: int


class WalletTransactionDetails(PicnicModel):
    amount_in_cents: int
    article_issue_refunds: list[Any]
    debt_resolution: Any | None
    delivery_debt: Any | None
    delivery_id: str
    deposits: list[Deposit]
    fees: list[Any]
    payment_execution_timestamp: int
    payment_method_icon_url: str
    payment_option_account: str
    payment_option_display_name: str
    refunded_items: list[Any]
    returned_containers: list[ReturnedContainer]
    shop_items: list[OrderLine]
    transaction_method: str
    transaction_status: str
    transaction_type: str
