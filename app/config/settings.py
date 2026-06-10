import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from dataclasses import dataclass
class EnvSettings(BaseSettings):
    API_SECRET_KEY: str
    ERP_BASE_URL: str
    ERP_API_KEY: str
    ERP_API_SECRET: str
    BRIDGE_URL: str
    SECRET: str
    DB_PREFIX: str
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_PHONE_NUMBER: str
    TELEGRAM_SESSION_NAME: str = "log_session"
    TELEGRAM_RECEIPT_EMAIL: str
    model_config = ConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "../../.env")
    )
env_settings = EnvSettings()
#############################

erp_settig = {
    'store' : ['Stores - MGD', 'marwan store - MGD'] # Your stores name in ERPNext
}
# these stores that used to calculate the available quantity.
#############################
opencart_settings = {
    'languages' : [1,2],  # put her the languages IDs that you have like '1,2' for Frensh and English
    "tax_class_id": "9",  # Which tax rule applies at checkout, "0"  = No tax, "9"  = Taxable Goods 
    "stock_status_id": "5", # The text label shown on the product page when quantity reaches 0, "5" = "Out of Stock"
}                         
   

# Which tax rule applies to this product at checkout.
# OpenCart looks this up and adds the correct tax percentage to the price.
# "0"  = No tax       — product is tax exempt
# "9"  = Taxable Goods — the default tax class in most OpenCart installs
# The actual percentage (e.g. 10%) is defined inside the tax class in admin.
# To check yours: Admin → System → Localisation → Taxes → Tax Classes
# Each row there has an ID — that ID is what you put here.

# The text label shown on the product page when quantity reaches 0.
# This is NOT a functional setting — it is purely a display label.
# It does NOT block purchasing (that is controlled by other settings).
# Common default values in OpenCart:
#   "5" = "Out of Stock"
#   "6" = "2-3 Days"
#   "7" = "In Stock"
#   "8" = "Pre-Order"

#################################################
# These variables should be in .env file

# API Secret key
# API_SECRET_KEY="Your_api_secret_key"

# # Erp configuration.
# ERP_BASE_URL="https://your_erpnext_domain/api/resource"  # /api/resource is important
# ERP_API_KEY=your_erpnext_key
# ERP_API_SECRET=your_erpnext_secret

# # Opencart configuration.
# BRIDGE_URL="https://your_opencart_domain/db_bridge.php"
# # Must match the SECRET defined inside db_bridge.php
# SECRET="your_opencart_secret_key"
# DB_PREFIX="your_db_prefix" # (e.g) _oc

# # Telegram configuration, get this info from https://my.telegram.org/
# TELEGRAM_API_ID="API_ID"
# TELEGRAM_API_HASH="API_HASH"
# TELEGRAM_PHONE_NUMBER="+PHONE_NUMBER" # (e.g) +123444555

# TELEGRAM_SESSION_NAME="log_session"
# TELEGRAM_RECEIPT_EMAIL="receipt_email"  # (e.g) @Marwan506

