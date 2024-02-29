""" Model module for the UED centering application """
import numpy as np
from bokeh.models import ColumnDataSource

from tifffile import imread
from reader_dm import DM3

from skimage.transform import warp_polar
from scipy.optimize import curve_fit
from scipy.ndimage import binary_erosion, binary_closing, center_of_mass

def fun(x, a, b, xc, yc):  # pylint:disable=C0103
    """ 2D-map analytical function used for the fit """
    return a * ((x[0] - xc) ** 2 + (x[1] - yc) ** 2) ** b

def jac(x, a, b, xc, yc):  # pylint:disable=C0103
    """ 2D-map analytical Jacobian function used for the fit """
    squared_distance = (x[0] - xc) ** 2 + (x[1] - yc) ** 2

    df_da = squared_distance ** b
    df_db = a * df_da * np.log(squared_distance)
    df_dxc = -2 * a * b * (x[0] - xc) * (squared_distance) ** (b - 1)
    df_dyc = -2 * a * b * (x[1] - yc) * (squared_distance) ** (b - 1)

    return np.array([df_da, df_db, df_dxc, df_dyc]).T

class Model:
    """ Model class for the UED centering application """
    def __init__(self, controller=None):
        self.controller = controller
        self.img = None
        self.img_bkg = None
        self.img_pol = None
        self.img_pol_masked = None
        self.img_pol_bkg = None
        self.prfl = None
        self.prfl_bkg = None
        self.prfl_flattened = None
        self.mask = None
        self.mask_min = None
        self.vmin = None
        self.vmax = None
        self.img_src = ColumnDataSource(data={"image": [np.zeros((1, 1))],
                                                   "dw": [10],
                                                   "dh": [10]})
        self.dot_src = ColumnDataSource(data={"x":[0],
                                                 "y":[0],
                                                 "listener_added":[False]}) 

    def load_img(self, img):
        """Load the image from the selected file"""
        # get extension
        ext = img.suffix

        if ext == ".dm3" or ext == ".dm4":
            dm = DM3(img)
            loaded_image = dm.imagedata.astype(float)
            self.pixel_size_init = dm.pxsize[0]
        elif ext == ".tif":
            loaded_image = imread(img).astype(float)
        else:
            self.controller.error("Unsupported file format. Please use .dm(3-4) or .tif files.")
            raise ValueError("Unsupported file format. Please use .dm(3-4) or .tif files.")

        self.controller.error(visible=False)
        self.img = loaded_image

    def compute_brightness(self, brightness):
        """ Calculate vmin and vmax based on the image and brightness """
        self.vmax = (0.01 / brightness) * np.max(self.img)
        self.vmin = np.min(self.img)
        return self.vmin, self.vmax

    def bkg_estimation_2d(self, popt, step):
        """
        Calculate the 2D background estimation
        """
        coords = np.mgrid[0:self.img.shape[0], 0:self.img.shape[1]]
        self.img_bkg = fun(coords, *popt) * pow(step, -2*popt[1])

    def mask_eval(self, img, quantile_min=0.05, quantile_max=0.95):
        """
        Mask evaluation based on quantile imgay 'img' partition

        Parameters
        ----------
        img: numpy.ndarray()
            Array to handle
        quantile_min: float, optional
            Minimum quantile value associated to the mask creation
        quantile_max: float, optional
            Maximum quantile value associated to the mask creation

        Returns
        -------
        mask: numpy.ndarray((img.shape), dtype=bool)
            Mask associated to the array given in input
        """
        mask_min = (img > np.nanquantile(img, quantile_min))
        mask = mask_min * (img < np.nanquantile(img, quantile_max))
        mask = binary_closing(mask)
        return mask, ~mask_min

    def center_eval(self, img, mask=None, curve_fit_fun=fun, curve_fit_jac=jac):
        """
        Return center position estimated from a 2D-map curve fitting

        Parameters
        ----------
        img: numpy.ndarray((m, n))
            Array to handle
        mask: numpy.ndarray((m, n), dtype=bool), optional
            Mask associated to the array to 'eliminate' inconsistant value
            during the fit.
        curve_fit_fun: function, optional
            Function used as 2D-map model during the fit
        curve_fit_jac: function, optional
            Associated Jacobian function associated to 'curve_fit_fun'

        Returns
        -------
        center: tuple of 2 floats
            Calculated center position returned by the 2D-map fit
        masked_img: numpy.ndarray((m//step, n//step))
            Masked array resulting from downsampling, used for center detection
        """
        if mask is None:
            mask = np.ones_like(img, dtype=bool)

        # image size reduction
        step = max(1, min(self.img.shape) // 512)
        img = img[::step, ::step]
        mask = mask[::step, ::step]

        # mask erosion enlarged to remove transition area around the beam-block
        mask = binary_erosion(mask, iterations=5)
        masked_img = img.copy().astype(float)
        masked_img[~mask] = np.nan  # pylint:disable=E1130

        # 2D map fitting
        yc_0, xc_0 = center_of_mass(img, labels=mask, index=0)
        guess0 = [np.max(img[mask]), -1, xc_0, yc_0]
        bounds = ([0, -np.inf, 0, 0], [np.inf, 0, img.shape[1], img.shape[0]])

        coords = np.mgrid[0:img.shape[0], 0:img.shape[1]]
        coords = [coords[0][mask], coords[1][mask]]
        popt = curve_fit(curve_fit_fun, coords, img[mask], p0=guess0,
                         jac=curve_fit_jac, bounds=bounds)[0]
        
        # parameters in the full real space
        popt = (popt[0], popt[1], popt[2] * step, popt[3] * step)
        center = (popt[3], popt[2])

        # Additonal step to calculate the 2D background estimation
        self.bkg_estimation_2d(popt, step)

        return center, masked_img
    
    def set_pol_imgs(self, img, img_masked, img_bkg_masked, center):
        """
        Set the polar images and their profiles in the model
        """
        # We keep img_pol to plot the polar image without nan values
        img_pol = warp_polar(img, center=center, cval=0)
        img_pol_masked = warp_polar(img_masked, center=center, cval=np.nan)
        img_pol_bkg = warp_polar(img_bkg_masked, center=center, cval=np.nan)

        self.img_pol = img_pol
        self.img_pol_masked = img_pol_masked
        self.img_pol_bkg = img_pol_bkg

        self.prfl = np.nansum(img_pol_masked, axis=0)
        self.prfl_bkg = np.nansum(img_pol_bkg, axis=0)
        self.prfl_flattened = np.clip(self.prfl-self.prfl_bkg,0,None)