from pydantic import BaseModel, Field

class PaginationReq(BaseModel):
    """
    通用分页请求参数
    """
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    pageSize: int = Field(default=10, ge=1, le=100, description="每页数量，范围 1-100")

