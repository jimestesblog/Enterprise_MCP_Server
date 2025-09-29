from typing import Any, Dict, List, Optional


class Tool:
    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description

    # async def invoke(self, **kwargs) -> Any:
    #     raise NotImplementedError

    def to_mcp_def(self) -> Dict[str, Any]:
        # Placeholder for converting to MCP tool definition
        return {"name": self.name, "description": self.description}


class EchoTool(Tool):
    def __init__(self, conf: Dict[str, Any]) -> None:
        super().__init__(name=conf.get("name"), description=conf.get("description", ""))
        # Echo has no specific params, but keep for consistency
        self.params = conf.get("params", {})

    # async def invoke(self, text: str, **kwargs) -> Dict[str, Any]:
    #     return {"echo": text}


# class HttpRequestTool(Tool):
#     def __init__(self, conf: Dict[str, Any]) -> None:
#         name = conf.get("name")
#         description = conf.get("description", "")
#         super().__init__(name, description)
#         params = conf.get("params", {})
#         base_url = params.get("base_url")
#         if not base_url:
#             raise ValueError("http_request tool requires params.base_url")
#         self.base_url = str(base_url).rstrip("/")
#         allowed_paths = params.get("allowed_paths") or []
#         self.allowed_paths = set(allowed_paths)
#
#     def _is_allowed(self, path: str) -> bool:
#         if not self.allowed_paths:
#             return True
#         p = path.lstrip("/")
#         return any(p.startswith(ap.lstrip("/")) for ap in self.allowed_paths)


