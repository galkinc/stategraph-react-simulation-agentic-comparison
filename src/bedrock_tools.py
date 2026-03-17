from functools import lru_cache
from typing import Any, Literal, TypedDict
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class BedrockJSONSchema(BaseModel):
    """Inner JSON Schema for Bedrock tool input."""
    type: Literal["object"] = "object"
    properties: dict[str, Any] # noqa: ANN401
    required: list[str]
    additionalProperties: bool = False


class InputSchemaDict(TypedDict):
    """Typed dict for Bedrock inputSchema structure."""
    json: BedrockJSONSchema


class BedrockToolSpecInner(BaseModel):
    """Inner content of a Bedrock tool definition."""
    name: str
    description: str
    input_schema: InputSchemaDict = Field(alias="inputSchema") # noqa: F821
    
    class Config:
        populate_by_name = True


class BedrockToolItem(BaseModel):
    """Wrapper for Bedrock API tools[] array item."""
    tool_spec: BedrockToolSpecInner = Field(alias="toolSpec")
    
    class Config:
        populate_by_name = True
    
    @classmethod
    @lru_cache(maxsize=32)
    def from_pydantic(
        cls,
        model: type[BaseModel],
        tool_name: str,
        description: str,
        allow_additional: bool = False,
        _force_rebuild: bool = False  # noqa: FBT001
    ) -> "BedrockToolItem":

        if _force_rebuild:
            cls.from_pydantic.cache_clear()

        logger.debug("Creating BedrockToolSpec from model: %s", model.__name__)

        schema = model.model_json_schema()
        
        # Resolve $refs for Bedrock compatibility
        properties = cls._resolve_refs(schema)
        
        json_schema = BedrockJSONSchema(
            properties=properties,
            required=schema.get("required", []),
            additionalProperties=allow_additional,
        )

        inner = BedrockToolSpecInner(
            name=tool_name,
            description=description,
            input_schema={"json": json_schema},
        )
        return cls(tool_spec=inner)

    @classmethod
    def _resolve_refs(cls, schema: dict) -> dict:
        """Resolve $ref definitions inline for Bedrock compatibility."""
        defs = schema.get("$defs", {})
        properties = schema.get("properties", {}).copy()
        
        for key, value in properties.items():
            if isinstance(value, dict) and "$ref" in value:
                ref = value["$ref"]
                if ref.startswith("#/$defs/"):
                    def_name = ref.split("/")[-1]
                    if def_name in defs:
                        def_schema = defs[def_name].copy()
                        # Remove Bedrock-incompatible fields
                        def_schema.pop("title", None)
                        # Recursively resolve nested refs
                        if "properties" in def_schema:
                            def_schema["properties"] = cls._resolve_refs(def_schema)
                        properties[key] = def_schema
        
        return properties

    def to_bedrock_dict(self) -> dict[str, Any]: # noqa: ANN401
        """Export to dict for Bedrock API call."""
        return self.model_dump(by_alias=True, exclude_none=True)