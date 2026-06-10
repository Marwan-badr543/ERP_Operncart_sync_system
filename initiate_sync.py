import asyncio
from colorama import Fore, Style, init
from app.services.ERPNext_services.item_service import Item
from app.config.category_configs import categoris_names_convertion
from main_manager import MainManager
from app.utils.logger import get_logger
from app.utils.telegram_notifier import send_telegram_message
import time

logger = get_logger(__name__)

init(autoreset=True)

class InitiateSync:
    synced_products = 0
    secceeded_products = 0
    skipped_products = 0
    failed_products = 0
    failed_products_names = []
    skipped_products_names = []
    failed_category = 0
    failed_category_names = []
    def __init__(self):
        self.item_obj = Item()
       
    async def sync_all_products(self):
        for category in categoris_names_convertion:
            tries = 5
            for i in range(tries):
                items_list = await self.item_obj.get_category_item_codes(category)
                if items_list:
                    logger.info(Fore.CYAN + f"category->[ {category} ], try [ {i + 1}/{tries} ] item list fetched with {len(items_list)} items")
                    InitiateSync.synced_products += len(items_list)
                    break
                logger.error(Fore.RED + f"category->[ {category} ], try [ {i + 1}/{tries} ] item list fetch failed")
            if items_list:
                semaphore = asyncio.Semaphore(2)
                
                async def sem_add(_item_code, _category):
                    async with semaphore:
                        await self._add_products_with_retry(_item_code, _category)

                tasks = [asyncio.create_task(sem_add(item_code, category)) for item_code in items_list]
                await asyncio.gather(*tasks)
            else:
                if i == tries - 1:
                    logger.error(f"failed to get item list for category->[ {category} ] after {tries} tries")
                else:    
                    logger.error(Fore.RED + f"category->[ {category} ] has no items")

        self._print_sync_summary()


    async def _add_products_with_retry(self, item_code):
        tries = 5
        result = {'pro_status': 'failed'}
        for i in range(tries):
            try:
                payload = await self.item_obj.get_item_data(item_code)
                main_manager_obj = MainManager(payload)
                result = await main_manager_obj.add_product_main()
                status_msg = result.get('pro_status')
                if status_msg == 'failed':
                    raise Exception(f"Failed to add product {item_code}")
                break
            except Exception as e:
                logger.error(Fore.RED +f"Try [ {i + 1}/{tries} ] failed, error while adding item {item_code}")
                if i == tries - 1:
                    logger.error(f"failed to add item {item_code} after {tries} tries\nerror: {e}", exc_info=True)
                    

        await self._check_result_and_log(result, item_code)

    async def _check_result_and_log(self, result, item_code):
        if result['pro_status'] == 'added':
            InitiateSync.secceeded_products += 1
            if result.get('categ_status') and result.get('categ_status') == 'failed':
                InitiateSync.failed_category += 1
                InitiateSync.failed_category_names.append(item_code)
                await send_telegram_message(f"failed to add category for item: {item_code}\ncheck the log file for more details")
                
        elif result['pro_status'] == 'failed':
            InitiateSync.failed_products += 1
            InitiateSync.failed_products_names.append(item_code)
            await send_telegram_message(f"failed to add item: {item_code}\ncheck the log file for more details")

        elif result['pro_status'] == 'skipped':
            InitiateSync.skipped_products += 1
            InitiateSync.skipped_products_names.append(item_code)


    def _print_sync_summary(self):
        logger.info(Fore.CYAN + "Sync summary:")
        logger.info(Fore.CYAN + f"Synced products: {InitiateSync.synced_products}")
        logger.info(Fore.GREEN + f"Secceeded products: {InitiateSync.secceeded_products}")
        logger.info(Fore.YELLOW + f"Skipped products: {InitiateSync.skipped_products}")
        logger.info(Fore.RED + f"Failed products: {InitiateSync.failed_products}")
        logger.info(Fore.RED + f"Failed products names: {InitiateSync.failed_products_names}")
        logger.info(Fore.YELLOW + f"Skipped products names: {InitiateSync.skipped_products_names}")
        logger.info(Fore.RED + f"Failed categories: {InitiateSync.failed_category}")
        logger.info(Fore.RED + f"Failed categories names: {InitiateSync.failed_category_names}")

async def main():
    try:
        first_time = time.time()
        sync = InitiateSync()
        await sync.sync_all_products()
        last_time = time.time()
        print(Fore.LIGHTMAGENTA_EX + f"total time {last_time - first_time:.2f} seconds.")
    finally:
        from app.services.ERPNext_services.item_service import close_shared_client
        await close_shared_client()

asyncio.run(main())


