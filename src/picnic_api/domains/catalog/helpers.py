import re
from typing import Any

from picnic_api.domains.catalog.models import (
    BundleItem,
    ProductDetails,
    ProductInfoSection,
    ProductPromotion,
    SimilarProduct,
)
from picnic_api.json_tree import find_all, iter_objects
from picnic_api.models.common import PicnicModel
from picnic_api.models.fusion import FusionPage, PriceRange

COLOR_MARKUP = re.compile(r"#\([A-Za-z0-9#_]+\)")
ALLERGEN_HEADING = re.compile(r"^bevat(\s+mogelijk)?$", re.IGNORECASE)
PRICE_RANGE_EXPRESSION_PARAMS = ("__ep1", "__ep2")


class ProductHeader(PicnicModel):
    """The texts at the top of the product details page."""

    name: str | None = None
    brand: str | None = None
    unit_quantity: str | None = None
    unit_price: str | None = None


def strip_color_markup(text: str) -> str:
    """Strips Picnic color markup like `#(#B40117)` from text."""
    return COLOR_MARKUP.sub("", text).strip()


def strip_markdown_formatting(text: str) -> str:
    """Strips bold and italic markers (`**`, `__`) from text."""
    return text.replace("**", "").replace("__", "")


def find_by_id(node: Any, node_id: str) -> dict[str, Any] | None:
    """Finds the node with the given `id` by following `child` and `children` links."""
    if not isinstance(node, dict):
        return None
    if node.get("id") == node_id:
        return node
    for key in ("child", "children"):
        value = node.get(key)
        for child in value if isinstance(value, list) else [value]:
            if found := find_by_id(node=child, node_id=node_id):
                return found
    return None


def extract_markdowns(node: Any) -> list[str]:
    """Returns all markdown strings in a node."""
    return [markdown for markdown in find_all(node=node, key="markdown") if isinstance(markdown, str)]


def extract_product_details(product_id: str, page: FusionPage) -> ProductDetails:
    """Extracts structured product details from a product details page."""
    raw = page.raw()
    body = raw["layout"]["body"]
    main_container = find_by_id(node=body, node_id="product-details-page-root-main-container")
    main_unit = next(
        (
            unit
            for unit in find_all(node=raw, key="sellingUnit")
            if isinstance(unit, dict) and unit.get("id") == product_id and "max_count" in unit
        ),
        {},
    )
    price_ranges = main_unit.get("price_ranges")
    max_count = main_unit.get("max_count")
    header = _extract_header(main_container=main_container)

    return ProductDetails(
        id=product_id,
        name=header.name or "",
        brand=header.brand,
        unit_quantity=header.unit_quantity or "",
        unit_price=header.unit_price,
        display_price=_extract_display_price(
            product_id=product_id, body=body, main_container=main_container, main_unit=main_unit
        ),
        max_count=max_count if max_count is not None else 0,
        image_ids=_extract_image_ids(body=body, main_unit=main_unit),
        description="\n".join(extract_markdowns(node=find_by_id(node=body, node_id="description"))) or None,
        highlights=[
            strip_markdown_formatting(text=strip_color_markup(text=text))
            for text in extract_markdowns(node=find_by_id(node=body, node_id="product-page-highlights"))
        ],
        allergens=_extract_allergens(body=body),
        info_sections=_extract_info_sections(body=body),
        promotion=_extract_promotion(raw=raw),
        bundles=_extract_bundles(body=body),
        price_ranges=price_ranges if price_ranges is not None else _extract_price_ranges_from_expressions(raw=raw),
        similar_products=_extract_similar_products(body=body),
    )


def _first(values: list[Any], default: Any) -> Any:
    return values[0] if values and values[0] is not None else default


def _numbers(values: list[Any]) -> list[int | float]:
    return [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]


def _node_markdown(node: dict[str, Any] | None) -> str | None:
    markdown = node.get("markdown") if node else None
    return strip_color_markup(text=markdown) if isinstance(markdown, str) else None


def _extract_header(main_container: dict[str, Any] | None) -> ProductHeader:
    component = ((main_container or {}).get("pml") or {}).get("component") or {}
    children = [child for child in component.get("children") or [] if isinstance(child, dict)]
    name_node = next((node for node in iter_objects(node=component) if node.get("textType") == "HEADER1"), None)
    brand_node = next(
        (child for child in children if (child.get("textAttributes") or {}).get("weight") == "REGULAR"), None
    )
    stack_node = next((child for child in children if child.get("type") == "STACK"), None)
    stack_texts = [
        child
        for child in (stack_node or {}).get("children") or []
        if isinstance(child, dict) and child.get("type") == "RICH_TEXT"
    ]
    unit_quantity_node = stack_texts[0] if stack_texts else None
    unit_price_node = stack_texts[1] if len(stack_texts) > 1 else None
    return ProductHeader(
        name=_node_markdown(node=name_node),
        brand=_node_markdown(node=brand_node),
        unit_quantity=_node_markdown(node=unit_quantity_node),
        unit_price=_node_markdown(node=unit_price_node),
    )


def _extract_display_price(
    product_id: str, body: dict[str, Any], main_container: dict[str, Any] | None, main_unit: dict[str, Any]
) -> int:
    display_price = main_unit.get("display_price") or 0
    if not display_price:
        bundle_node = find_by_id(node=body, node_id=product_id)
        if bundle_node:
            display_price = _first(values=find_all(node=bundle_node, key="price"), default=0)
    if not display_price and main_container:
        display_price = _first(values=_numbers(values=find_all(node=main_container, key="price")), default=0)
    return display_price


def _extract_image_ids(body: dict[str, Any], main_unit: dict[str, Any]) -> list[str]:
    gallery = find_by_id(node=body, node_id="product-page-image-gallery-main-image-container")
    if gallery:
        sources = find_all(node=gallery, key="source")
        return list(dict.fromkeys(source["id"] for source in sources if isinstance(source, dict) and "id" in source))
    return [main_unit["image_id"]] if main_unit.get("image_id") else []


def _extract_allergens(body: dict[str, Any]) -> list[str]:
    texts = extract_markdowns(node=find_by_id(node=body, node_id="product-page-allergies"))
    allergens = [strip_color_markup(text=text) for text in texts]
    return [allergen for allergen in allergens if not ALLERGEN_HEADING.match(allergen.strip())]


def _extract_info_sections(body: dict[str, Any]) -> list[ProductInfoSection]:
    accordion = find_by_id(node=body, node_id="accordion-list")
    items = _first(values=find_all(node=accordion, key="items"), default=None) if accordion else None
    if not isinstance(items, list):
        return []

    sections = []
    for item in items:
        item = item if isinstance(item, dict) else {}
        titles = [
            strip_color_markup(text=strip_markdown_formatting(text=text))
            for text in extract_markdowns(node=item.get("header"))
        ]
        contents = [strip_color_markup(text=text) for text in extract_markdowns(node=item.get("body"))]
        sections.append(ProductInfoSection(title=titles[0] if titles else "", content="\n".join(contents)))
    return sections


def _extract_promotion(raw: dict[str, Any]) -> ProductPromotion | None:
    promotion_ids = find_all(node=raw, key="promotion_id")
    promotion_labels = find_all(node=raw, key="promotion_label")
    if not promotion_ids or not promotion_labels:
        return None
    return ProductPromotion(id=promotion_ids[0], label=promotion_labels[0])


def _extract_bundles(body: dict[str, Any]) -> list[BundleItem]:
    container = next(
        (
            node
            for node in iter_objects(node=body)
            if isinstance(node.get("id"), str) and node["id"].startswith("product-page-bundles-")
        ),
        None,
    )
    if container is None:
        return []

    item_nodes = [
        node
        for node in iter_objects(node=container)
        if node.get("type") == "STATE_BOUNDARY" and isinstance(node.get("id"), str) and node["id"].startswith("s")
    ]
    bundles = []
    for index, node in enumerate(item_nodes):
        selling_units = find_all(node=node, key="sellingUnit")
        if not selling_units or not selling_units[0]:
            continue
        unit = selling_units[0]
        bundles.append(
            BundleItem(
                id=unit["id"],
                quantity=index + 1,
                price_per_unit=_first(values=_numbers(values=find_all(node=node, key="price")), default=0),
                image_id=unit.get("image_id") or "",
                max_count=unit.get("max_count") or 0,
            )
        )
    return bundles


def _extract_similar_products(body: dict[str, Any]) -> list[SimilarProduct]:
    container = find_by_id(node=body, node_id="alternatives-container")
    selling_units = find_all(node=container, key="sellingUnit") if container else []
    return [
        SimilarProduct.model_validate(obj={field: unit.get(field) for field in SimilarProduct.model_fields})
        for unit in selling_units
        if isinstance(unit, dict) and "display_price" in unit
    ]


def _extract_price_ranges_from_expressions(raw: dict[str, Any]) -> list[PriceRange] | None:
    """Finds price ranges in PML script parameters (`__ep1.v1`, then `__ep2.v1`), where the PDP embeds them."""
    for param in PRICE_RANGE_EXPRESSION_PARAMS:
        for expression in find_all(node=raw, key=param):
            ranges = expression.get("v1") if isinstance(expression, dict) else None
            if (
                isinstance(ranges, list)
                and ranges
                and isinstance(ranges[0], dict)
                and "price" in ranges[0]
                and "from_quantity" in ranges[0]
            ):
                return [PriceRange.model_validate(obj=price_range) for price_range in ranges]
    return None
