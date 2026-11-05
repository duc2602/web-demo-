import unittest

import cv2
import numpy as np

from app.inference.preprocessing import preprocess_phone_photo, preprocess_phone_photos


class PhonePhotoPreprocessingTests(unittest.TestCase):
    def test_image_without_clear_page_contour_is_preserved(self) -> None:
        image = np.full((120, 180, 3), 235, dtype=np.uint8)
        cv2.putText(image, "scan", (30, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)

        result = preprocess_phone_photo(image)

        self.assertEqual(result.shape, image.shape)
        self.assertEqual(result.dtype, np.uint8)
        np.testing.assert_array_equal(result, image)
        np.testing.assert_array_equal(preprocess_phone_photos(image)[0], image)

    def test_rectifies_a_document_and_removes_color_channels(self) -> None:
        image = np.full((300, 400, 3), (55, 60, 65), dtype=np.uint8)
        corners = np.array([[70, 35], [340, 60], [320, 270], [45, 245]], dtype=np.int32)
        cv2.fillConvexPoly(image, corners, (220, 225, 230))
        cv2.putText(image, "TEST", (110, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (20, 20, 20), 2)

        result = preprocess_phone_photo(image)

        self.assertNotEqual(result.shape[:2], image.shape[:2])
        self.assertEqual(result.shape[2], 3)
        np.testing.assert_array_equal(result[:, :, 0], result[:, :, 2])
        self.assertGreater(int(result.max()), 200)
        self.assertLess(int(result.min()), 100)

    def test_detects_and_rectifies_multiple_documents(self) -> None:
        image = np.full((600, 800, 3), (55, 60, 65), dtype=np.uint8)
        first = np.array([[40, 35], [360, 50], [350, 540], [30, 520]], dtype=np.int32)
        second = np.array([[430, 50], [760, 35], [770, 520], [440, 540]], dtype=np.int32)
        cv2.fillConvexPoly(image, first, (225, 225, 225))
        cv2.fillConvexPoly(image, second, (220, 220, 220))
        cv2.putText(image, "PAGE 1", (90, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (20, 20, 20), 2)
        cv2.putText(image, "PAGE 2", (500, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (20, 20, 20), 2)

        pages = preprocess_phone_photos(image)

        self.assertEqual(len(pages), 2)
        self.assertTrue(all(page.dtype == np.uint8 and page.shape[2] == 3 for page in pages))
        self.assertTrue(all(page.shape[0] > page.shape[1] for page in pages))

    def test_rejects_non_rgb_or_non_uint8_input(self) -> None:
        with self.assertRaises(ValueError):
            preprocess_phone_photo(np.zeros((10, 10), dtype=np.uint8))
        with self.assertRaises(ValueError):
            preprocess_phone_photo(np.zeros((10, 10, 3), dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
