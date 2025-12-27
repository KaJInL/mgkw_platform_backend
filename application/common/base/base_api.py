from fastapi import APIRouter


class BaseAPI:
    def __init__(self, router: APIRouter):
        self.router = router
