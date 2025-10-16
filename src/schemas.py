from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator, model_validator

from .config import get_settings

class WriteRequest(BaseModel):
    topic: str = Field(..., description="文章主题", min_length=1, max_length=500, example="machine learning in healthcare")
    style: Optional[str] = Field(None, description="文章风格类型")
    keywords: Optional[List[str]] = Field(None, description="关键词列表")
    instructions: Optional[str] = Field(None, description="额外的用户指令")
    focus_areas: Optional[List[str]] = Field(None, description="重点关注的领域")
    language: Optional[str] = Field(None, description="文章语言")
    include_references: bool = Field(True, description="是否包含参考文献")
    max_sources: Optional[int] = Field(None, ge=1, description="最大参考文献数量")
    request_id: str = Field(default_factory=lambda: str(uuid4()), description="请求唯一标识符")
    translate_to: Optional[List[str]] = Field(None, description="需要翻译的目标语言列表")
    generate_images: bool = Field(False, description="是否为文章生成插图")

    @staticmethod
    def _deduplicate_preserve_order(values: Optional[List[str]]) -> Optional[List[str]]:
        if not values: return values
        seen, result = set(), []
        for item in values:
            cleaned = item.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
        return result or None

    @field_validator('keywords', 'focus_areas')
    def validate_lists(cls, v):
        return cls._deduplicate_preserve_order(v)

    @field_validator('style', mode="before")
    def apply_style_defaults(cls, v):
        settings = get_settings().api
        value = (v or "").strip() if isinstance(v, str) else v
        if value and value not in settings.supported_styles:
            raise ValueError(f"Unsupported style '{value}'. Supported: {', '.join(settings.supported_styles)}")
        return value or None

    @field_validator('language', mode="before")
    def apply_language_defaults(cls, v):
        settings = get_settings().api
        value = (v or "").strip() if isinstance(v, str) else v
        if value and value not in settings.supported_languages:
            raise ValueError(f"Unsupported language '{value}'. Supported: {', '.join(settings.supported_languages)}")
        return value or None

    @field_validator('max_sources', mode="before")
    def apply_max_sources_defaults(cls, v):
        settings = get_settings().api
        if v is None: return None
        try: value = int(v)
        except (TypeError, ValueError): raise ValueError("max_sources must be an integer")
        if value > settings.max_sources_limit:
            raise ValueError(f"max_sources {value} exceeds limit {settings.max_sources_limit}")
        return value

    @model_validator(mode="after")
    def apply_defaults_and_validate(self):
        api_cfg = get_settings().api
        if not self.style: self.style = api_cfg.default_style
        if not self.language: self.language = api_cfg.default_language
        if self.keywords and len(self.keywords) > api_cfg.max_keywords:
            raise ValueError(f"Too many keywords. Max: {api_cfg.max_keywords}")
        if self.focus_areas and len(self.focus_areas) > api_cfg.max_focus_areas:
            raise ValueError(f"Too many focus areas. Max: {api_cfg.max_focus_areas}")
        if self.max_sources is None: self.max_sources = api_cfg.default_max_sources
        return self

class WriteResponse(BaseModel):
    article_id: str
    status: Literal["completed", "failed", "processing"]
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_time: Optional[float] = None
    word_count: Optional[int] = None
    error: Optional[str] = None
    trace_id: Optional[str] = None
    translations: Optional[Dict[str, str]] = None
    generated_images: Optional[List[str]] = None
    file_paths: Optional[Dict[str, str]] = Field(default_factory=dict)

class TranslateRequest(BaseModel):
    article_id: str = Field(..., description="要翻译的文章ID")
    target_languages: List[str] = Field(..., min_length=1)
    source_file: Optional[str] = Field(None, description="源文件路径 (可选)")

class ImageGenerationRequest(BaseModel):
    article_id: str = Field(..., description="要生成图片的文章ID")
    source_file: Optional[str] = Field(None, description="源文件路径 (可选)")
    number_of_images: int = Field(1, gt=0)

class PubMedSearchRequest(BaseModel):
    topic: str = Field(..., description="The topic to research on PubMed.", min_length=1, max_length=500)
    keywords: Optional[List[str]] = Field(None, description="Keywords to refine the PubMed search.")
    max_results: Optional[int] = Field(10, description="Maximum number of articles to fetch from PubMed.")

class WriteFromPubMedRequest(BaseModel):
    article_id: str = Field(..., description="The ID of the article to be written from existing PubMed data.")
    topic: str = Field(..., description="The main topic of the article to be written.")
    style: Optional[str] = Field("scientific review", description="The style of the article.")
    language: Optional[str] = Field("en", description="The language of the article.")
    translate_to: Optional[List[str]] = Field(None, description="A list of languages to translate the article into.")
    instructions: Optional[str] = Field(None, description="Additional user instructions for writing.")
    focus_areas: Optional[List[str]] = Field(None, description="Areas to focus on during writing.")
    include_references: bool = Field(True, description="Whether to include references in the article.")