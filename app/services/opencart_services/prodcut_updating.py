from colorama import Fore, init
from typing import Any, Dict
from app.config.settings import opencart_settings, env_settings
from app.utils.logger import get_logger
from app.utils.db_utils import sql_query
from app.utils.db_utils import get_product_id, get_product_image
from app.services.opencart_services.category_updating import CategoryUpdating
from app.services.ERPNext_services.item_service import Item
from app.utils.telegram_notifier import send_telegram_message
from app.utils.image_sync import sync_image, get_oc_image_path



init(autoreset=True)

db_prefix = env_settings.DB_PREFIX

logger = get_logger(__name__)

ProductPayload = Dict[str, Any]

class ProductUpdating:
    def __init__(self, item_obj:Item, payload:ProductPayload):
        self.payload = payload
        self.item_obj = item_obj
        
    async def update_product(self):
        try:
            product_sku = self.payload["sku"]
            product_model = self.payload.get('model')
            product_id = await get_product_id(product_sku)
            
            if product_id:
                await self._update_product_table(product_id)
                await self._update_product_description_table(product_id)
                await self._update_product_image(product_id, product_model)

                
                category_obj = CategoryUpdating(self.item_obj, product_id, product_model )
                result = await category_obj.update_link_category_to_product()
                if result == 'success':
                    logger.info(f"prodcut {product_model} updated successfully.")
                else:
                    logger.info(Fore.YELLOW + f"prodcut {product_model} updated successfully, but category is not updated")

            else:
                logger.info(f"product with sku :{product_sku} is not exist , can't update it")    
        except Exception as e:
            logger.error(f"error in update_product for product {product_sku} : {e}", exc_info=True)
            await send_telegram_message(f"error while updating product {product_model},\ncheck the log file for more details")
            raise Exception(f"Failed, product {product_sku} failed to update")
    

    async def update_product_price(self, product_sku:str, new_price:float, price_list:str):
        try:    
            if await self._is_product_exist(product_sku):
                logger.info(f"product price list for {product_sku} is {price_list}")
                if price_list.lower() == "standard selling":
                    query = f""" UPDATE {db_prefix}product SET price = '{new_price}' WHERE sku = '{product_sku}'; """
                    await sql_query(query)
                    logger.info(f"product price for {product_sku} updated sucessfully to {new_price}")
        except Exception as e:
            logger.error(f"error in update_product_price for product {product_sku} : {e}", exc_info=True)            
            raise Exception(f"Failed, product {product_sku} failed to update price")
             

    async def update_product_quantity(self, product_sku):
        try:
            if await self._is_product_exist(product_sku):
                new_quantity = await self.item_obj.get_available_qty(product_sku)            
                query = f""" UPDATE {db_prefix}product SET quantity = '{new_quantity}' WHERE sku = '{product_sku}'; """
                await sql_query(query)
                logger.info(f"product quantity for {product_sku} updated sucessfully to {new_quantity}")
        except Exception as e:
            logger.error(f"error in update_product_quantity for product {product_sku} : {e}", exc_info=True)                        
            raise Exception(f"Failed, product {product_sku} failed to update quantity")


    async def _is_product_exist(self, product_sku):
        product_id = await get_product_id(product_sku)
        return True if product_id else False
        
    async def _update_product_table(self, product_id):
        description_query = f"""
            UPDATE {db_prefix}product SET
                model = '{self.payload["model"]}',
                stock_status_id = '{opencart_settings.get("stock_status_id", "7")}',
                shipping = '{self.payload["shipping"]}',
                points = '0',
                tax_class_id = '{opencart_settings.get("tax_class_id", "0")}',
                date_available = NOW(),
                weight = '{self.payload["weight"]}',
                weight_class_id = '1',
                length_class_id = '1',
                subtract = '{self.payload["subtract"]}',
                minimum = '1',
                status = '{self.payload["status"]}',
                date_modified = NOW()
            WHERE product_id  = {product_id}; 
            """
        await sql_query(description_query)
    
    async def _update_product_description_table(self, product_id):
        description_query = f"""
            UPDATE {db_prefix}product_description SET
                name = '{self.payload["name"]}',
                description = '{self.payload.get("description", "")}',
                meta_title = '{self.payload["meta_title"]}',
                meta_description = '{self.payload.get("meta_description", "")}'
            WHERE product_id = '{product_id}';
        """
        await sql_query(description_query)

    async def _update_product_image(self, product_id: int, product_model: str):
        erp_image_path = self.payload.get("image")
        
        # If image is provided in payload (not empty)
        if erp_image_path:
            # Predict the target OpenCart path
            target_oc_path = get_oc_image_path(erp_image_path)
            # Get the current path from DB
            current_oc_path = await get_product_image(product_id)
            
            # If they match, skip sync to avoid redundancy
            if target_oc_path == current_oc_path:
                logger.info(f"Image for product {product_model} is already up to date ({target_oc_path}). Skipping sync.")
                return

            # Synchronize image file from ERP to OpenCart server
            oc_image_path = await sync_image(erp_image_path)
            
            if oc_image_path:

                query = f"""
                    UPDATE {db_prefix}product
                    SET image = '{oc_image_path}'
                    WHERE product_id = {product_id}
                """
                await sql_query(query)
            else:
                logger.error(Fore.RED + f"Skipping database update for image because sync failed for {erp_image_path}")
                await send_telegram_message(f"Image sync failed for product {product_model}\nimage: {erp_image_path}")
        else:
            # If image is empty in payload, it means it was deleted in ERPNext
            # So we clear it in OpenCart as well
            logger.info(f"Image is empty for product {product_model}, clearing it in OpenCart.")
            query = f"""
                UPDATE {db_prefix}product
                SET image = ''
                WHERE product_id = {product_id}
            """
            await sql_query(query)

        