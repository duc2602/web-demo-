import { useEffect, useRef, useState } from "react";
import { ImagePlus, RefreshCw } from "lucide-react";

interface Props {
  imageFile: File | null;
  onImageSelected: (file: File) => void;
}

export default function ImageUploader({ imageFile, onImageSelected }: Props) {
  const [dragActive, setDragActive] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [dims, setDims] = useState<{ w: number; h: number } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (imageFile) {
      const url = URL.createObjectURL(imageFile);
      setPreviewUrl(url);
      const img = new Image();
      img.onload = () => setDims({ w: img.naturalWidth, h: img.naturalHeight });
      img.src = url;
      return () => URL.revokeObjectURL(url);
    } else {
      setPreviewUrl(null);
      setDims(null);
    }
  }, [imageFile]);

  function handleFile(file: File) {
    onImageSelected(file);
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div className="card p-5 sm:p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-white tracking-tight">Input image</p>
          <p className="mt-1 text-xs text-zinc-400">Select the image you want to process.</p>
        </div>
        {imageFile && (
          <span className="shrink-0 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] font-medium text-zinc-300">
            IMAGE READY
          </span>
        )}
      </div>

      {!previewUrl && (
        <div
          className={`dropzone ${dragActive ? "active" : ""} flex min-h-[300px] flex-col items-center justify-center px-5 py-12 text-center cursor-pointer`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
        >
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg border border-accent/20 bg-accent/10">
            <ImagePlus size={20} className="text-accent" />
          </div>
          <p className="text-sm font-medium text-white">Drag and drop an image</p>
          <p className="mt-1 text-xs text-zinc-400">or click anywhere here to browse</p>
          <p className="mt-4 text-xs text-zinc-400">PNG, JPG, WEBP, BMP, TIFF · Any resolution</p>
        </div>
      )}

      {previewUrl && (
        <div>
          <div className="flex min-h-[300px] max-h-[420px] items-center justify-center overflow-hidden rounded-xl border border-white/10 bg-black/30 p-2 shadow-inner">
            <img src={previewUrl} alt="Input preview" className="max-h-[400px] w-auto max-w-full rounded-lg object-contain" />
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-zinc-300">
            <span>{dims ? `Resolution  ${dims.w} × ${dims.h}` : "Reading image dimensions..."}</span>
            <span>{imageFile ? `File size  ${(imageFile.size / (1024 * 1024)).toFixed(1)} MB` : ""}</span>
          </div>
          <div className="mt-4 border-t border-white/[0.07] pt-4">
            <button
              type="button"
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/[0.025] px-3.5 text-sm font-medium text-zinc-200 transition-colors hover:border-white/25 hover:bg-white/[0.06]"
              onClick={() => inputRef.current?.click()}
            >
              <RefreshCw size={14} aria-hidden="true" />
              Change image
            </button>
          </div>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept=".png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
    </div>
  );
}
