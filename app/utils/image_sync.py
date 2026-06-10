import httpx
import os
from colorama import Fore
from app.config.settings import env_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

def get_oc_image_path(erp_image_path: str) -> str | None:
    """
    Translates an ERPNext image path (or URL) into the relative path used by OpenCart.
    Example: /files/image.png -> catalog/erp_sync/image.png
    """
    if not erp_image_path:
        return None
    filename = os.path.basename(erp_image_path.split("?")[0])  # strip query params
    return f"catalog/erp_sync/{filename}"

async def sync_image(erp_image_path: str):
    """
    Downloads image from ERPNext (or external URL) and uploads it to OpenCart server via Bridge.
    Returns the relative path for OpenCart database.
    """
    oc_relative_path = get_oc_image_path(erp_image_path)
    if not oc_relative_path:
        return None

    # 1. Determine the full download URL and whether auth is needed
    if erp_image_path.startswith("http://") or erp_image_path.startswith("https://"):
        # External URL (e.g. pexels.com) — download directly, no auth
        full_download_url = erp_image_path
        auth = None
    else:
        # Relative ERPNext path (e.g. /files/image.png) — needs ERPNext auth
        erp_base = env_settings.ERP_BASE_URL.replace("/api/resource", "")
        full_download_url = erp_base + erp_image_path
        auth = (env_settings.ERP_API_KEY, env_settings.ERP_API_SECRET)

    filename = os.path.basename(erp_image_path.split("?")[0])  # strip query params

    
    try:
        # Use headers that external sites accept (Pexels, etc.)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
            # step 1: Download image
            logger.info(f"Downloading image from: {full_download_url}")
            response = await client.get(full_download_url, auth=auth, timeout=120)
            
            if response.status_code != 200:
                logger.error(f"Failed to download image: HTTP {response.status_code} from {full_download_url}")
                return None
            
            image_content = response.content
            logger.info(f"Downloaded {len(image_content)} bytes")
            
            # step 2: Upload to OpenCart Bridge
            files = {'file': (filename, image_content)}
            data = {
                'secret': env_settings.SECRET,
                'path': oc_relative_path
            }
            
            upload_response = await client.post(
                env_settings.BRIDGE_URL, 
                data=data, 
                files=files, 
                timeout=120
            )
            
            if upload_response.status_code == 200:
                result = upload_response.json()
                if result.get('status') == 'success':
                    logger.info(Fore.GREEN + f"Image synced successfully: {oc_relative_path}")
                    return oc_relative_path
                elif result.get('error'):
                    logger.error(f"Bridge error: {result.get('error')}")
                else:
                    logger.error(f"Unexpected bridge response: {result}")
            else:
                logger.error(f"Bridge returned HTTP {upload_response.status_code}")
                
    except Exception as e:
        logger.error(f"Error syncing image {erp_image_path}", exc_info=True)
        
    return None
