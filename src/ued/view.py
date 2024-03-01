""" View module for the UED Centering App """
import panel as pn
import numpy as np

import matplotlib.pyplot as plt

from bokeh import events
from bokeh.plotting import figure
from bokeh.models import (Div, CustomJS, Button,
                          LinearColorMapper,
                          DataRange1d,
                          WheelZoomTool,
                          HoverTool)

from file_browser import FileBrowser


class View:
    """ View class for the UED Centering App """

    def __init__(self, controller):
        self.controller = controller
        self.lines = []
        self.original_ylim = None
        self.title = pn.pane.Markdown(
            "<div style='text-align: center;'><h1>UED Centering App</h1></div>",
            width=500)

        # In case of error, display an alert
        self.alert = pn.pane.Alert('', alert_type='danger', visible=False)

        # Create a FileBrowser widget
        self.file_browser = FileBrowser()
        self.file_browser_layout = self.file_browser.layout()
        self.file_browser.df_widget.param.watch(
                self.controller.start, "selection")

        # Create centering button
        self.center_btn = Button(
            label="Centering", button_type="primary")
        self.center_btn.on_click(controller.center)

        # Getting all ColumnDataSources from model via controller
        img_src = controller.get_img_src()
        dot_src = controller.get_dot_src()

        # Create a new plot for the src image
        self.plot = figure(x_range=DataRange1d(range_padding=0),
                           y_range=DataRange1d(range_padding=0),
                           width=500,
                           height=500)
        self.plot.toolbar.active_scroll = self.plot.select_one(WheelZoomTool)
        # Limit the range of the plot to just the data
        self.plot.x_range.bounds = self.plot.y_range.bounds = "auto"

        self.fig, self.ax = plt.subplots(figsize=(6, 2), tight_layout=True)
        self.ax2 = self.ax.twinx()
        self.ax2.get_yaxis().set_visible(False)

        # TODO add matplotlib interactive=True when fixed
        # https://github.com/bokeh/ipywidgets_bokeh/issues/41
        self.polar_plot = pn.pane.Matplotlib(self.fig, tight=True)
        self.polar_imshow = None

        # Define your color mapper, with the range of colors you want to use
        self.color_mapper = LinearColorMapper(palette="Inferno256",
                                              low=0, high=1,
                                              nan_color=(0, 0, 0, 0))

        # Render Image and Red dot
        img_glyph = self.plot.image(x=0,
                                    y=0,
                                    dw="dw",
                                    dh="dh",
                                    source=img_src,
                                    color_mapper=self.color_mapper)

        self.dot = self.plot.dot(x="x",
                                 y="y",
                                 size=40,
                                 color="red",
                                 source=dot_src,
                                 visible=False)

        # Add a hover tool to display x,y and pixel value
        hover = HoverTool(tooltips=[
            ("x", "$x"),
            ("y", "$y"),
            ("value", "@image"),
        ], renderers=[img_glyph])
        self.plot.add_tools(hover)

        # Div to display the coordinates of the red dot
        self.coordinates_div = Div()

        # update red dot position when mouse clic
        self.plot.js_on_event(
            events.Tap,
            CustomJS(
                args={
                    "source": dot_src,
                    "div": self.coordinates_div,
                    "img": img_src
                },
                code="""
let x = img.data.dh[0]
let y = img.data.dw[0]

if (cb_obj.x >= 0 && cb_obj.x <= x && cb_obj.y >= 0 && cb_obj.y <= y) {
        source.data = {'x': [cb_obj.x], 'y': [cb_obj.y]};
    div.text = "Coordinates: " + cb_obj.x.toFixed(0) + ", " + cb_obj.y.toFixed(0);
}
                """))

        self.btn_callback = CustomJS(
            args={"source": dot_src,
                  "div": self.coordinates_div
                  },
            code="""
let mousePos = { x: 0, y: 0 };
let inRightThird = false; // flag to check if mouse is in the right third of the screen

// Listen for mousemove events
window.addEventListener('mousemove', function(event) {
    // Update mouse position
    mousePos.x = event.clientX;
    mousePos.y = event.clientY;
    inRightThird = mousePos.x > window.innerWidth / 3;
});

// Listen arrow keys events when in right third of the screen
if (!(source.data['listener_added'][0])) {
    window.addEventListener('keydown', function(event) {
        if (inRightThird) {
            // Check if the key pressed was an arrow key
            if (event.key === 'ArrowUp') {
                source.data = {'x': [source.data['x'][0]], 'y': [source.data['y'][0] + 1], 'listener_added': [true]};
            } else if (event.key === 'ArrowDown') {
                source.data = {'x': [source.data['x'][0]], 'y': [source.data['y'][0] - 1], 'listener_added': [true]};
            } else if (event.key === 'ArrowLeft') {
                source.data = {'x': [source.data['x'][0] - 1], 'y': [source.data['y'][0]], 'listener_added': [true]};
            } else if (event.key === 'ArrowRight') {
                source.data = {'x': [source.data['x'][0] + 1], 'y': [source.data['y'][0]], 'listener_added': [true]};
            }
            div.text = "Coordinates: " + source.data['x'][0].toFixed(0) + ", " + source.data['y'][0].toFixed(0);
        }
    }); 
}  
""")

        self.center_btn.js_on_click(self.btn_callback)

        dot_src.on_change("data", controller.dot_moved)

        # Used to specify vertical lines of interest on the polar plot
        # TODO use Multichoice when issue #5047 is completed
        # https://github.com/holoviz/panel/issues/5047
        self.x_values = pn.widgets.TextInput(
            name="X Points of interest (confirm with enter)",
            value="8.2,10.7")
        self.x_values.param.watch(
            lambda event: self.draw_lines_circles(), "value")

        self.x_offset_slider = pn.widgets.IntSlider(
            name="X Offset",
            start=0,
            end=250,
            value=110,
            step=5)
        self.x_offset_slider.param.watch(
            lambda event: controller.apply_x_offset(), "value")

        self.pixel_size_input = pn.widgets.FloatInput(
            name="Pixel Size Factor",
            start=0,
            end=100,
            value=1,
            format='0.000',
            width=100)
        self.pixel_size_input.param.watch(
            lambda event: controller.apply_px_size(), "value")

        self.export_csv = Button(
            label="Export profiles.csv", button_type="primary")
        self.export_csv.on_click(controller.export_profiles)
        self.download_csv = pn.widgets.FileDownload(visible=False)

        self.cmap_choice = pn.widgets.Select(
            options=['Inferno256', 'Greys256', 'Cividis256', 'Viridis256',
                     'Plasma256'],
            name='Colormap:')
        self.cmap_choice.param.watch(controller.update_colormap, "value")

        self.cmap = {"Inferno256": "inferno", "Greys256": "gray",
                     "Cividis256": "cividis", "Viridis256": "viridis",
                     "Plasma256": "plasma"}
        self.mpl_cmap = self.cmap[self.cmap_choice.value]

        # add checkbox
        self.hide_x_val = pn.widgets.Checkbox(name='Hide X values', value=False)
        self.hide_x_val.param.watch(
            lambda event: controller.toggle_lines_and_circles(), "value")

        self.show_extra_profiles = pn.widgets.Checkbox(
            name='Show Original + Bkg profiles', value=False)
        self.show_extra_profiles.param.watch(
            lambda event: self.show_all_profiles(), "value")

        self.quantile_slider = pn.widgets.RangeSlider(
            name="Quantile",
            start=0,
            end=1,
            value=(0.10, 0.95),
            step=0.05)
        self.quantile_slider.param.watch(lambda event: controller.update_mask(
            quantile_min=self.quantile_slider.value[0],
            quantile_max=self.quantile_slider.value[1]),
                                         "value")

        self.progress = pn.indicators.Progress(name='Progress', width=200,
                                               visible=False)

        self.brightness_slider = pn.widgets.FloatSlider(
            name="Brightness",
            start=0,
            end=1,
            value=0.1,
            step=0.01)
        self.brightness_slider.param.watch(
            lambda event: controller.update_brightness(), "value")

        self.mask_chkbox = pn.widgets.Checkbox(name='Hide Mask', value=False)
        self.mask_chkbox.param.watch(
            lambda event: controller.toggle_mask(), "value")

    def render_polar_image(self):
        """
        Render the polar image while applying effects such as cropping
        the x-axis and setting the pixel size.
        """
        # Get the polar image from the model
        img_pol = self.controller.get_pol_imgs()[0]
        self.draw_lines_circles()
        self.polar_imshow = self.ax.imshow(img_pol,
                                           vmin=0,
                                           vmax=self.controller.get_vmax(),
                                           cmap=self.mpl_cmap)
        self.ax.set_aspect('auto')
        self.ax.margins(x=0, y=0)

    def render_profiles(self):
        """
        Render the profiles.
        """
        # Get the profiles from the model
        prof, prof_bkg, prof_flattened = self.controller.get_profiles()

        # alt x-axis to plot the profiles so they match the polar image width
        # as they were calculated on downsampled image
        x = np.linspace(0, self.controller.get_pol_imgs()[0].shape[1], len(prof))

        # Then plot with the new x-axis
        self.ax2.plot(x, prof, visible=False)
        self.ax2.plot(x, prof_bkg, color='b', visible=False)
        self.ax2.plot(x, prof_flattened, color='green', visible=False)

    def show_all_profiles(self):
        """
        Show or hide the extra profiles (axial sum & bkg) on the polar plot
        """
        # Get flate
        _, _, prof_flattened = self.controller.get_profiles()

        # Scale the y-axis to the profile if the extra profiles are hidden
        if not self.show_extra_profiles.value:
            self.original_ylim = self.ax2.get_ylim()
            self.ax2.set_ylim([
                min(prof_flattened), max(prof_flattened)])
        else:
            self.ax2.set_ylim(self.original_ylim)

        # Set the visibility of the extra profiles
        for line in self.ax2.lines[:2]:
            line.set_visible(self.show_extra_profiles.value)

        # Show the flattened profile & update the Matplotlib pane
        self.ax2.lines[2].set_visible(True)
        self.polar_plot.param.trigger("object")

    def plot_polar(self):
        """
        Plots the polar representation of the image with the axial sum, the
        background estimation and the flattened profile. This function is called
        whenever the red dot is moved or the x_values are updated.
        """
        img = self.controller.get_img()

        # Show the progress bar
        self.progress.visible = True

        # Get the new coordinates of the red dot
        dot_src = self.controller.get_dot_src()
        x = dot_src.data["x"][0]
        y = dot_src.data["y"][0]
        self.coordinates_div.text = f"Coordinates: {x:.0f}, {y:.0f}"

        # Auto set pixel_size if its value has been defined when loading img
        self.controller.apply_px_size(init=True)

        # Create the polar warp of the image
        mask_min_only = self.controller.get_mask_min()

        # Copy of the image and the background to apply the mask
        img_masked = img.copy()
        img_bkg_masked = self.controller.get_img_bkg().copy()

        img_masked[mask_min_only] = np.nan  # TODO this shouldn't be in the view
        img_bkg_masked[mask_min_only] = np.nan

        # Set the polar images in the model
        self.controller.update_pol_imgs(img, img_masked, img_bkg_masked, (y, x))

        self.render_polar_image()
        self.render_profiles()
        self.controller.apply_x_offset() # Set the x-axis limits
        self.controller.apply_px_size() # Set the pixel size

        self.show_all_profiles()

        self.controller.callback_id = None
        self.progress.visible = False

    def draw_lines(self, x_values):
        """ Draw vertical lines of interest on the polar plot """
        # Remove the old lines
        for line in self.lines:
            line.remove()
        self.lines = []

        # Add the new lines
        for x_val in x_values:
            line = self.ax.axvline(x=x_val, color="r")
            self.lines.append(line)

    def draw_circles(self, x_values):
        """ Draw circles of interest on the polar plot """
        # save current number of renderers (image and red dot)
        len_renderers = len(self.plot.renderers)
        len_x_values = len(x_values)
        dot_src = self.controller.get_dot_src()
        center = (dot_src.data["x"][0], dot_src.data["y"][0])

        # First, draw circles
        for i, radius in enumerate(x_values):
            i += 2  # Ignore the image and the center dot
            # If there is already a circle
            if i < len_renderers:
                # update the circle with the new value
                self.plot.renderers[i].glyph.x = center[
                    0]  # pylint:disable=unsubscriptable-object
                self.plot.renderers[i].glyph.y = center[
                    1]  # pylint:disable=unsubscriptable-object
                self.plot.renderers[
                    i].glyph.radius = radius  #
                # pylint:disable=unsubscriptable-object
            else:
                # create a new circle
                self.plot.circle(
                    x=center[0],
                    y=center[1],
                    radius=radius,
                    color="red",
                    fill_alpha=0,
                    line_width=2,
                    source=dot_src)

        # Removing unwanted circles
        if len_renderers - 2 > len_x_values:
            for i in range(len_x_values, len_renderers - 2):
                self.plot.renderers.pop()  # pylint:disable=E1101

    def draw_lines_circles(self):
        """ Draw the lines and circles of interest on the plots """
        # Get the x-values from the text input
        x_values_string = self.x_values.value
        x_values_list = x_values_string.split(",")
        factor = self.pixel_size_input.value
        x_values = [float(x_val.strip()) / factor for x_val in x_values_list]

        # Add the circles and the vertical lines of interest
        self.draw_circles(x_values)
        self.draw_lines(x_values)

        # Update the Matplotlib pane
        self.polar_plot.param.trigger("object")

    def update_color_mapper(self, vmin, vmax):
        """ Update the color mapper with the given vmin and vmax """
        self.color_mapper.low = vmin
        self.color_mapper.high = vmax

    def layout(self):
        """ Return the app layout """
        self.left_panel = pn.Column(
            self.file_browser_layout,
            pn.Row(self.center_btn,
                   self.progress),
            pn.Spacer(height=20),
            pn.panel("Select image file and set the mask with the quantile \
                     slider, finally press Centering."),
            pn.Row(self.coordinates_div),
            pn.Spacer(height=20),
            pn.Row(self.export_csv, self.download_csv),
            self.cmap_choice,
            pn.Row(self.x_values, self.hide_x_val, self.show_extra_profiles),
            pn.Row(self.x_offset_slider, self.pixel_size_input),
            sizing_mode="fixed")

        self.center_panel = pn.Column(
            pn.Row(self.brightness_slider, self.quantile_slider,
                   self.mask_chkbox,
                   align='center'),
            pn.Row(self.plot, align='center'),
            self.polar_plot)

        return pn.Column(
            self.alert, self.title, pn.Row(self.left_panel, self.center_panel)
        )
