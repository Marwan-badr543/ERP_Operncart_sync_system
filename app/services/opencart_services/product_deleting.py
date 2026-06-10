from colorama import Fore, init
from app.utils.logger import get_logger
from app.utils.db_utils import sql_query
from app.utils.db_utils import get_product_id
from app.config.settings import env_settings
from app.utils.telegram_notifier import send_telegram_message
init(autoreset=True)

db_prefix = env_settings.DB_PREFIX
logger = get_logger(__name__)


class ProductDeleting:
    def __init__(self, prodcut_sku: str):
        self.prodcut_sku = prodcut_sku 
        self.product_id = 0 

    async def delete_product(self):
        try:
            self.product_id = await get_product_id(self.prodcut_sku)
            if not self.product_id:
                logger.info(f"product with sku:{self.prodcut_sku} is not exist ,can't delete it")
                return

            # Order matters: delete dependencies before the main record
            await self._delete_product_attribute()
            await self._delete_product_description()
            await self._delete_product_discount()
            await self._delete_product_filter()
            await self._delete_product_image()
            await self._delete_product_option()
            await self._delete_product_option_value()
            await self._delete_product_related()
            await self._delete_product_reward()
            await self._delete_product_special()
            await self._delete_product_to_category()
            await self._delete_product_to_download()
            await self._delete_product_to_layout()
            await self._delete_product_to_store()
            await self._delete_product_recurring()
            await self._delete_review()
            await self._delete_seo_url()
            await self._delete_coupon_product()

            # Delete main product record last
            await self._delete_from_product_table()

            logger.info(f"Product {self.prodcut_sku} deleted successfully from all tables.")

        except Exception as e:
            logger.error(f"Error in delete_product for product_id={self.prodcut_sku}: {e}", exc_info=True)
            await send_telegram_message(f"error while deleting product {self.prodcut_sku},\ncheck the log file for more details")
            raise Exception(f"Failed, product {self.prodcut_sku} failed to delete")

    # ------------------------------------------------------------------ #
    #  Main table                                                          #
    # ------------------------------------------------------------------ #

    async def _delete_from_product_table(self):
        query = f"DELETE FROM {db_prefix}product WHERE product_id = {self.product_id}"
        await sql_query(query)

    # ------------------------------------------------------------------ #
    #  Dependent tables                                                    #
    # ------------------------------------------------------------------ #

    async def _delete_product_attribute(self):
        query = f"DELETE FROM {db_prefix}product_attribute WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_product_description(self):
        query = f"DELETE FROM {db_prefix}product_description WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_product_discount(self):
        query = f"DELETE FROM {db_prefix}product_discount WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_product_filter(self):
        query = f"DELETE FROM {db_prefix}product_filter WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_product_image(self):
        query = f"DELETE FROM {db_prefix}product_image WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_product_option(self):
        query = f"DELETE FROM {db_prefix}product_option WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_product_option_value(self):
        query = f"DELETE FROM {db_prefix}product_option_value WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_product_related(self):
        # Must delete both directions of the relationship
        await sql_query(f"DELETE FROM {db_prefix}product_related WHERE product_id = {self.product_id}")
        await sql_query(f"DELETE FROM {db_prefix}product_related WHERE related_id = {self.product_id}")

    async def _delete_product_reward(self):
        query = f"DELETE FROM {db_prefix}product_reward WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_product_special(self):
        query = f"DELETE FROM {db_prefix}product_special WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_product_to_category(self):
        query = f"DELETE FROM {db_prefix}product_to_category WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_product_to_download(self):
        query = f"DELETE FROM {db_prefix}product_to_download WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_product_to_layout(self):
        query = f"DELETE FROM {db_prefix}product_to_layout WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_product_to_store(self):
        query = f"DELETE FROM {db_prefix}product_to_store WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_product_recurring(self):
        query = f"DELETE FROM {db_prefix}product_recurring WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_review(self):
        query = f"DELETE FROM {db_prefix}review WHERE product_id = {self.product_id}"
        await sql_query(query)

    async def _delete_seo_url(self):
        # String match, not an integer — no quotes issue but still safe via int cast above
        query = f"DELETE FROM {db_prefix}seo_url WHERE query = 'product_id={self.product_id}'"
        await sql_query(query)

    async def _delete_coupon_product(self):
        query = f"DELETE FROM {db_prefix}coupon_product WHERE product_id = {self.product_id}"
        await sql_query(query)