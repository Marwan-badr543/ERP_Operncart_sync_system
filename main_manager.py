from app.services.ERPNext_services.item_service import Item
from app.services.opencart_services.product_addition import ProductAddition
from app.services.opencart_services.product_deleting import ProductDeleting
from app.services.opencart_services.prodcut_updating import ProductUpdating
from app.mapper.erpnext_to_opencart import ERPToOpencart

class MainManager:
    def __init__(self, payload):
        self.payload = payload
        self.item = Item()
        
    async def add_product_main(self) -> dict:
        item_qty = await self.item.get_available_qty(self.payload["data"]['item_code'])
        item_price = await self.item.get_item_price(self.payload["data"]['item_code'])
        mapper = ERPToOpencart(self.payload, item_qty, item_price)
        payload = mapper.map_erpnext_item_to_opencart_product()
        product = ProductAddition(self.item, payload)
        result = await product.add_product()
        return result

    async def update_product_main(self) -> None:
        item_qty = await self.item.get_available_qty(self.payload["data"]['item_code'])
        item_price = await self.item.get_item_price(self.payload["data"]['item_code'])
        mapper = ERPToOpencart(self.payload, item_qty, item_price)
        payload = mapper.map_erpnext_item_to_opencart_product()
        pro = ProductUpdating(self.item, payload)
        await pro.update_product()
        
    async def delete_product_main(self) -> None:
        product_sku = self.payload["data"]["item_code"]
        pro = ProductDeleting(product_sku)    
        await pro.delete_product()
        


