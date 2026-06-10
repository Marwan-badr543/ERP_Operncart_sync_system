from colorama import Fore, init
from logging import exception
from app.config.settings import  env_settings
from app.utils.logger import get_logger
from app.utils.db_utils import sql_query
from app.services.ERPNext_services.item_service import Item
from app.services.opencart_services.category_addition import CategoryAddition
from app.utils.telegram_notifier import send_telegram_message

init(autoreset=True)

db_prefix = env_settings.DB_PREFIX

logger = get_logger(__name__)

class CategoryUpdating(CategoryAddition):
    def __init__(self, item:Item, product_id:int, product_model:str):
        super().__init__(item, product_id, product_model)

    async def update_link_category_to_product(self):
        try:
            category_name = await self._get_category_name()
            categ_id_result = await self._get_category_id(category_name)
            category_id = categ_id_result.get('catog_id')
            
            if not category_id:
                logger.warning(Fore.YELLOW + f"Category {categ_id_result.get('category')} not exist in opencart , Please add it first.")
                await send_telegram_message(f"Category {categ_id_result.get('category')} not exist in opencart,\nPlease add it first.")
                return 'failed'
                
            if await self._is_product_has_category(self.product_id):
                await self._update_product_to_category(category_id)
                logger.info(f"category {category_name} updated and linked successfully to product {self.product_model}")
                return 'success'
            await self._insert_into_product_to_category(category_id)    
            logger.info(f"product {self.product_model} wasn't linked to any categories, it is linked successfully now to {category_name}.")
            return 'success'

        except exception as e:
            logger.error(f"error while updating category {category_name} to product {self.product_model}, error: {e}", exc_info=True)
            await send_telegram_message(f"error while updating category {category_name} to product {self.product_model},\ncheck the log file for more details")
            return 'failed'

    async def _update_product_to_category(self, category_id):
        update_query = f"""UPDATE {db_prefix}product_to_category
                            SET category_id = {category_id}
                            WHERE product_id = {self.product_id}""" 
        await sql_query(update_query)

