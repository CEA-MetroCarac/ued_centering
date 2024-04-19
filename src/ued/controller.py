""" Controller module for the UED centering app """
from io import StringIO
import socket
import numpy as np
import panel as pn
from bokeh.io import curdoc
from matplotlib.ticker import FuncFormatter

class Controller:
    """ Controller class for the UED centering app """

    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.callback_id = None

    def get_img(self):
        """ Get the original image from the model """
        return self.model.img

    def get_img_src(self):
        """ Get the original image source from the model """
        return self.model.img_src

    def get_img_bkg(self):
        """ Get the background image from the model """
        return self.model.img_bkg

    def get_pol_imgs(self):
        """ Get the polar images from the model """
        return (
            self.model.img_pol,
            self.model.img_pol_masked,
            self.model.img_pol_bkg,
        )

    def get_profiles(self):
        """ Get the profiles from the model """
        return self.model.prof, self.model.prof_bkg, self.model.prof_flattened

    def get_dot_src(self):
        """ Get the red dot source from the model """
        return self.model.dot_src

    def get_mask_min(self):
        """ Get the mask min value from the model """
        return self.model.mask_min

    def get_vmax(self):
        """ Get the vmax value from the model """
        return self.model.vmax

    def error(self, message='', visible=True):
        """ Show an error message in the view """
        self.view.alert.object = message
        self.view.alert.visible = visible

    def update_pol_imgs(self, img, img_masked, img_bkg_masked, center):
        """
        Update the polar images in the model with the given images and center
        """
        self.model.set_pol_imgs(img, img_masked, img_bkg_masked, center)

    def dot_moved(self,
                  attr, old, new):  # pylint: disable=W0613(unused-argument)
        """Update the polar plot when the red dot is moved"""
        # If a callback is already scheduled, remove it
        if self.callback_id is not None:
            curdoc().remove_timeout_callback(self.callback_id)

        # Schedule a new callback with 200 ms delay
        self.callback_id = curdoc().add_timeout_callback(
            self.view.plot_polar, 200)

    def toggle_mask(self):
        """
        Show the effect of the mask on the image depending on the checkbox state
        """

        img = self.model.img
        img_src = self.model.img_src

        if self.view.mask_chkbox.value:
            img_src.data.update(image=[img], dh=[img.shape[0]],
                                dw=[img.shape[1]])
        else:
            # Get the mask
            mask = self.model.mask
            # Update the masked image source
            masked_img = np.where(mask, img, np.nan) # TODO should be in model
            img_src.data.update(image=[masked_img], dh=[img.shape[0]],
                                dw=[img.shape[1]])

    def export_profiles(self):
        """ Export the axial sum profile as a csv file """
        view = self.view  # for shorter code
        model = self.model

        x = np.arange(model.prof.shape[0])
        factor = view.pixel_size_input.value
        data = np.column_stack(
            (x * factor, model.prof, model.prof_bkg, model.prof_flattened)
        )

        # save to a StringIO object
        csv_output = StringIO()
        np.savetxt(
            csv_output,
            data,
            fmt="%f",
            delimiter=",",
            header="X,Y,Y_bkg,Y_flattened",
            comments="",
        )

        # Reset the pointer to the beginning of the StringIO object
        csv_output.seek(0)

        view.download_csv.filename = "profiles.csv"
        view.download_csv.file = csv_output

        # Trigger the download
        view.download_csv._clicks += 1

    def update_colormap(self, _):
        """Update the colormap of all the plots"""
        view = self.view  # for shorter code

        view.mpl_cmap = view.cmap[view.cmap_choice.value]

        # Update colormap of 1st plot (bokeh plot)
        view.color_mapper.update(palette=view.cmap_choice.value)

        # Update colormap of 2nd plot (matplotlib plot)
        view.polar_imshow.set_cmap(view.mpl_cmap)
        view.polar_plot.param.trigger("object")

    def toggle_lines_and_circles(self):
        """Show or hide the lines & circles of interest on the polar plot"""
        view = self.view  # for shorter code
        visible = not view.hide_x_val.value

        for i in range(2, len(view.plot.renderers)):
            view.plot.renderers[i].visible = visible
        for line in view.ax.lines:
            line.set_visible(visible)

        # Update the Matplotlib pane
        view.polar_plot.param.trigger("object")

    def apply_x_offset(self):
        """Apply the x-offset to the polar plot by setting the x-axis limits"""
        view = self.view  # for shorter code

        # Set the x-axis limits & Update the Matplotlib pane
        view.ax.set_xlim([view.x_offset_slider.value, None])
        view.polar_plot.param.trigger("object")

    def apply_px_size(self, init=False):
        """Apply the pixel size to the polar plot by setting the x-axis ticks"""
        view = self.view  # for shorter code

        if init:
            view.pixel_size_input.value = self.model.pixel_size_init
            return

        factor = view.pixel_size_input.value  # Get the pixel size factor
        x_ticks = view.ax.get_xticks()  # Get current x and y ticks

        # TODO Fix warning, this adds a wider blank border to the plot
        # view.ax.set_xticks(x_ticks)

        # Apply the factor to the ticks
        x_ticks = (x_ticks * factor).astype(int)
        def format_func(value, tick_number):
            return "%.2f" % (value * factor)

        # Set new tick labels with 2 decimal places
        view.ax.xaxis.set_major_formatter(FuncFormatter(format_func))
        
        # Update lines and circles position according to the new pixel size
        view.draw_lines_circles()

        # Update the Matplotlib pane
        view.polar_plot.param.trigger("object")

    def update_brightness(self):
        """ Setting vmax for all the plots"""
        view = self.view  # for shorter code
        vmin, vmax = self.model.compute_brightness(view.brightness_slider.value)
        view.update_color_mapper(vmin, vmax)

        if view.polar_imshow is not None:
            view.polar_imshow.set_clim(vmax=vmax)
            view.polar_plot.param.trigger("object")

    def center(self):
        """ Center the red dot on the image """
        self.view.progress.visible = True
        self.view.dot.visible = True

        img = self.model.img
        center, _ = self.model.center_eval(img, self.model.mask)
        self.model.dot_src.data.update(x=[center[0]], y=[center[1]])

        self.view.progress.visible = False

    def update_mask(self, quantile_min=0.10, quantile_max=0.95):
        """ Update the mask based on the quantile values """
        model = self.model
        img = model.img

        # Set red dot position, display coordinates and update the image
        model.mask, model.mask_min = model.mask_eval(img, quantile_min,
                                                     quantile_max)

        # Plot the original img or the masked img depending on the checkbox
        self.toggle_mask()

    def start(self, _=None, quantile_min=0.10, quantile_max=0.95):
        """
        Load the image and do the mask evaluation
        """
        model = self.model  # for shorter code
        view = self.view
        view.progress.visible = True

        # Load the image
        file_path = view.file_browser.get_selection_path()

        try:
            # TODO reset the model
            # from model import Model
            # self.model = Model(self)
            # model = self.model
            model.load_img(file_path)
        except ValueError:
            self.view.progress.visible = False
            return

        # Update the brightness
        self.update_brightness()
        self.update_mask(quantile_min, quantile_max)

        view.progress.visible = False

    def run(self):
        """Run the app"""

        # Getting a free port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', 0))  # Bind to a port that is free
        port = sock.getsockname()[1]
        sock.close()

        # Serve the app
        pn.serve(self.view.layout(), port=port)
