import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import torch
from PIL import Image

from app.inference.pipeline import InferencePipeline


class SlightlyChangedModel(torch.nn.Module):
    def forward(self, image: torch.Tensor) -> torch.Tensor:
        return image * 0.99


class MultiPageInferenceTests(unittest.TestCase):
    def test_pipeline_runs_and_saves_each_detected_page(self) -> None:
        image = np.full((600, 800, 3), (55, 60, 65), dtype=np.uint8)
        first = np.array([[40, 35], [360, 50], [350, 540], [30, 520]], dtype=np.int32)
        second = np.array([[430, 50], [760, 35], [770, 520], [440, 540]], dtype=np.int32)
        cv2.fillConvexPoly(image, first, (225, 225, 225))
        cv2.fillConvexPoly(image, second, (220, 220, 220))
        cv2.putText(image, "PAGE 1", (90, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (20, 20, 20), 2)
        cv2.putText(image, "PAGE 2", (500, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (20, 20, 20), 2)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.png"
            output_path = root / "output.png"
            Image.fromarray(image).save(input_path)
            pipeline = InferencePipeline()

            with patch.object(
                pipeline.loader,
                "load",
                return_value=(SlightlyChangedModel(), torch.device("cpu")),
            ):
                result = pipeline.run(
                    model_path=root / "unused.pth",
                    input_path=input_path,
                    output_path=output_path,
                    processing_mode="full_image",
                    device="cpu",
                )

            self.assertEqual(len(result["pages"]), 2)
            self.assertTrue(output_path.is_file())
            self.assertTrue(all((root / f"{page['output_id']}.png").is_file() for page in result["pages"]))
            self.assertEqual(len({page["output_id"] for page in result["pages"]}), 2)


if __name__ == "__main__":
    unittest.main()
