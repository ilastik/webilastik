# Ilastik overlay

This project implements a web version of [ilastik](https://www.ilastik.org/), in particular of its [Pixel Classification Workflow](https://www.ilastik.org/documentation/pixelclassification/pixelclassification)

## Coordinate Space conventions  and Terminology

### Voxel Space

The Voxel Space are the coordinates of a voxel as defined in the image format where it is stored. For example, the voxel space coordinates of the top-left corner of a `.png` image is `{x: 0, y: 0}`, with `y` pointing down and `x` pointing to the right. In voxel space, the difference between the coordinates of adjacent voxels on the same line is something like `{x: 1, y: 0}`

One can think of the `Voxel Space` as the "Object Space" of an image file in 3D modeling terms; It has coordinates that only make sense inside a file format, and those coordinates must eventually be mapped to a common representation - the `World Space`. This mapping makes sure that whatever "top", "left", "bottom", etc in the conventions of the file format that defines the `Voxel Space` will correspond to the conventions of the `World Space`.

### World Space

The `World Space` is a common coordinate system where voxels from any image file format can be represented after adequate conversion. It is a right-handed coordinate system which gives the following meanings to its axes:
- `+x` is right
- `+y` is up
- `-z` is forwards

When zoomed in on the voxels, they are represented as macroscopic boxes rather than points, which mean they have a shape. Such shape is `1x1x1` for isotropic data, but that can be adjusted via the matrix produced by `IViewportDriver.getVoxelToWorldMatrix()`. When brushing over a dataset where the voxels are, say, wider than they are tall, and also very deep, they could have a `World Space` shape like `{x: 1, y: 2.5, z: 6}`

Sticking to the previous example of looking at a `.png` image, a sensible implementation of `IviewportDriver.getVoxelToWorldMatrix()` matrix might return a matrix that looks like this:

```
1  0  0  0 // +x in .png points to the right, so leave it untouched
0 -1  0  0 // +y in .png points down, so flip it
0  0 -1  0 // there is no depth in .png, but this would make it stack "forwards" (i.e.,  layer z + 1 is "behind" layer z0)
0  0  0  1
```

### View Space

These are coordinates with the origin at the camera's position. It is assumed throughout the code that:
 - `+x` points to the right;
 - `+y` points up.
 - the camera looks down the `-z` axis;


## Concepts

### Brush Stroke

One of the main features of ilastik is doing pixel classification, that is, determine to which class any pixel in an image belongs based on some samples provided by the user. These samples are provided by means of brush strokes; the user draws on top of t heir image with MSPaint-like brushing tools, marking pixels in the images with colors that map to arbitrary, user-defined classes (like, for example, "foreground" and "backgrond").

Instances of the `BrushStroke` class represent a collection of voxel coordinates, which are the voxels marked using the brushing tool.

### Overlay

The overlay is a transparent HTML element that tracks another underlying HTML element, and allows the user to brush over any web viewer.

### Viewport

The overlay can be split into multiple "Viewports", which behave as different views on the same data. A limitation of this implementation (and somewhat of webgl itself) is that the viewports must be geometrically contained within the main overlay.
