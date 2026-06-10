import httpx
import inspect
from colorama import Fore, Style, init
from app.config.settings import env_settings
from app.utils.logger import get_logger


init(autoreset=True)
logger = get_logger(__name__)
db_prefix = env_settings.DB_PREFIX

async def sql_query(query):
    """send a requerst has an sql query to the php file and return the result"""
    async with httpx.AsyncClient(timeout=15) as client:
        response =await client.post(env_settings.BRIDGE_URL, data={
            "secret": env_settings.SECRET,
            "query":  query,
        }, timeout=30)
    
    result = {'status' : response.status_code ,
            'sql_data' : response.json()
            }    
    await check_if_request_successed(result)    
    return result

async def check_if_request_successed(response):
    status = response.get('status')
    caller = inspect.stack()[1].function
    if status != 200:
        logger.critical(Fore.RED + f"Request failed: {response}")
        raise RuntimeError(Fore.RED + f"Request failed with status code {status} in {caller} function")
    
    result = response.get('sql_data')
    if result.get('error'):
        logger.critical(Fore.RED + f"SQL error: {result['error']}")
        raise RuntimeError(Fore.RED + f"Request failed in {caller} function, with error {result['error']}")


async def get_product_id(product_sku) -> int | None:
   query = f"""
       SELECT product_id 
       FROM {db_prefix}product 
       WHERE sku = '{product_sku}'
       LIMIT 1;
   """
   result = await sql_query(query)
   if result and result['sql_data']['data']:
       product_id = result['sql_data']['data'][0]["product_id"]
       return product_id
       
   return None        

async def get_product_image(product_id: int) -> str | None:
    query = f"""
        SELECT image 
        FROM {db_prefix}product 
        WHERE product_id = {product_id}
        LIMIT 1;
    """
    result = await sql_query(query)
    if result and result['sql_data']['data']:
        return result['sql_data']['data'][0].get("image")
    return None

