from pydantic import BaseModel, Field


class CreateOrderReq(BaseModel):
    product_id: int = Field(description="产品ID", alias="productId")
    sku_id: int = Field(description="SKU ID", alias="skuId")
