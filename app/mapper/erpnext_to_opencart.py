from datetime import datetime
from typing import Any, Dict
import re
from app.config.settings import opencart_settings

ErpnextItem = Dict[str, Any]
OpenCartProductPayload = Dict[str, Any]


class ERPToOpencart:
    def __init__(self, item_data: ErpnextItem, item_qty: int, item_price: float):
        self.item_data = item_data
        self.item_qty = item_qty
        self.item_price = item_price
        
    def map_erpnext_item_to_opencart_product(self) -> OpenCartProductPayload:
        """
        Public method that combines extraction + payload building.
        """
        core_fields = self._extract_core_fields()
        return self._build_payload_from_fields(core_fields)



    def _extract_core_fields(self) -> Dict[str, Any]:
        """
        Extract and normalize fields from raw ERPNext item data.
        """
        data = self.item_data.get("data", self.item_data)

        item_name = data.get("item_name")
        item_code = data.get("item_code")
        last_purchase_rate = data.get("last_purchase_rate", self.item_price)
        description = data.get("description", "")
        valuation_rate = data.get("valuation_rate", 0)
        status = "1" if data.get("disabled") in (False, 0, None) else "0"
        is_stock_item = "0" if data.get("is_stock_item") == 0 else "1"
        weight_per_unit = str(data.get("weight_per_unit", ""))
        image = data.get("image", "")

        return {
            "item_name": item_name,
            "item_code": item_code,
            "price": self.item_price,
            "last_purchase_rate": last_purchase_rate,
            "actual_qty": self.item_qty,
            "description": description,
            "valuation_rate": valuation_rate,
            "status": status,
            "is_stock_item": is_stock_item,
            "weight_per_unit": weight_per_unit,
            "image": image,
        }

    def _build_payload_from_fields(self, fields: Dict[str, Any]) -> OpenCartProductPayload:
        # ── core identity ─────────────────────────────────────────────────────
        item_code = fields.get("item_code")
        item_name = fields.get("item_name", item_code)
        description = fields.get("description", "")

        # ── pricing ───────────────────────────────────────────────────────────
        price = fields.get("price",0)

        # ── stock ─────────────────────────────────────────────────────────────
        quantity      = fields.get("actual_qty",0)
        status        = fields.get("status","1")
        is_stock_item = fields.get("is_stock_item",1)   # used for both subtract & shipping

        # ── physical ──────────────────────────────────────────────────────────
        weight = fields.get("weight_per_unit",0)

        # ── opencart settings ─────────────────────────────────────────────────
        tax_class_id   = opencart_settings.get("tax_class_id", "0")
        stock_status_id = opencart_settings.get("stock_status_id", "7")

        # ── seo ───────────────────────────────────────────────────────────────
        seo_keyword = self.clean_product_name(str(item_code))

        payload: OpenCartProductPayload = {
            # ── description ───────────────────────────────────────────────────
            "name":             item_name,
            "description":      description,
            "meta_title":       item_name,
            "meta_description": description,
            "meta_keyword":     "",
            "tag":              "",

            # ── product identity ──────────────────────────────────────────────
            "model":            item_code,
            "sku":              item_code,
            "upc":              "",
            "ean":              "",
            "jan":              "",
            "isbn":             "",
            "mpn":              "",
            "location":         "",

            # ── pricing ───────────────────────────────────────────────────────
            "price":            price,
            "tax_class_id":     tax_class_id,
            "points":           "0",

            # ── stock ─────────────────────────────────────────────────────────
            "quantity":         quantity,
            "status":           status,
            "subtract":         is_stock_item,
            "stock_status_id":  stock_status_id,
            "minimum":          "1",

            # ── shipping ──────────────────────────────────────────────────────
            "shipping":         is_stock_item,

            # ── physical dimensions ───────────────────────────────────────────
            "weight":           weight,
            "weight_class_id":  "1",   # 1=Kilogram 2=Gram 5=Pound 6=Ounce
            "length":           "",
            "width":            "",
            "height":           "",
            "length_class_id":  "1",   # 1=Centimeter 2=Millimeter 3=Inch

            # ── visibility & display ──────────────────────────────────────────
            "sort_order":       "0",
            "date_available":   datetime.now().strftime("%Y-%m-%d"),

            # ── store & category ──────────────────────────────────────────────
            "store_id":         "0",   # 0 = Default store

            # ── seo ───────────────────────────────────────────────────────────
            "seo_keyword":      seo_keyword,

            # ── image ─────────────────────────────────────────────────────────
            "image":            fields.get("image", ""),
        }

        return payload
    
    def clean_product_name(self, product_name:str):
        product_name = product_name.lower()
        product_name = re.sub(r'[^a-z0-9\s-]', '', product_name)  # remove ALL symbols
        product_name = re.sub(r'\s+', '-', product_name)          # spaces → hyphens
        return product_name.strip()
