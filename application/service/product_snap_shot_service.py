from application.common.base import BaseService
from application.common.models.product import ProductSnapshot


class ProductSnapShotService(BaseService[ProductSnapshot]):
    pass


product_snap_shot_service = ProductSnapShotService()





