from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class InferenceCreateResponse(BaseModel):
    job_id: str
    status: str


class ImageInfo(BaseModel):
    width: int
    height: int


class TileInfo(BaseModel):
    tile_size: int
    overlap: int
    columns: int
    rows: int
    total: int


DegradationMode = Literal["direct", "synthetic_noise", "blur", "broken", "missing", "occlusion"]


class MetricsInfo(BaseModel):
    """psnr_vs_input/ssim_vs_input compare output against whatever was actually
    fed to the model. In "direct" mode that's the uploaded image itself (no
    ground truth exists, so this only measures how much the model changed the
    image - not accuracy). In any synthetic degradation mode, the uploaded image
    is clean and its degraded version is fed to the model; ground-truth metrics
    compare the output against that original clean image.
    """
    psnr_vs_input: float
    ssim_vs_input: float
    psnr_vs_ground_truth: Optional[float] = None
    ssim_vs_ground_truth: Optional[float] = None


class PageResult(BaseModel):
    output_id: str
    degraded_id: Optional[str] = None
    output_url: str
    degraded_url: Optional[str] = None
    input: ImageInfo
    output: ImageInfo
    tiles: TileInfo
    metrics: MetricsInfo


JobStatus = Literal["queued", "loading_model", "processing", "completed", "failed"]


class InferenceStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = 0
    processed_tiles: int = 0
    total_tiles: int = 0
    elapsed_seconds: float = 0.0
    error: Optional[str] = None

    input: Optional[ImageInfo] = None
    output: Optional[ImageInfo] = None
    tiles: Optional[TileInfo] = None
    output_url: Optional[str] = None
    degraded_url: Optional[str] = None
    pages: list[PageResult] = Field(default_factory=list)
    processing_time_seconds: Optional[float] = None
    metrics: Optional[MetricsInfo] = None


class InferenceSettings(BaseModel):
    tile_size: int = 128
    tile_overlap: int = 16
    processing_mode: Literal["tile", "full_image"] = "tile"
    batch_size: int = 1
    device: Literal["auto", "cpu", "cuda"] = "auto"
    degradation_mode: DegradationMode = "direct"
    noise_sigma: float = 25.0
    degradation_strength: int = 25


class HistoryRecord(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    job_id: str
    input_filename: str
    model_filename: str
    input_id: Optional[str] = None
    output_id: Optional[str] = None
    output_ids: list[str] = Field(default_factory=list)
    degraded_ids: list[str] = Field(default_factory=list)
    degraded_id: Optional[str] = None
    deleted_at: Optional[str] = None
    owner_id: Optional[str] = None
    degradation_mode: Optional[DegradationMode] = None
    degradation_strength: Optional[int] = None
    status: JobStatus
    processing_time_seconds: Optional[float] = None
    created_at: str