import logging
from fastapi import Depends, FastAPI, HTTPException, Request
from main_manager import MainManager
from app.services.opencart_services.prodcut_updating import ProductUpdating
from app.services.ERPNext_services.item_service import Item
from app.controller.schema import UpdatePrice, UpdateQuantity, MianPayload
from app.utils.telegram_notifier import send_telegram_message
from app.config.settings import env_settings
from app.utils.logger import get_logger

secret_key = env_settings.API_SECRET_KEY
logger = get_logger(__name__)



async def verify_secret(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header :
        logger.error("Missing or invalid Authorization header")
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header
    if token != secret_key:
        logger.error("Invalid secret key")
        raise HTTPException(status_code=403, detail="Invalid secret key")
    
item_obj = Item()
app = FastAPI()

@app.post('/sync/add-product')
async def add_product(payload:MianPayload, deb = Depends(verify_secret)):    
    main_manager = MainManager(payload)
    result = await main_manager.add_product_main()
    if result['pro_status'] == 'failed':
        await send_telegram_message(f"failed to add product {payload['data']['item_code']}\ncheck the log file for more details")
        raise HTTPException(status_code=400, detail=result['error'])
    if result.get("categ_status") == 'failed':
        await send_telegram_message(f"failed to add category for item: {payload['data']['item_code']}\ncheck the log file for more details")
    return {"message":'product added successfully'}


@app.put('/sync/update-product')    
async def update_product(payload:MianPayload, deb = Depends(verify_secret)):
    main_manager = MainManager(payload)
    await main_manager.update_product_main()
    return {"message":'product updated successfully'}


@app.delete('/sync/delete-product')
async def delete_product(payload:MianPayload, deb = Depends(verify_secret)):
    main_manager = MainManager(payload)
    await main_manager.delete_product_main()
    return {"message":'product deleted successfully'}


@app.put('/sync/update-product-price')   
async def update_product_price(payload:UpdatePrice, deb = Depends(verify_secret)):
    product_sku = payload.item_code
    new_price = payload.price_list_rate
    price_list = payload.price_list
    product_obj = ProductUpdating(item_obj, payload)
    await product_obj.update_product_price(product_sku, new_price, price_list)
    return {"message":"product price updated successfully"}


@app.put('/sync/update-product-quantity-sle')
async def update_product_quantity_sle(payload:UpdateQuantity, deb = Depends(verify_secret)):
    item_code = payload.item_code
    product_obj = ProductUpdating(item_obj, payload)
    await product_obj.update_product_quantity(item_code)
    return {"message":"product quantity updated successfully"}


@app.put('/sync/update-product-quantity-so')
async def update_product_quantity_so(payload:MianPayload, deb = Depends(verify_secret)):
    product_obj = ProductUpdating(item_obj, payload)
    for item in payload.get("items"):
        item_code = item.get("item_code")
        await product_obj.update_product_quantity(item_code)
    return {"message":"product quantity updated successfully"}

    
@app.get('/')    
async def test():
    return {"message": "test"}  

