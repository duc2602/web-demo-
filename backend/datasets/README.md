# Handwriting restoration pairs

Generate paired clean/degraded samples from clean handwritten-page images:

```powershell
Set-Location backend
uv run --isolated --python 3.12 --with-requirements .\requirements.txt `
  python -m app.inference.dataset_builder `
  --source .\uploads\clean-page-1.png `
  --source .\uploads\clean-page-2.png
```

The builder deduplicates identical page pixels and writes `clean/`, `degraded/`,
and `manifest.csv` under `datasets/handwriting_pairs`. The manifest pairs each
degraded image with its clean target and records degradation mode, severity,
seed, and split. Supported modes are synthetic noise, blur, broken strokes,
missing regions, and occlusion.

The current workspace only contains one unique clean page among its synthetic
inference sources. Its generated pairs are useful for pipeline experiments,
not for training a general-purpose model. Add distinct clean pages before
relying on validation/test metrics or model quality claims.