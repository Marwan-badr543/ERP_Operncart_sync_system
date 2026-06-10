from colorama import Fore, init
from app.config.settings import env_settings
from app.utils.logger import get_logger
from app.utils.db_utils import sql_query
from app.services.ERPNext_services.item_service import Item
from app.config.category_configs import categoris_names_convertion

init(autoreset=True)

db_prefix = env_settings.DB_PREFIX

logger = get_logger(__name__)

class CategoryAddition:
    def __init__(self, item:Item, product_id:int, product_model:str):
        self.item = item
        self.product_id = product_id
        self.product_model = product_model

    async def link_category_to_product(self):
        try:
            category_name = await self._get_category_name()
            categ_id_result = await self._get_category_id(category_name)
            category_id = categ_id_result.get('catog_id')
            
            if not category_id:
                logger.warning(Fore.YELLOW + f"Category {categ_id_result.get('category')} not exist in opencart , Please add it first.")
                return {"categ_status":"failed",
                        "message":'category not exist in opencart'}
            
            if not await self._is_product_has_category(self.product_id):
                await self._insert_into_product_to_category(category_id)
                logger.info(Fore.GREEN + f"category {category_name} linked successfully to product {self.product_model}")
                return {"categ_status":"success",
                        "message":'category inserted successfully.'}
            
            else:
                logger.info(f"category {category_name} already linked to product {self.product_model}")
                return {"categ_status":"success",
                        "message":'category already linked to product.'}

        except Exception as e :
            logger.error(f"error while link_category_to_product for prodcut {self.product_model}, error: {e}", exc_info=True)
            return({
                "categ_status": 'failed',
                "message":f"error while link_category_to_product"
                })
        
        
    async def _get_category_name(self):
        erp_category_name = await self.item.get_item_category(self.product_model)
        return self.__get_opencart_category_name(erp_category_name)

    def __get_opencart_category_name(self, erp_category_name:str) -> str | None:
        for catog in categoris_names_convertion.keys():
            if erp_category_name.lower() in catog.lower():
                opencart_category_name = categoris_names_convertion.get(erp_category_name)
                return opencart_category_name
                
    async def _get_category_id(self, category_name):
        if not category_name:
            return {'catog_id':None,
                    'category': category_name}
        query = ""f"SELECT category_id FROM {db_prefix}category_description WHERE name = '{category_name}'"""    
        result = await sql_query(query)
        if result['sql_data']['count'] != 0 :
            category_id = int(result['sql_data']['data'][0]['category_id'])
            return {'catog_id':category_id ,
                    'category': category_name}
        else:
            return {'catog_id':None,
                    'category': category_name}
            
    async def _insert_into_product_to_category(self, category_id):
        insert_query = f"INSERT INTO {db_prefix}product_to_category (product_id, category_id) VALUES ({self.product_id}, {category_id})"
        await sql_query(insert_query)

    async def _is_product_has_category(self, product_id):
        try:
            query = f"SELECT category_id FROM {db_prefix}product_to_category WHERE product_id = '{product_id}'"
            result = await sql_query(query)
            return True if result['sql_data']['count'] != 0 else False
        except Exception as e:
            logger.error(f"Failed to check if product {product_id} has category", exc_info=True)
            raise RuntimeError(f"error in check_if_product_has_category\nerror:{e}")



if __name__ == "__main__":
    pass
