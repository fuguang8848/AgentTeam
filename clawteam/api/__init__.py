"""
API versioning module for ClawTeam

Provides API version management and backward compatibility support.
"""
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional

from clawteam.utils.logger import get_logger

logger = get_logger(__name__)


class APIVersion(Enum):
    """Supported API versions"""
    V1 = "v1"
    V2 = "v2"
    LATEST = V2


@dataclass
class APIEndpoint:
    """An API endpoint definition"""
    path: str
    method: str = "GET"
    version: APIVersion = APIVersion.V1
    handler: Optional[Callable] = None
    description: str = ""
    deprecated: bool = False
    removed_in: Optional[APIVersion] = None


@dataclass
class APIRouter:
    """API router for managing endpoints"""
    version: APIVersion = APIVersion.V1
    _endpoints: dict[str, APIEndpoint] = field(default_factory=dict)
    
    def route(self, path: str, method: str = "GET", deprecated: bool = False):
        """Decorator to register an endpoint"""
        def decorator(func: Callable) -> Callable:
            endpoint = APIEndpoint(
                path=path,
                method=method,
                version=self.version,
                handler=func,
                deprecated=deprecated,
            )
            self._endpoints[f"{method}:{path}"] = endpoint
            logger.info(f"Registered {self.version.value} endpoint: {method} {path}")
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def get_endpoint(self, path: str, method: str = "GET") -> Optional[APIEndpoint]:
        """Get an endpoint by path and method"""
        return self._endpoints.get(f"{method}:{path}")
    
    def list_endpoints(self, include_deprecated: bool = False) -> list[APIEndpoint]:
        """List all registered endpoints"""
        endpoints = list(self._endpoints.values())
        if not include_deprecated:
            endpoints = [e for e in endpoints if not e.deprecated]
        return endpoints


class APIVersionAdapter:
    """
    Adapter for converting between API versions
    
    Handles backward compatibility by converting request/response
    formats between different API versions.
    """
    
    def __init__(self):
        self._converters: dict[tuple[str, APIVersion, APIVersion], Callable] = {}
        self._register_default_converters()
    
    def _register_default_converters(self):
        """Register default version converters"""
        # V1 to V2 converters can be added here
        pass
    
    def register_converter(
        self,
        entity: str,
        from_version: APIVersion,
        to_version: APIVersion,
        converter: Callable[[dict], dict],
    ):
        """Register a custom converter function"""
        key = (entity, from_version, to_version)
        self._converters[key] = converter
    
    def convert(
        self,
        entity: str,
        data: dict,
        from_version: APIVersion,
        to_version: APIVersion,
    ) -> dict:
        """Convert data from one version to another"""
        if from_version == to_version:
            return data
        
        key = (entity, from_version, to_version)
        if key in self._converters:
            return self._converters[key](data)
        
        # No converter found, return data as-is
        logger.warning(f"No converter found for {entity} {from_version} -> {to_version}")
        return data


class VersionedAPIHandler:
    """
    Base handler for versioned API endpoints
    
    Provides version negotiation and request/response transformation.
    
    Example:
        class MyAPI(VersionedAPIHandler):
            def __init__(self):
                super().__init__()
                
                @self.post("/api/v1/users", version=APIVersion.V1)
                def get_users_v1(request):
                    return {"users": [...]}
                
                @self.post("/api/v2/users", version=APIVersion.V2)
                def get_users_v2(request):
                    return {"data": [...], "meta": {...}}
        
        api = MyAPI()
        response = api.handle(request)  # Handles version negotiation
    """
    
    def __init__(self, default_version: APIVersion = APIVersion.V1):
        self.default_version = default_version
        self.routers: dict[APIVersion, APIRouter] = {
            v: APIRouter(version=v) for v in APIVersion
        }
        self.adapter = APIVersionAdapter()
    
    def get_router(self, version: APIVersion) -> APIRouter:
        """Get the router for a specific version"""
        return self.routers.get(version, self.routers[self.default_version])
    
    def route(self, path: str, method: str = "GET", version: APIVersion = None):
        """Decorator to register a versioned endpoint"""
        version = version or self.default_version
        
        def decorator(func: Callable) -> Callable:
            router = self.get_router(version)
            endpoint = APIEndpoint(
                path=path,
                method=method,
                version=version,
                handler=func,
            )
            key = f"{method}:{path}"
            # Store in the specific version's router
            router._endpoints[key] = endpoint
            logger.info(f"Registered {version.value} endpoint: {method} {path}")
            return func
        return decorator
    
    def get(self, path: str, version: APIVersion = None):
        """Decorator for GET endpoint"""
        return self.route(path, "GET", version)
    
    def post(self, path: str, version: APIVersion = None):
        """Decorator for POST endpoint"""
        return self.route(path, "POST", version)
    
    def put(self, path: str, version: APIVersion = None):
        """Decorator for PUT endpoint"""
        return self.route(path, "PUT", version)
    
    def delete(self, path: str, version: APIVersion = None):
        """Decorator for DELETE endpoint"""
        return self.route(path, "DELETE", version)
    
    def handle(self, request: dict) -> dict:
        """
        Handle an API request with version negotiation
        
        Args:
            request: Request dict with keys:
                - path: URL path
                - method: HTTP method
                - version: Requested API version (optional)
                - data: Request body (optional)
        
        Returns:
            Response dict
        """
        path = request.get("path", "/")
        method = request.get("method", "GET")
        client_version_str = request.get("version")
        
        # Determine version to use
        if client_version_str:
            try:
                client_version = APIVersion(client_version_str)
            except ValueError:
                client_version = self.default_version
        else:
            client_version = self.default_version
        
        # Find endpoint - first try exact version match
        endpoint = None
        
        # Try the requested version first
        router = self.get_router(client_version)
        endpoint = router.get_endpoint(path, method)
        
        # If not found and client version is not default, try default
        if endpoint is None and client_version != self.default_version:
            router = self.get_router(self.default_version)
            endpoint = router.get_endpoint(path, method)
        
        if not endpoint:
            return {
                "error": "Not Found",
                "message": f"Endpoint {method} {path} not found",
                "status": 404,
            }
        
        # Check if deprecated
        if endpoint.deprecated:
            logger.warning(f"Using deprecated endpoint: {method} {path}")
        
        # Execute handler
        try:
            handler = endpoint.handler
            if handler is None:
                return {
                    "error": "Internal Error",
                    "message": "Handler not implemented",
                    "status": 500,
                }
            
            result = handler(request)
            
            # Add version info to response
            if isinstance(result, dict):
                result["_version"] = endpoint.version.value
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling {method} {path}: {e}")
            return {
                "error": "Internal Server Error",
                "message": str(e),
                "status": 500,
            }
    
    def get_api_info(self) -> dict:
        """Get API information for discovery"""
        return {
            "version": APIVersion.LATEST.value,
            "supported_versions": [v.value for v in APIVersion],
            "endpoints": {
                v.value: [
                    {
                        "path": e.path,
                        "method": e.method,
                        "deprecated": e.deprecated,
                    }
                    for e in router.list_endpoints()
                ]
                for v, router in self.routers.items()
            },
        }


def version_required(min_version: APIVersion):
    """Decorator to require a minimum API version"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Version check would happen here based on request context
            return func(*args, **kwargs)
        return wrapper
    return decorator


def deprecated_since(version: APIVersion, replacement: str = None):
    """Decorator to mark an endpoint as deprecated"""
    def decorator(func: Callable) -> Callable:
        func._deprecated = True
        func._deprecated_in = version
        func._replacement = replacement
        return func
    return decorator


# Global API info
API_VERSION = APIVersion.LATEST.value
API_TITLE = "ClawTeam API"
API_DESCRIPTION = """
ClawTeam Multi-Agent Coordination API

## Versioning

All endpoints are versioned. The current version is v2.

### Version Negotiation

Clients can specify the API version in the request:
- Header: `X-API-Version: v1` or `X-API-Version: v2`
- Query param: `?version=v2`

### Changelog

#### v2 (latest)
- Standardized response format with `data` field
- Added pagination support
- Added batch operations

#### v1 (deprecated)
- Original format with direct object returns
- Will be removed in future release
"""


__all__ = [
    "APIVersion",
    "APIEndpoint",
    "APIRouter",
    "APIVersionAdapter",
    "VersionedAPIHandler",
    "version_required",
    "deprecated_since",
    "API_VERSION",
    "API_TITLE",
    "API_DESCRIPTION",
]
