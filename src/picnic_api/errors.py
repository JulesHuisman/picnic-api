from typing import Any

from picnic_api.models.rsc import PageFormat

AGE_VERIFICATION_TYPE = "LEGACY_ALCOHOL_AGE_VERIFICATION_REQUIRED"
CART_HAS_ISSUES = "CART_HAS_ISSUES"
DEFAULT_ISSUE_MESSAGE = "Cart has issues"


class PicnicError(Exception):
    """Raised when the Picnic API rejects a request or returns unusable data."""


class CheckoutIssueError(PicnicError):
    """Raised when the cart cannot proceed to checkout (e.g. alcohol age check or minimum order value)."""

    def __init__(
        self, *, code: str, title: str, issue_message: str, resolve_key: str, blocking: bool, issue_type: str
    ) -> None:
        super().__init__(issue_message or title or code)
        self.code = code
        self.title = title
        self.issue_message = issue_message
        self.resolve_key = resolve_key
        self.blocking = blocking
        self.issue_type = issue_type

    def is_age_verification_issue(self) -> bool:
        """Returns whether the issue is the alcohol age check, which can be resolved with `resolve_key`."""
        return self.issue_type == AGE_VERIFICATION_TYPE


class UnexpectedPageFormatError(PicnicError):
    """Raised when a page is served as Fusion while RSC was expected, or the other way around.

    Which format Picnic serves depends on the page and the `x-picnic-agent` version, so use the method
    that matches `received_format`.
    """

    def __init__(self, *, page_id: str, received_format: PageFormat) -> None:
        method = "app.get_rsc_page" if received_format == "rsc" else "app.get_page"
        served_as = "an RSC payload" if received_format == "rsc" else "a Fusion page"
        super().__init__(f'Page "{page_id}" was served as {served_as}; use {method} to fetch it.')
        self.page_id = page_id
        self.received_format = received_format


def parse_checkout_issue_error(body: Any) -> CheckoutIssueError | None:
    """Builds a `CheckoutIssueError` from an error response body, or returns None when it is not a cart issue."""
    if not isinstance(body, dict):
        return None
    error = body.get("error")
    nested: dict[str, Any] = error if isinstance(error, dict) else {}
    code = _coalesce(body.get("code"), nested.get("code"))
    if code != CART_HAS_ISSUES:
        return None

    message = _coalesce(body.get("message"), nested.get("message"))
    details = _coalesce(body.get("details"), nested.get("details"))
    if not isinstance(details, dict):
        return CheckoutIssueError(
            code=CART_HAS_ISSUES,
            title=message or DEFAULT_ISSUE_MESSAGE,
            issue_message=message or DEFAULT_ISSUE_MESSAGE,
            resolve_key="",
            blocking=True,
            issue_type="UNKNOWN",
        )

    blocking = details.get("blocking")
    return CheckoutIssueError(
        code=CART_HAS_ISSUES,
        title=details.get("localized_title") or DEFAULT_ISSUE_MESSAGE,
        issue_message=details.get("localized_message") or message or DEFAULT_ISSUE_MESSAGE,
        resolve_key=details.get("resolve_key") or "",
        blocking=True if blocking is None else blocking,
        issue_type=details.get("type") or "UNKNOWN",
    )


def _coalesce(first: Any, second: Any) -> Any:
    return first if first is not None else second
