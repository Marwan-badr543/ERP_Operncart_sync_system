import httpx
from dotenv import load_dotenv
import json
from colorama import Fore, init
from app.utils.logger import get_logger
from app.config.settings import env_settings, erp_settig

init(autoreset=True)

logger = get_logger(__name__)
load_dotenv()

_shared_client = None

def get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(max_keepalive_connections=50, max_connections=100)
        )
    return _shared_client

async def close_shared_client():
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
        _shared_client = None

class Item:
    def __init__(self):
        self.erp_url = env_settings.ERP_BASE_URL
        self.erp_headers = {
            "Authorization": f"token {env_settings.ERP_API_KEY}:{env_settings.ERP_API_SECRET}",
            "Content-Type": "application/json"
        }
        self.store = erp_settig.get("store")
        

    async def get_category_item_codes(self, item_group: str = None) -> list:        
        try:
            params = {
                "fields": '["item_code"]',
                "limit_page_length": 1000000
            }
            
            if item_group:
                params["filters"] = f'[["item_group", "=", "{item_group}"]]'
            
            client = get_shared_client()
            response = await client.get(f"{self.erp_url}/Item", headers=self.erp_headers, params=params)
            response.raise_for_status()
            all_json_items = response.json()
            item_codes_list = [item['item_code'] for item in all_json_items['data']]
            logger.info(f"Number of items fetched is: {len(item_codes_list)}"
                        + (f" for item group: '{item_group}'" if item_group else ""))

            if not item_codes_list:
                logger.warning(f"No item codes found" + (f" for item group: '{item_group}'" if item_group else ""))
                return []
            return item_codes_list
            
        except httpx.HTTPStatusError as e:
            logger.error(f"""error in get_all_item_codes, Status code: {e.response.status_code}
                            \nResponse: {e.response.text[:500]}""", exc_info=True)                        
            raise Exception(f"""error in get_all_item_codes, Status code: {e.response.status_code}
                            \nResponse: {e.response.text[:500]}""") from e        
            

    async def get_item_data(self, item_code) -> dict:
        try:
            client = get_shared_client()
            response = await client.get(f"{self.erp_url}/Item/{item_code}", headers=self.erp_headers)
            response.raise_for_status()
            item_data = response.json()
            logger.info(f"Successfully fetched data for item: {item_code}")
            if not item_data:
                logger.warning(Fore.YELLOW + f"No item data found for {item_code}")
                return None
            return item_data

        except httpx.HTTPStatusError as e:
            logger.error(f"""error in get_item_data for {item_code}: {e.response.status_code}
                            \nResponse: {e.response.text[:500]}""", exc_info=True)                        
            raise Exception(f"""error in get_item_data for {item_code}: {e.response.status_code}
                            \nResponse: {e.response.text[:500]}""") from e


    async def get_item_price(self, item_code) -> float | None:
        try:
            filters = [
                ["item_code", "=", item_code],
                ["price_list", "=", "Standard Selling"]
            ]
            params = {
                "filters": json.dumps(filters),
                "fields": json.dumps(["item_code", "price_list_rate", "price_list"])
            }

            client = get_shared_client()
            response = await client.get(f"{self.erp_url}/Item Price", headers=self.erp_headers, params=params)
            response.raise_for_status()
            json_response = response.json()
            data = json_response.get("data", [])
            price_value = self._extract_valid_price_from_list(data, item_code)
            if price_value:
                return price_value
            logger.info(f"  No price found for product {item_code} in ERPNext (Standard Selling price list)")
            logger.debug(f"   Response: {json_response}")
            return 0
        except httpx.HTTPStatusError as e:
            logger.error(f"""error in get_item_price for {item_code}: {e.response.status_code}
                            \nResponse: {e.response.text[:500]}""", exc_info=True)            
            raise Exception(f"""error in get_item_price for {item_code}: {e.response.status_code}
                            \nResponse: {e.response.text[:500]}""") from e


    def _extract_valid_price_from_list(self, data: list, item_code: str) -> float | None:
        """
        Helper to pick a valid price from the ERPNext Item Price list response.
        """
        if not data:
            return 0
            
        for price_record in data:
            if not isinstance(price_record, dict):
                continue
            price = price_record.get("price_list_rate")
            if price is not None and price != 0:
                try:
                    price_value = float(price)
                except (TypeError, ValueError):
                    continue
                return price_value
            
        logger.warning(f"⚠️  Price records found for {item_code} but all are None or 0\nPrice data: {data}")
        return 0
        
    
    async def get_available_qty(self, item_code) -> int:
        try:
            # Support both a single store (str) and multiple stores (list)
            stores = self.store if isinstance(self.store, list) else [self.store]

            filters = [
                ["Bin", "item_code", "=", item_code],
                ["Bin", "warehouse", "in", stores]   # "in" operator works for 1 or many
            ]
            filters_param = json.dumps(filters)
            params = {
                "filters": filters_param,
                "fields": '["actual_qty", "reserved_qty"]',
                "limit_page_length": 100000
            }

            client = get_shared_client()
            response = await client.get(
                f"{self.erp_url}/Bin",
                headers=self.erp_headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()

            if not data or not data.get("data"):
                logger.info(f"There is no stock for this item: {item_code}")
                return 0

            # Sum across all returned warehouse bins
            total_actual   = sum(bin.get("actual_qty",   0) for bin in data["data"])
            total_reserved = sum(bin.get("reserved_qty", 0) for bin in data["data"])
            available_qty  = total_actual - total_reserved

            return int(available_qty)

        except httpx.HTTPStatusError as e:
            logger.error(
                f"error in get_available_qty for {item_code}: {e.response.status_code}"
                f"\nResponse: {e.response.text[:500]}",
                exc_info=True
            )
            raise Exception(
                f"error in get_available_qty for {item_code}: {e.response.status_code}"
                f"\nResponse: {e.response.text[:500]}"
            )     
                

    async def get_item_category(self, item_code):
        last_error = None
        tries = 5
        for i in range(tries):
            try:
                client = get_shared_client()
                response = await client.get(f"{self.erp_url}/Item/{item_code}", headers=self.erp_headers)
                response.raise_for_status()
                data = response.json()
                if "data" not in data:
                    raise Exception(f"failed to get item category from ERPNext for {item_code}")
                return data["data"]['item_group']
            except Exception as e:
                last_error = e
                logger.warning(Fore.YELLOW + f"Attempt {i+1}/{tries} failed for {item_code}")
                continue

        logger.error(f"Failed to get item category from ERPNext for {item_code} after {tries} tries", exc_info=True)
        raise RuntimeError(f"failed to get item category from ERPNext for {item_code}\nerror:{last_error}")
