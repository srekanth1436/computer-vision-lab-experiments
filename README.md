# Computer Vision Lab Experiments

A clean, GitHub-ready collection of **40 Computer Vision laboratory experiments**
implemented using Python, OpenCV, NumPy, and Pillow.

## Student

**V. Sreekanth**  
B.Tech Computer Science and Engineering  
SIMATS Engineering

## Repository Highlights

- 40 separately organised experiment folders
- Corrected, portable Python programs with no computer-specific file paths
- Input and output folders for every experiment
- Sample images and videos included
- Generated result files included
- Individual README file for every experiment
- Repository-level syntax checker
- GitHub Actions workflow
- MIT License

## Installation

```bash
git clone <your-repository-url>
cd computer-vision-lab-experiments
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

### macOS/Linux

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Run One Experiment

```bash
python Experiment-01-grayscale-conversion/program.py
```

## Check All Python Programs

```bash
python check_repository.py
```

## Experiments

| No. | Experiment | Aim |
|---:|---|---|
| 01 | [Grayscale Conversion](Experiment-01-grayscale-conversion/) | Convert a colour image into grayscale. |
| 02 | [Gaussian Blur](Experiment-02-gaussian-blur/) | Blur an image using the Gaussian filter. |
| 03 | [Canny Outline](Experiment-03-canny-outline/) | Show image outlines using the Canny method. |
| 04 | [Basic Image Dilation](Experiment-04-basic-image-dilation/) | Dilate a grayscale image. |
| 05 | [Basic Image Erosion](Experiment-05-basic-image-erosion/) | Erode a grayscale image. |
| 06 | [Slow and Fast Motion Video](Experiment-06-slow-and-fast-motion-video/) | Create slow-motion and fast-motion versions of a video. |
| 07 | [Webcam Slow and Fast Motion](Experiment-07-webcam-slow-and-fast-motion/) | Capture webcam video and display smaller and larger views. |
| 08 | [Image Scaling](Experiment-08-image-scaling/) | Scale an image to bigger and smaller sizes. |
| 09 | [Clockwise and Counterclockwise Rotation](Experiment-09-clockwise-and-counterclockwise-rotation/) | Rotate an image in both directions. |
| 10 | [Image Translation](Experiment-10-image-translation/) | Move image content from one position to another. |
| 11 | [Affine Transformation](Experiment-11-affine-transformation/) | Apply an affine transformation to an image. |
| 12 | [Perspective Transformation on Image](Experiment-12-perspective-transformation-on-image/) | Apply a perspective transformation to an image. |
| 13 | [Perspective Transformation on Video](Experiment-13-perspective-transformation-on-video/) | Apply perspective transformation to every video frame. |
| 14 | [Homography Transformation](Experiment-14-homography-transformation/) | Transform an image using a homography matrix. |
| 15 | [Direct Linear Transformation](Experiment-15-direct-linear-transformation/) | Estimate a homography using the Direct Linear Transform algorithm. |
| 16 | [Canny Edge Detection](Experiment-16-canny-edge-detection/) | Detect edges using the Canny method. |
| 17 | [Sobel Edge Detection Along X Axis](Experiment-17-sobel-edge-detection-along-x-axis/) | Detect vertical edges using the Sobel X derivative. |
| 18 | [Sobel Edge Detection Along Y Axis](Experiment-18-sobel-edge-detection-along-y-axis/) | Detect horizontal edges using the Sobel Y derivative. |
| 19 | [Sobel Edge Detection Along XY Axes](Experiment-19-sobel-edge-detection-along-xy-axes/) | Combine Sobel X and Sobel Y edges. |
| 20 | [Laplacian Mask with Negative Center](Experiment-20-laplacian-mask-with-negative-center/) | Apply a Laplacian mask with a negative centre coefficient. |
| 21 | [Laplacian Mask with Diagonal Neighbours](Experiment-21-laplacian-mask-with-diagonal-neighbours/) | Apply a Laplacian mask using all eight neighbours. |
| 22 | [Laplacian Mask with Positive Center](Experiment-22-laplacian-mask-with-positive-center/) | Sharpen using a positive-centre Laplacian kernel. |
| 23 | [Unsharp Masking](Experiment-23-unsharp-masking/) | Sharpen an image using unsharp masking. |
| 24 | [High-Boost Filtering](Experiment-24-high-boost-filtering/) | Sharpen an image using high-boost filtering. |
| 25 | [Gradient Masking](Experiment-25-gradient-masking/) | Sharpen an image using a gradient mask. |
| 26 | [Histogram Equalization](Experiment-26-histogram-equalization/) | Improve image contrast using histogram equalization. |
| 27 | [Image Thresholding](Experiment-27-image-thresholding/) | Perform global, adaptive, and Otsu thresholding. |
| 28 | [Contour Detection](Experiment-28-contour-detection/) | Detect and draw object contours. |
| 29 | [Morphological Erosion](Experiment-29-morphological-erosion/) | Perform morphological erosion. |
| 30 | [Morphological Dilation](Experiment-30-morphological-dilation/) | Perform morphological dilation. |
| 31 | [Morphological Opening](Experiment-31-morphological-opening/) | Perform morphological opening. |
| 32 | [Morphological Closing](Experiment-32-morphological-closing/) | Perform morphological closing. |
| 33 | [Morphological Gradient](Experiment-33-morphological-gradient/) | Extract object boundaries using morphological gradient. |
| 34 | [Top-Hat Transformation](Experiment-34-top-hat-transformation/) | Extract bright regions using top-hat transformation. |
| 35 | [Black-Hat Transformation](Experiment-35-black-hat-transformation/) | Extract dark regions using black-hat transformation. |
| 36 | [Watch Recognition](Experiment-36-watch-recognition/) | Recognise a watch face using circle detection. |
| 37 | [Reverse Video Playback](Experiment-37-reverse-video-playback/) | Create a video whose frames play in reverse order. |
| 38 | [Face Detection](Experiment-38-face-detection/) | Detect faces using OpenCV Haar cascades. |
| 39 | [Vehicle Detection in Video](Experiment-39-vehicle-detection-in-video/) | Detect moving vehicle regions in a video. |
| 40 | [Draw Rectangle and Extract Object](Experiment-40-draw-rectangle-and-extract-object/) | Draw a rectangular region and extract the selected object. |

## Notes

Experiments 7 and the optional webcam mode of Experiment 38 need a webcam and
a desktop environment. All other experiments save results directly inside
their own `output` folders.

## License

This repository is released under the [MIT License](LICENSE).
