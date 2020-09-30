from typing import Optional, Tuple

from fastapi import FastAPI, Request
from fastapi_tools import limit


def limit_func(requests: Request) -> Tuple[str, str]:
    return requests.session['user'], requests.session['group']


app = FastAPI()

app.add_middleware(
    limit.LimitMiddleware,
    func=limit_func,
    rule_dict={
        r"^/api": [limit.Rule(second=10, group='admin'), limit.Rule(second=10, group='user')]
    }
)


@app.get("/")
@limit.limit([limit.Rule(second=10)], limit_func=limit.func.client_ip)
async def root():
    return {"Hello": "World"}


@app.get("/api/users/{user_id}/items/{item_id}")
async def read_user_item(
    user_id: int, item_id: str, q: Optional[str] = None, short: bool = False
):
    """
    copy from:https://fastapi.tiangolo.com/tutorial/query-params/#multiple-path-and-query-parameters
    """
    item = {"item_id": item_id, "owner_id": user_id}
    if q:
        item.update({"q": q})
    if not short:
        item.update(
            {"description": "This is an amazing item that has a long description"}
        )
    return item


@app.get("/api/users/login")
async def user_login():
    return 'ok'


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
