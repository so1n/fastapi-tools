import time
from typing import Callable, Optional, Set

from aio_statsd import StatsdClient

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from fast_tools.base import NAMESPACE, RouteTrie, BaseSearchRouteMiddleware


class StatsdMiddleware(BaseSearchRouteMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        client: StatsdClient,
        app_name: str = NAMESPACE,
        prefix: str = NAMESPACE,
        route_trie: Optional["RouteTrie"] = None,
        url_replace_handle: Optional[Callable] = None,
        block_url_set: Optional[Set[str]] = None,
    ) -> None:
        super().__init__(app, route_trie=route_trie)
        self._block_url_set = block_url_set
        self._client: StatsdClient = client
        self._metric = ""
        self._url_replace_handle = url_replace_handle
        if prefix:
            self._metric += prefix + "."
        if app_name:
            self._metric += app_name + "."

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method: str = request.method
        url_path: str = self.search_route_url(request)

        if url_path in self._block_url_set:
            return await call_next(request)

        if self._url_replace_handle:
            url_path = self._url_replace_handle(url_path)

        metric: str = f"{self._metric}{method}.{url_path}."
        self._client.gauge(metric + "request_in_progress", 1)
        self._client.gauge(metric + "request_count", 1)

        status_code = 500
        start_time = time.time()
        request_result = "fail"
        try:
            response = await call_next(request)
            status_code = response.status_code
            request_result = "success"
            return response
        except Exception as e:
            self._client.gauge(metric + f"exception.{type(e).__name__}", 1)
            raise e
        finally:
            self._client.timer(metric + f"{request_result}.request_time", time.time() - start_time)
            self._client.gauge(metric + f"{status_code}.response_count", 1)
            self._client.gauge(metric + "request_in_progress", -1)
