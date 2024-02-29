
<!-- <p align="center">
  <img src="https://raw.githubusercontent.com/CEA-MetroCarac/ued_centering/master/images/logo.png" alt="logo">
</p> -->

**UED Centering** is a web app for Ultrafast Electron Diffraction (UED) image analysis. It can automatically find the center of the diffraction pattern and display the polar representation of the data. The app also allows the user to manually adjust the center and to export the data. The app runs a [Panel](https://panel.holoviz.org/) server.

![app](https://raw.githubusercontent.com/CEA-MetroCarac/ued_centering/master/images/app.png)

## Installation

To install and run the app, use the following commands:

```bash
git clone https://github.com/CEA-MetroCarac/ued_centering.git
cd ued_centering/src/ued
python ./app.py
```

## Requirements

- `panel`
- `numpy`
- `matplotlib`
- `scikit-image`
- `scipy`
- `pandas`
- `tifffile` (optional: only for loading TIFF files)

## Interface

Here is a brief description of the fields and components of the interface:

| Side | Component | Description |
| ---- | --------- | ----------- |
| Left | File selector | Choose the file you want to work with. |
| Left | Centering button | Start centering with the chosen file. |
| Left | Coordinates | Displays the coordinates of the center in real time. |
| Left | Export buttons | One for exporting the Plot to PNG, another for exporting the profiles data to TXT. |
| Left | Colormap selector | A multichoice field to select the colormap to apply on both plots. |
| Left | Points of interest field | A free text field to set points of interest to show as lines and circles depending on the plot (polar or not). Each point is separated by a comma (e.g., 5,10,15). To update, you can click outside of this field or just press enter. |
| Left | Points of interest checkbox | Show or hide these points of interest. |
| Left | Extra profiles checkbox | Show or hide extra profiles used during auto center calculations. |
| Left | X offset slider | Can be used to zoom on the X axis. |
| Left | Pixel size factor | Automatically set based on dm file metadata (can be modified if not detected, for example with tif files). |
| Right | Brightness slider | Adjust the brightness of the two plots. |
| Right | Quantile slider | Set the minimum and maximum threshold used in auto center calculation. |
| Right | Show mask checkbox | Use this when you are finished setting your quantile and the mask looks good to you. |
| Right | Two plots | One for the original image with the center, and the other for the polar representation for further analysis. |

<!-- Authors information -->
