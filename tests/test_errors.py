from picnic_api import CheckoutIssueError, UnexpectedPageFormatError
from picnic_api.errors import parse_checkout_issue_error


def test_returns_none_for_non_cart_errors() -> None:
    assert parse_checkout_issue_error(body={"code": "OTHER"}) is None
    assert parse_checkout_issue_error(body=None) is None
    assert parse_checkout_issue_error(body="CART_HAS_ISSUES") is None


def test_parses_age_verification_issue() -> None:
    issue = parse_checkout_issue_error(
        body={
            "code": "CART_HAS_ISSUES",
            "message": "Cart has issues",
            "details": {
                "type": "LEGACY_ALCOHOL_AGE_VERIFICATION_REQUIRED",
                "localized_title": "Altersprüfung",
                "localized_message": "Du musst 18+ sein",
                "resolve_key": "age_verified",
                "blocking": False,
            },
        }
    )

    assert isinstance(issue, CheckoutIssueError)
    assert issue.is_age_verification_issue()
    assert issue.resolve_key == "age_verified"
    assert issue.blocking is False
    assert issue.title == "Altersprüfung"
    assert str(issue) == "Du musst 18+ sein"


def test_parses_blocking_issue_from_nested_error_body() -> None:
    issue = parse_checkout_issue_error(
        body={
            "error": {
                "code": "CART_HAS_ISSUES",
                "message": "Minimum not reached",
                "details": {
                    "type": "MINIMUM_ORDER_VALUE_NOT_REACHED",
                    "localized_title": "Mindestbestellwert",
                    "localized_message": "Noch 5 Euro fehlen",
                    "resolve_key": "",
                    "blocking": True,
                },
            }
        }
    )

    assert issue is not None
    assert issue.blocking is True
    assert issue.issue_type == "MINIMUM_ORDER_VALUE_NOT_REACHED"
    assert not issue.is_age_verification_issue()


def test_defaults_when_details_are_missing_or_partial() -> None:
    without_details = parse_checkout_issue_error(body={"error": {"code": "CART_HAS_ISSUES", "message": "Nope"}})
    assert without_details is not None
    assert (without_details.title, without_details.issue_message) == ("Nope", "Nope")
    assert (without_details.blocking, without_details.issue_type, without_details.resolve_key) == (True, "UNKNOWN", "")

    partial = parse_checkout_issue_error(body={"code": "CART_HAS_ISSUES", "message": "Fallback", "details": {}})
    assert partial is not None
    assert (partial.title, partial.issue_message, partial.blocking) == ("Cart has issues", "Fallback", True)


def test_unexpected_page_format_error_names_the_right_method() -> None:
    rsc = UnexpectedPageFormatError(page_id="category-tree-root", received_format="rsc")
    fusion = UnexpectedPageFormatError(page_id="home_page_root", received_format="fusion")

    assert str(rsc) == 'Page "category-tree-root" was served as an RSC payload; use app.get_rsc_page to fetch it.'
    assert str(fusion) == 'Page "home_page_root" was served as a Fusion page; use app.get_page to fetch it.'
    assert (rsc.page_id, rsc.received_format) == ("category-tree-root", "rsc")
