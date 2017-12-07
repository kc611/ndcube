# -*- coding: utf-8 -*-

import abc

import astropy.units as u
import astropy.nddata
from astropy.utils.misc import InheritDocstrings
import numpy as np
import sunpy.map

from ndcube import cube_utils
from ndcube import wcs_util
from ndcube.mixins import NDCubeSlicingMixin, NDCubePlotMixin
from ndcube import DimensionPair


__all__ = ['NDCubeBase', 'NDCube', 'NDCubeOrdered']


class NDCubeMetaClass(abc.ABCMeta, InheritDocstrings):
    """
    A metaclass that combines `abc.ABCMeta` and `~astropy.utils.misc.InheritDocstrings`.
    """


class NDCubeBase(astropy.nddata.NDData, metaclass=NDCubeMetaClass):

    @abc.abstractmethod
    def pixel_to_world(self, quantity_axis_list, origin=0):
        """
        Convert a pixel coordinate to a data (world) coordinate by using
        `~astropy.wcs.WCS.all_pix2world`.

        Parameters
        ----------
        quantity_axis_list : `list`
            A list of `~astropy.units.Quantity` with unit as pixel `pix`.

        origin : `int`.
            Origin of the top-left corner. i.e. count from 0 or 1.
            Normally, origin should be 0 when passing numpy indices, or 1 if
            passing values from FITS header or map attributes.
            See `~astropy.wcs.WCS.wcs_pix2world` for more information.
            Default is 0.

        Returns
        -------

        coord : `list`
            A list of arrays containing the output coordinates
            reverse of the wcs axis order.
        """

    @abc.abstractmethod
    def world_to_pixel(self, quantity_axis_list, origin=0):
        """
        Convert a world coordinate to a data (pixel) coordinate by using
        `~astropy.wcs.WCS.all_world2pix`.

        Parameters
        ----------
        quantity_axis_list : `list`
            A list of `~astropy.units.Quantity`.

        origin : `int`
            Origin of the top-left corner. i.e. count from 0 or 1.
            Normally, origin should be 0 when passing numpy indices, or 1 if
            passing values from FITS header or map attributes.
            See `~astropy.wcs.WCS.wcs_world2pix` for more information.
            Default is 0.

        Returns
        -------

        coord : `list`
            A list of arrays containing the output coordinates
            reverse of the wcs axis order.
        """

    @abc.abstractproperty
    def dimensions(self):
        """
        Returns a named tuple with two attributes: 'shape' gives the shape
        of the data dimensions; 'axis_types' gives the WCS axis type of each dimension,
        e.g. WAVE or HPLT-TAN for wavelength of helioprojected latitude.
        """

    @abc.abstractproperty
    def extra_coords(self):
        """
        """

    @abc.abstractmethod
    def crop_by_coords(self, lower_left_corner, dimension_widths):
        """
        Crops an NDCube given a lower left corner and widths of region of interest.

        Parameters
        ----------
        lower_left_corner: `list` of `astropy.units.Quantity`
            The lower left corner of the region of interest described in physical units
            consistent with the NDCube's wcs object.  The length of the iterable must
            equal the number of data dimensions and must have the same order as the data.

        dimension_widths: iterable of `astropy.units.Quantity`
            The width of the region of interest in each dimension in physical units
            consistent with the NDCube's wcs object.  The length of the iterable must
            equal the number of data dimensions and must have the same order as the data.

        Returns
        -------
        result: NDCube

        """


class NDCube(NDCubeSlicingMixin, NDCubePlotMixin, NDCubeBase):
    """
    Class representing N dimensional cubes.
    Extra arguments are passed on to `~astropy.nddata.NDData`.

    Parameters
    ----------
    data: `numpy.ndarray`
        The array holding the actual data in this object.

    wcs: `ndcube.wcs.wcs.WCS`
        The WCS object containing the axes information

    uncertainty : any type, optional
        Uncertainty in the dataset. Should have an attribute uncertainty_type
        that defines what kind of uncertainty is stored, for example "std"
        for standard deviation or "var" for variance. A metaclass defining
        such an interface is NDUncertainty - but isn’t mandatory. If the uncertainty
        has no such attribute the uncertainty is stored as UnknownUncertainty.
        Defaults to None.

    mask : any type, optional
        Mask for the dataset. Masks should follow the numpy convention
        that valid data points are marked by False and invalid ones with True.
        Defaults to None.

    meta : dict-like object, optional
        Additional meta information about the dataset. If no meta is provided
        an empty collections.OrderedDict is created. Default is None.

    unit : Unit-like or str, optional
        Unit for the dataset. Strings that can be converted to a Unit are allowed.
        Default is None.

    extra_coords : iterable of `tuple`, each with three entries
        (`str`, `int`, `astropy.units.quantity` or array-like)
        Gives the name, axis of data, and values of coordinates of a data axis not
        included in the WCS object.

    copy : bool, optional
        Indicates whether to save the arguments as copy. True copies every attribute
        before saving it while False tries to save every parameter as reference.
        Note however that it is not always possible to save the input as reference.
        Default is False.

    missing_axis : `list` of `bool`
        Designates which axes in wcs object do not have a corresponding axis is the data.
        True means axis is "missing", False means axis corresponds to a data axis.
        Ordering corresponds to the axis ordering in the WCS object, i.e. reverse of data.
        For example, say the data's y-axis corresponds to latitude and x-axis corresponds
        to wavelength.  In order the convert the y-axis to latitude the WCS must contain
        a "missing" longitude axis as longitude and latitude are not separable.

    """

    def __init__(self, data, wcs, uncertainty=None, mask=None, meta=None,
                 unit=None, extra_coords=None, copy=False, missing_axis=None, **kwargs):
        if missing_axis is None:
            self.missing_axis = [False]*wcs.naxis
        else:
            self.missing_axis = missing_axis
        if data.ndim is not wcs.naxis:
            count = 0
            for bool_ in self.missing_axis:
                if not bool_:
                    count += 1
            if count is not data.ndim:
                raise ValueError("The number of data dimensions and number of "
                                 "wcs non-missing axes do not match.")
        # Format extra coords.
        if extra_coords:
            self._extra_coords_wcs_axis = cube_utils._format_input_extra_coords_to_extra_coords_wcs_axis(
                extra_coords, self.missing_axis, data.shape)
        else:
            self._extra_coords_wcs_axis = None
        # Initialize NDCube.
        super().__init__(data, wcs=wcs, uncertainty=uncertainty, mask=mask,
                         meta=meta, unit=unit, copy=copy, **kwargs)

    def pixel_to_world(self, quantity_axis_list, origin=0):
        list_arg = []
        indexed_not_as_one = []
        result = []
        quantity_index = 0
        for i in range(len(self.missing_axis)):
            wcs_index = self.wcs.naxis-1-i
            # the cases where the wcs dimension was made 1 and the missing_axis is True
            if self.missing_axis[wcs_index]:
                list_arg.append(self.wcs.wcs.crpix[wcs_index]-1+origin)
            else:
                # else it is not the case where the dimension of wcs is 1.
                list_arg.append(quantity_axis_list[quantity_index].to(u.pix).value)
                quantity_index += 1
                # appending all the indexes to be returned in the answer
                indexed_not_as_one.append(wcs_index)
        list_arguments = list_arg[::-1]
        pixel_to_world = self.wcs.all_pix2world(*list_arguments, origin)
        # collecting all the needed answer in this list.
        for index in indexed_not_as_one[::-1]:
            result.append(u.Quantity(pixel_to_world[index], unit=self.wcs.wcs.cunit[index]))
        return result[::-1]

    def world_to_pixel(self, quantity_axis_list, origin=0):
        list_arg = []
        indexed_not_as_one = []
        result = []
        quantity_index = 0
        for i in range(len(self.missing_axis)):
            wcs_index = self.wcs.naxis-1-i
            # the cases where the wcs dimension was made 1 and the missing_axis is True
            if self.missing_axis[wcs_index]:
                list_arg.append(self.wcs.wcs.crval[wcs_index]+1-origin)
            else:
                # else it is not the case where the dimension of wcs is 1.
                list_arg.append(
                    quantity_axis_list[quantity_index].to(self.wcs.wcs.cunit[wcs_index]).value)
                quantity_index += 1
                # appending all the indexes to be returned in the answer
                indexed_not_as_one.append(wcs_index)
        list_arguments = list_arg[::-1]
        world_to_pixel = self.wcs.all_world2pix(*list_arguments, origin)
        # collecting all the needed answer in this list.
        for index in indexed_not_as_one[::-1]:
            result.append(u.Quantity(world_to_pixel[index], unit=u.pix))
        return result[::-1]

    def to_sunpy(self):
        wcs_axes = list(self.wcs.wcs.ctype)
        missing_axis = self.missing_axis
        if 'TIME' in wcs_axes and len(self.dimensions.shape) is 1:
            result = self.pixel_to_world([u.Quantity(self.data, unit=u.pix)])
        elif 'HPLT-TAN' in wcs_axes and 'HPLN-TAN' in wcs_axes \
                and len(self.dimensions.shape) is 2:
            if not missing_axis[wcs_axes.index("HPLT-TAN")] \
                    and not missing_axis[wcs_axes.index("HPLN-TAN")]:
                result = sunpy.map.Map(self.data, self.meta)
        else:
            raise NotImplementedError("Object type not Implemented")
        return result

    @property
    def dimensions(self):
        ctype = list(self.wcs.wcs.ctype)
        axes_ctype = []
        for i, axis in enumerate(self.missing_axis):
            if not axis:
                axes_ctype.append(ctype[i])
        shape = u.Quantity(self.data.shape, unit=u.pix)
        return DimensionPair(shape=shape, axis_types=axes_ctype[::-1])

    def crop_by_coords(self, lower_left_corner, dimension_widths):
        n_dim = len(self.dimensions.shape)
        if len(lower_left_corner) != len(dimension_widths) != n_dim:
            raise ValueError("lower_left_corner and dimension_widths must have "
                             "same number of elements as number of data dimensions.")
        # Convert coords of lower left corner to pixel units.
        lower_pixels = self.world_to_pixel(lower_left_corner)
        upper_pixels = self.world_to_pixel([lower_left_corner[i]+dimension_widths[i]
                                            for i in range(n_dim)])
        # Round pixel values to nearest integer.
        lower_pixels = [int(np.rint(l.value)) for l in lower_pixels]
        upper_pixels = [int(np.rint(u.value)) for u in upper_pixels]
        slic = tuple([slice(lower_pixels[i], upper_pixels[i]) for i in range(n_dim)])
        return self[slic]

    @property
    def extra_coords(self):
        if not self._extra_coords_wcs_axis:
            result = None
        else:
            result = {}
            for key in list(self._extra_coords_wcs_axis.keys()):
                result[key] = {
                    "axis": cube_utils.wcs_axis_to_data_axis(
                        self._extra_coords_wcs_axis[key]["wcs axis"],
                        self.missing_axis),
                    "value": self._extra_coords_wcs_axis[key]["value"]}
        return result

    def __repr__(self):
        return (
            """Sunpy NDCube
---------------------
{wcs}
---------------------
Length of NDCube: {lengthNDCube}
Axis Types of NDCube: {axis_type}
""".format(wcs=self.wcs.__repr__(), lengthNDCube=self.dimensions[0], axis_type=self.dimensions[1]))


class NDCubeOrdered(NDCube):
    """
    Class representing N dimensional cubes with oriented WCS.
    Extra arguments are passed on to NDData's init.
    The order is TIME, SPECTRAL, SOLAR-x, SOLAR-Y and any other dimension.
    For example, in an x, y, t cube the order would be (t,x,y) and in a
    lambda, t, y cube the order will be (t, lambda, y).
    Extra arguments are passed on to NDData's init.

    Parameters
    ----------
    data: `numpy.ndarray`
        The array holding the actual data in this object.

    wcs: `ndcube.wcs.wcs.WCS`
        The WCS object containing the axes' information. The axes'
        priorities are time, spectral, celestial. This means that if
        present, each of these axis will take precedence over the others.

    uncertainty : any type, optional
        Uncertainty in the dataset. Should have an attribute uncertainty_type
        that defines what kind of uncertainty is stored, for example "std"
        for standard deviation or "var" for variance. A metaclass defining
        such an interface is NDUncertainty - but isn’t mandatory. If the uncertainty
        has no such attribute the uncertainty is stored as UnknownUncertainty.
        Defaults to None.

    mask : any type, optional
        Mask for the dataset. Masks should follow the numpy convention
        that valid data points are marked by False and invalid ones with True.
        Defaults to None.

    meta : dict-like object, optional
        Additional meta information about the dataset. If no meta is provided
        an empty collections.OrderedDict is created. Default is None.

    unit : Unit-like or str, optional
        Unit for the dataset. Strings that can be converted to a Unit are allowed.
        Default is None.

    copy : bool, optional
        Indicates whether to save the arguments as copy. True copies every attribute
        before saving it while False tries to save every parameter as reference.
        Note however that it is not always possible to save the input as reference.
        Default is False.
    """

    def __init__(self, data, wcs, uncertainty=None, mask=None, meta=None,
                 unit=None, copy=False, missing_axis=None, **kwargs):
        axtypes = list(wcs.wcs.ctype)
        array_order = cube_utils.select_order(axtypes)
        result_data = data.transpose(array_order)
        wcs_order = np.array(array_order)[::-1]
        result_wcs = wcs_util.reindex_wcs(wcs, wcs_order)

        super().__init__(result_data, result_wcs, uncertainty=uncertainty,
                         mask=mask, meta=meta, unit=unit, copy=copy,
                         missing_axis=missing_axis, **kwargs)
