# HEIF regression images

These unmodified test images are from the Pillow-Heif project at commit
`558ee2bfbe85a64b4371bcc1bc067883c5f9573d` and are distributed under its
BSD 3-Clause license, reproduced in `LICENSE.txt`.

- `spatial_photo.heic`: a 2560 × 2560, two-frame spatial photo, used to exercise
  a real multi-image HEIF container through upload validation and conversion.
  Source: https://github.com/bigcat88/pillow_heif/blob/558ee2bfbe85a64b4371bcc1bc067883c5f9573d/tests/images/heif_other/spatial_photo.heic
- `unsupported_depth_image.heic`: a small primary photo with a depth item that
  does not need to be decoded for web display.
  Source: https://github.com/bigcat88/pillow_heif/blob/558ee2bfbe85a64b4371bcc1bc067883c5f9573d/tests/images/heif_special/unsupported_depth_image.heic

Neither file contains QOT user content. Both decode with Pillow-Heif 1.5.0 as
well as 1.8.1; these are compatibility regressions, not reproductions of the
specific user's unprovided failing image.
