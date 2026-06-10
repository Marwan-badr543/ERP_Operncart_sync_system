import json
from typing import Any, Dict
from colorama import Fore, init
from app.config.settings import opencart_settings, env_settings
from app.utils.logger import get_logger
from app.utils.db_utils import sql_query
from app.utils.db_utils import get_product_id
from app.services.opencart_services.category_addition import CategoryAddition
from app.services.ERPNext_services.item_service import Item
from app.config.category_configs import categoris_names_convertion
from app.services.opencart_services.product_deleting import ProductDeleting
from app.utils.image_sync import sync_image
from app.utils.telegram_notifier import send_telegram_message

init(autoreset=True)

db_prefix = env_settings.DB_PREFIX
logger = get_logger(__name__)

ProductPayload = Dict[str, Any]

class ProductAddition:
    
    langs_list = opencart_settings.get('languages')

    def __init__(self, item_obj:Item, payload: ProductPayload):
        self.payload = payload
        self.item_obj = item_obj
        
    async def add_product(self):
        try:
            product_model = self.payload.get("model")
            category_name = await self.item_obj.get_item_category(product_model)
            if category_name in categoris_names_convertion:
                
                product_sku = self.payload["sku"]
                product_id = await get_product_id(product_sku)
                if not product_id:
                    # ✅ FIX: capture the returned product_id from the insert
                    product_id = await self._insert_into_product_table()
                    
                    if not product_id:
                        raise Exception("Failed to get product_id after insert")

                    # ✅ Update image if provided
                    if self.payload.get("image"):
                        await self._update_product_image(product_id, product_model)

                    # ✅ Insert description for each language
                    for lang in ProductAddition.langs_list:
                        await self._insert_into_product_description_table(product_id, lang)

                    # ✅ Assign product to store (required — product won't show otherwise)
                    store_id = opencart_settings.get("store_id", 0)
                    await self._insert_into_product_to_store(product_id, store_id)

                    # # ✅ Assign product to category
                    # if category:
                    #     category_id = await get_category_id(category)
                    #     if category_id:
                    #         await self._insert_into_product_to_category(product_id, category_id)

                    # # ✅ SEO URL (optional, but good for clean URLs)
                    # if self.payload.get("seo_keyword"):
                    #     await self._insert_seo_url(product_id, store_id)

                    # # ✅ Additional images (optional)
                    # if self.payload.get("product_images"):
                    #     await self._insert_product_images(product_id)

                    # # ✅ Discounts (optional)
                    # if self.payload.get("product_discounts"):
                    #     await self._insert_product_discounts(product_id)

                    # # ✅ Special prices (optional)
                    # if self.payload.get("product_specials"):
                    #     await self._insert_product_specials(product_id)

                    category_obj = CategoryAddition(self.item_obj, product_id, product_model)
                    categ_result = await category_obj.link_category_to_product()
                    
                    return_dict = {
                        'pro_status': 'added',
                        'categ_status': categ_result['categ_status'],
                        'message': f'product {self.payload.get("name")} added successfully',
                        'product_id': product_id
                    }
                    
                    logger.info(Fore.GREEN + json.dumps(return_dict, indent=2))
                    return return_dict
                else:
                    return_dict = {
                        'pro_status': 'skipped',
                        'message': f'product {self.payload.get("name")} already exists',
                        'product_id': product_id
                    }
                logger.info(Fore.YELLOW + json.dumps(return_dict, indent=2))
                return return_dict

        except Exception as e:
            logger.error(Fore.RED + f"Error in add_product for {self.payload.get('name')}", exc_info=True)
            product_deleting_obj = ProductDeleting(self.payload.get("sku"))
            await product_deleting_obj.delete_product()
            return {
                'pro_status': 'failed',
                'message': f'product {self.payload.get("name")} failed to add',
                'product_id': None
            }
    # ------------------------------------------------------------------ #
    #  Main product table                                                #
    # ------------------------------------------------------------------ #

    async def _insert_into_product_table(self) -> int:
        """
        Insert main product record and return the new product_id.
        """
        product_query = f"""
            INSERT INTO {db_prefix}product (
                model, sku, price, quantity, stock_status_id, shipping,
                points, tax_class_id, date_available, weight, weight_class_id,
                length_class_id, subtract, minimum, status, date_added, date_modified
            ) VALUES (
                '{self.payload["model"]}',
                '{self.payload["sku"]}',
                '{float(self.payload["price"])}',
                '{int(self.payload["quantity"])}',
                '{int(opencart_settings.get("stock_status_id", 7))}',
                '{int(self.payload.get("is_stock_item", 1))}',
                '0',
                '{int(opencart_settings.get("tax_class_id", 0))}',
                NOW(),
                '{float(self.payload.get("weight", 0))}',
                '1',
                '1',
                '{int(self.payload.get("subtract", 1))}',
                '1',
                '{int(self.payload.get("status", 1))}',
                NOW(),
                NOW()
            );
        """
        result = await sql_query(product_query)
        product_id = result["sql_data"]["insert_id"]
        return product_id


    async def _update_product_image(self, product_id: int, product_model: str):
        erp_image_path = self.payload.get("image")
        
        # If image is provided in payload (not empty)
        if erp_image_path:
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
            # If image is empty in payload, it means it's missing or deleted
            # We ensure it's empty in OpenCart as well
            logger.info(f"Image is empty for product {product_model}, setting to empty in OpenCart.")
            query = f"""
                UPDATE {db_prefix}product
                SET image = ''
                WHERE product_id = {product_id}
            """
            await sql_query(query)

    # ------------------------------------------------------------------ #
    #  Description                                                         #
    # ------------------------------------------------------------------ #

    async def _insert_into_product_description_table(self, product_id: int, lang: int):
        product_name = self.payload.get('name', "")

        description_query = f"""
            INSERT INTO {db_prefix}product_description (
                product_id, language_id, name, description,
                tag, meta_title, meta_description, meta_keyword
            ) VALUES (
                {product_id},
                {lang},
                '{product_name}',
                '{self.payload.get("description", "")}',
                '{self.payload.get("tag", "")}',
                '{self.payload.get("meta_title", product_name)}',
                '{self.payload.get("meta_description", "")}',
                '{self.payload.get("meta_keyword", "")}'
            );
        """
        await sql_query(description_query)

    # ------------------------------------------------------------------ #
    #  Store assignment (REQUIRED — product is invisible without this)    #
    # ------------------------------------------------------------------ #

    async def _insert_into_product_to_store(self, product_id: int, store_id: int):
        query = f"""
            INSERT INTO {db_prefix}product_to_store (product_id, store_id)
            VALUES ({product_id}, {store_id})
        """
        await sql_query(query)

    # ------------------------------------------------------------------ #
    #  Category assignment                                                 #
    # ------------------------------------------------------------------ #

    async def _insert_into_product_to_category(self, product_id: int, category_id: int):
        query = f"""
            INSERT INTO {db_prefix}product_to_category (product_id, category_id)
            VALUES ({product_id}, {category_id})
        """
        await sql_query(query)

    # ------------------------------------------------------------------ #
    #  SEO URL                                                             #
    # ------------------------------------------------------------------ #

    async def _insert_seo_url(self, product_id: int, store_id: int):
        for lang in ProductAddition.langs_list:
            keyword = self.payload.get("seo_keyword", "")
            if keyword:
                query = f"""
                    INSERT INTO {db_prefix}seo_url (store_id, language_id, query, keyword)
                    VALUES (
                        {store_id},
                        {lang},
                        'product_id={product_id}',
                        '{keyword}-{product_id}'
                    )
                """
                await sql_query(query)

    # ------------------------------------------------------------------ #
    #  Additional images                                                   #
    # ------------------------------------------------------------------ #

    async def _insert_product_images(self, product_id: int):
        for idx, image in enumerate(self.payload.get("product_images", [])):
            query = f"""
                INSERT INTO {db_prefix}product_image (product_id, image, sort_order)
                VALUES ({product_id}, '{image}', {idx})
            """
            await sql_query(query)

    # ------------------------------------------------------------------ #
    #  Discounts & Specials (optional)                                     #
    # ------------------------------------------------------------------ #

    async def _insert_product_discounts(self, product_id: int):
        for discount in self.payload.get("product_discounts", []):
            query = f"""
                INSERT INTO {db_prefix}product_discount (
                    product_id, customer_group_id, quantity,
                    priority, price, date_start, date_end
                ) VALUES (
                    {product_id},
                    '{int(discount.get("customer_group_id", 0))}',
                    '{int(discount.get("quantity", 0))}',
                    '{int(discount.get("priority", 1))}',
                    '{float(discount.get("price", 0))}',
                    '{discount.get("date_start", "0000-00-00")}',
                    '{discount.get("date_end", "0000-00-00")}'
                )
            """
            await sql_query(query)

    async def _insert_product_specials(self, product_id: int):
        for special in self.payload.get("product_specials", []):
            query = f"""
                INSERT INTO {db_prefix}product_special (
                    product_id, customer_group_id, priority,
                    price, date_start, date_end
                ) VALUES (
                    {product_id},
                    '{int(special.get("customer_group_id", 0))}',
                    '{int(special.get("priority", 1))}',
                    '{float(special.get("price", 0))}',
                    '{special.get("date_start", "0000-00-00")}',
                    '{special.get("date_end", "0000-00-00")}'
                )
            """
            await sql_query(query)


