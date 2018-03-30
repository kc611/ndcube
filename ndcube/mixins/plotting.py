from warnings import warn
import copy

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import astropy.units as u
from sunpy.visualization.imageanimator import ImageAnimatorWCS, LineAnimator
import sunpy.visualization.wcsaxes_compat as wcsaxes_compat

from ndcube import utils
from ndcube.mixins.sequence_plotting import _prep_axes_kwargs, _derive_1D_coordinates_and_units, _determine_sequence_units, _make_1D_sequence_plot

__all__ = ['NDCubePlotMixin']

INVALID_UNIT_SET_MESSAGE = "Can only set unit for axis if corresponding coordinates in " + \
  "axes_coordinates are set to None, an astropy Quantity or the name of an extra coord that " + \
  "is an astropy Quantity."


class NDCubePlotMixin:
    """
    Add plotting functionality to a NDCube class.
    """

    def plot(self, axes=None, plot_axis_indices=None, axes_coordinates=None,
             axes_units=None, data_unit=None, **kwargs):
        """
        Plots an interactive visualization of this cube with a slider
        controlling the wavelength axis for data having dimensions greater than 2.
        Plots an x-y graph onto the current axes for 2D or 1D data.
        Keyword arguments are passed on to matplotlib.
        Parameters other than data and wcs are passed to ImageAnimatorWCS,
        which in turn passes them to imshow for data greater than 2D.

        Parameters
        ----------
        plot_axis_indices: `list`
            The two axes that make the image.
            Default=[-1,-2].  This implies cube instance -1 dimension
            will be x-axis and -2 dimension will be y-axis.

        axes: `astropy.visualization.wcsaxes.core.WCSAxes` or None:
            The axes to plot onto. If None the current axes will be used.

        axes_unit: `list` of `astropy.units.Unit`

        data_unit: `astropy.unit.Unit`
            The data is changed to the unit given or the cube.unit if not given, for 1D plots.

        axes_coordinates: list of physical coordinates for array or None
            If None array indices will be used for all axes.
            If a list it should contain one element for each axis of the numpy array.
            For the image axes a [min, max] pair should be specified which will be
            passed to :func:`matplotlib.pyplot.imshow` as extent.
            For the slider axes a [min, max] pair can be specified or an array the
            same length as the axis which will provide all values for that slider.
            If None is specified for an axis then the array indices will be used
            for that axis.

        """
        # If old API is used, convert to new API.
        plot_axis_indices, axes_coordiantes, axes_units, data_unit, kwargs = _support_101_plot_API(
            plot_axis_indices, axes_coordinates, axes_units, data_unit, kwargs)
        # Check kwargs are in consistent formats and set default values if not done so by user.
        naxis = len(self.dimensions)
        plot_axis_indices, axes_coordinates, axes_units = _prep_axes_kwargs(
            naxis, plot_axis_indices, axes_coordinates, axes_units)
        if self.data.ndim is 1:
            plot = self._plot_1D_cube(axes, axes_coordinates,
                                      axes_units, data_unit, **kwargs)
        elif self.data.ndim is 2:
            plot = self._plot_2D_cube(axes, plot_axis_indices, axes_coordinates,
                                      axes_units, data_unit, **kwargs)
        else:
            plot = self._plot_3D_cube(plot_axis_indices=plot_axis_indices,
                                      axes_coordinates=axes_coordinates, axes_units=axes_units,
                                      **kwargs)
        return plot

    def _plot_1D_cube(self, axes=None, axes_coordinates=None, axes_units=None, data_unit=None,
                      **kwargs):
        """
        Plots a graph.
        Keyword arguments are passed on to matplotlib.

        Parameters
        ----------
        data_unit: `astropy.unit.Unit`
            The data is changed to the unit given or the cube.unit if not given.

        """
        # Derive x-axis coordinates and unit from inputs.
        x_axis_coordinates, unit_x_axis = _derive_1D_coordinates_and_units(axes_coordinates,
                                                                           axes_units)
        if x_axis_coordinates is None:
            # Default is to derive x coords and defaul xlabel from WCS object.
            xname = self.world_axis_physical_types[0]
            xdata = self.axis_world_coords()
        elif isinstance(x_axis_coordinates, str):
            # User has entered a str as x coords, get that extra coord.
            xname = x_axis_coordinates
            xdata = self.extra_coords[x_axis_coordinates]["value"]
        else:
            # Else user must have set the x-values manually.
            xname = ""
            xdata = x_axis_coordinates
        # If a unit has been set for the x-axis, try to convert x coords to that unit.
        if isinstance(xdata, u.Quantity):
            if unit_x_axis is None:
                unit_x_axis = xdata.unit
                xdata = xdata.value
            else:
                xdata = xdata.to(unit_x_axis).value
        else:
            if unit_x_axis is not None:
                raise TypeError(INVALID_UNIT_SET_MESSAGE)
        # Define default x axis label.
        default_xlabel = "{0} [{1}]".format(xname, unit_x_axis)
        # Combine data and uncertainty with mask.
        xdata = np.ma.masked_array(xdata, self.mask)
        # Derive y-axis coordinates, uncertainty and unit from the NDCube's data.
        if self.unit is None:
            if data_unit is not None:
                raise TypeError("Can only set y-axis unit if self.unit is set to a "
                                "compatible unit.")
            else:
                ydata = self.data
                if self.uncertainty is None:
                    yerror = None
                else:
                    yerror = self.uncertainty.array
        else:
            if data_unit is None:
                data_unit = self.unit
                ydata = self.data
                if self.uncertainty is None:
                    yerror = None
                else:
                    yerror = self.uncertainty.array
            else:
                ydata = (self.data * self.unit).to(data_unit).value
                if self.uncertainty is None:
                    yerror = None
                else:
                    yerror = (self.uncertainty.array * self.unit).to(data_unit).value
        # Combine data and uncertainty with mask.
        ydata = np.ma.masked_array(ydata, self.mask)
        if yerror is not None:
            yerror = np.ma.masked_array(yerror, self.mask)
        # Create plot
        fig, ax = _make_1D_sequence_plot(xdata, ydata, yerror, data_unit, default_xlabel, kwargs)
        return ax

    def _plot_2D_cube(self, axes=None, plot_axis_indices=None, axes_coordinates=None,
                      axes_units=None, data_unit=None, **kwargs):
        """
        Plots a 2D image onto the current
        axes. Keyword arguments are passed on to matplotlib.

        Parameters
        ----------
        axes: `astropy.visualization.wcsaxes.core.WCSAxes` or `None`:
            The axes to plot onto. If None the current axes will be used.

        plot_axis_indices: `list`.
            The first axis in WCS object will become the first axis of plot_axis_indices and
            second axis in WCS object will become the second axis of plot_axis_indices.
            Default: ['x', 'y']

        """
        # Set default values of kwargs if not set.
        if axes_coordinates is None:
            axes_coordinates = [None, None]
        if axes_units is None:
            axes_units = [None, None]
        # Set which cube dimensions are on the x an y axes.
        axis_data = ['x', 'x']
        axis_data[plot_axis_indices[1]] = 'y'
        axis_data = axis_data[::-1]
        # Determine data to be plotted
        if data_unit is None:
            data = self.data
        else:
            # If user set data_unit, convert dat to desired unit if self.unit set.
            if self.unit is None:
                raise TypeError("Can only set data_unit if NDCube.unit is set.")
            else:
                data = (self.data * self.unit).to(data_unit).value
        # Combine data with mask
        data = np.ma.masked_array(data, self.mask)
        if axes is None:
            try:
                axes_coord_check = axes_coordinates == [None, None]
            except:
                axes_coord_check = False
            if axes_coord_check:
                # Build slice list for WCS for initializing WCSAxes object.
                if self.wcs.naxis is not 2:
                    slice_list = []
                    index = 0
                    for i, bool_ in enumerate(self.missing_axis):
                        if not bool_:
                            slice_list.append(axis_data[index])
                            index += 1
                        else:
                            slice_list.append(1)
                    if index is not 2:
                        raise ValueError("Dimensions of WCS and data don't match")
                ax = wcsaxes_compat.gca_wcs(self.wcs, slices=slice_list)
                # Set axis labels
                x_wcs_axis = utils.cube.data_axis_to_wcs_axis(plot_axis_indices[0],
                                                             self.missing_axis)
                ax.set_xlabel("{0} [{1}]".format(
                    self.world_axis_physical_types[plot_axis_indices[0]],
                    self.wcs.wcs.cunit[x_wcs_axis]))
                y_wcs_axis = utils.cube.data_axis_to_wcs_axis(plot_axis_indices[1],
                                                             self.missing_axis)
                ax.set_ylabel("{0} [{1}]".format(
                    self.world_axis_physical_types[plot_axis_indices[1]],
                    self.wcs.wcs.cunit[y_wcs_axis]))
                # Plot data
                ax.imshow(data, **kwargs)
            else:
                # Else manually set axes x and y values based on user's input for axes_coordinates.
                axes_values = []
                default_labels = []
                for i, plot_axis_index in enumerate(plot_axis_indices):
                    # If axis coordinate is None, derive axis values from WCS.
                    if axes_coordinates[plot_axis_index] is None:
                        if axes_units[plot_axis_index] is None:
                            # N.B. This assumes axes are independent.  Fix this before merging!!!
                            axis_value = self.axis_world_coords(plot_axis_index)
                            axes_units[plot_axis_index] = axis_value.unit
                            axis_value = self.axis_world_coords()[plot_axis_index].value
                        else:
                            axis_value = self.axis_world_coords(plot_axis_index).to(
                                axes_units[plot_axis_index]).value
                        # Derive default axis label.
                        default_label = "{0} [{1}]".format(
                            self.world_axis_physical_types[plot_axis_index],
                            axes_units[plot_axis_index])
                    elif isinstance(axes_coordinates[plot_axis_index], str):
                        # If axis coordinate is a string, derive axis values from
                        # corresponding extra coord.
                        axis_label_text = copy.deepcopy(axes_coordinates[plot_axis_index])
                        axis_value = self.extra_coords[axes_coordinates[plot_axis_index]]["value"]
                        if isinstance(axis_value, u.Quantity):
                            if axes_units[plot_axis_index] is None:
                                axes_units[plot_axis_index] = axis_value.unit
                            axis_value = axis_value.value
                        else:
                            if axes_units[plot_axis_index] is not None:
                                raise TypeError(INVALID_UNIT_SET_MESSAGE)
                        default_label = "{0} [{1}]".format(axis_label_text,
                                                           axes_units[plot_axis_index])
                    else:
                        # Else user must have manually set the axis coordinates.
                        if isinstance(axes_coordinates[plot_axis_index], u.Quantity):
                            if axes_units[plot_axis_index] is None:
                                axes_units[plot_axis_index] = axes_coordinates[plot_axis_index].unit
                                axis_value = axes_coordinates[plot_axis_index].value
                            else:
                                axis_value = axes_coordinates[plot_axis_index].to(
                                    axes_units[plot_axis_index]).value
                        else:
                            if axes_units[plot_axis_index] is None:
                                axis_value = axes_coordinates[plot_axis_index]
                            else:
                                raise TypeError(INVALID_UNIT_SET_MESSAGE)
                        default_label = " [{0}]".format(axes_units[plot_axis_index])
                    axes_values.append(axis_value)
                    default_labels.append(default_label)
                # Initialize axes object and set values along axis.
                fig, ax = plt.subplots(1, 1)
                # Since we can't assume the x-axis will be uniform, create NonUniformImage
                # axes and add it to the axes object.
                if plot_axis_indices[0] < plot_axis_indices[1]:
                    data = data.transpose()
                im_ax = mpl.image.NonUniformImage(
                    ax, extent=(axes_values[0][0], axes_values[0][-1],
                                axes_values[1][0], axes_values[1][-1]), **kwargs)
                im_ax.set_data(axes_values[0], axes_values[1], data)
                ax.add_image(im_ax)
                # Set the limits, labels, etc. of the axes.
                xlim = kwargs.pop("xlim", (axes_values[0][0], axes_values[0][-1]))
                ax.set_xlim(xlim)
                ylim = kwargs.pop("xlim", (axes_values[1][0], axes_values[1][-1]))
                ax.set_ylim(ylim)
                xlabel = kwargs.pop("xlabel", default_labels[0])
                ylabel = kwargs.pop("ylabel", default_labels[1])
                ax.set_xlabel(xlabel)
                ax.set_ylabel(ylabel)
        return ax

    def _plot_3D_cube(self, plot_axis_indices=None, axes_coordinates=None,
                      axes_units=None, data_unit=None, **kwargs):
        """
        Plots an interactive visualization of this cube using sliders to move through axes
        plot using in the image.
        Parameters other than data and wcs are passed to ImageAnimatorWCS, which in turn
        passes them to imshow.

        Parameters
        ----------
        plot_axis_indices: `list`
            The two axes that make the image.
            Like [-1,-2] this implies cube instance -1 dimension
            will be x-axis and -2 dimension will be y-axis.

        axes_unit: `list` of `astropy.units.Unit`

        axes_coordinates: `list` of physical coordinates for array or None
            If None array indices will be used for all axes.
            If a list it should contain one element for each axis of the numpy array.
            For the image axes a [min, max] pair should be specified which will be
            passed to :func:`matplotlib.pyplot.imshow` as extent.
            For the slider axes a [min, max] pair can be specified or an array the
            same length as the axis which will provide all values for that slider.
            If None is specified for an axis then the array indices will be used
            for that axis.
        """
        # For convenience in inserting dummy variables later, ensure
        # plot_axis_indices are all positive.
        plot_axis_indices = [i if i >= 0 else self.data.ndim + i for i in plot_axis_indices]
        # If axes kwargs not set by user, set them as list of Nones for
        # each axis for consistent behaviour.
        if axes_coordinates is None:
            axes_coordinates = [None] * self.data.ndim
        if axes_units is None:
            axes_units = [None] * self.data.ndim
        # If data_unit set, convert data to that unit
        if data_unit is None:
            data = self.data
        else:
            data = (self.data * self.unit).to(data_unit).value
        # Combine data values with mask.
        data = np.ma.masked_array(data, self.mask)
        # If there are missing axes in WCS object, add corresponding dummy axes to data.
        if data.ndim < self.wcs.naxis:
            new_shape = list(data.shape)
            for i in np.arange(self.wcs.naxis)[self.missing_axis[::-1]]:
                new_shape.insert(i, 1)
                # Also insert dummy coordinates and units.
                axes_coordinates.insert(i, None)
                axes_units.insert(i, None)
                # Iterate plot_axis_indices if neccessary
                for j, pai in enumerate(plot_axis_indices):
                    if pai >= i:
                        plot_axis_indices[j] = plot_axis_indices[j] + 1
            # Reshape data
            data = data.reshape(new_shape)

        ax = ImageAnimatorWCS(data, wcs=self.wcs, image_axes=plot_axis_indices,
                              unit_x_axis=axes_units[plot_axis_indices[0]],
                              unit_y_axis=axes_units[plot_axis_indices[1]],
                              axis_ranges=axes_coordinates[1], **kwargs)
        return ax

    def _animate_cube_1D(self, plot_axis_index=-1, unit_x_axis=None, unit_y_axis=None, **kwargs):
        """Animates an axis of a cube as a line plot with sliders for other axes."""
        # Get real world axis values along axis to be plotted and enter into axes_ranges kwarg.
        xdata = self.axis_world_coords(plot_axis_index)
        # Change x data to desired units it set by user.
        if unit_x_axis:
            xdata = xdata.to(unit_x_axis)
        axis_ranges = [None] * self.data.ndim
        axis_ranges[plot_axis_index] = xdata.value
        if unit_y_axis:
            if self.unit is None:
                raise TypeError("NDCube.unit is None.  Must be an astropy.units.unit or "
                                "valid unit string in order to set unit_y_axis.")
            else:
                data = (self.data * self.unit).to(unit_y_axis)
        # Initiate line animator object.
        plot = LineAnimator(data.value, plot_axis_index=plot_axis_index, axis_ranges=axis_ranges,
                            xlabel="{0} [{1}]".format(
                                self.world_axis_physical_types[plot_axis_index], unit_x_axis),
                            ylabel="Data [{0}]".format(unit_y_axis), **kwargs)
        return plot


def _support_101_plot_API(plot_axis_indices, axes_coordinates, axes_units, data_unit, kwargs):
    """Check if user has used old API and convert it to new API."""
    # Get old API variable values.
    image_axes = kwargs.pop("image_axes", None)
    axis_ranges = kwargs.pop("axis_ranges", None)
    unit_x_axis = kwargs.pop("unit_x_axis", None)
    unit_y_axis = kwargs.pop("unit_y_axis", None)
    unit = kwargs.pop("unit", None)
    # Check if conflicting new and old API values have been set.
    # If not, set new API using old API and raise deprecation warning.
    if image_axes is not None:
        variable_names = ("image_axes", "plot_axis_indices")
        _raise_101_API_deprecation_warning(*variable_names)
        if plot_axis_indices is None:
            plot_axis_indices = image_axes
        else:
            _raise_API_error(*variable_names)
    if axis_ranges is not None:
        variable_names = ("axis_ranges", "axes_coordinates")
        _raise_101_API_deprecation_warning(*variable_names)
        if axes_coordinates is None:
            axes_coordinates = axis_ranges
        else:
            _raise_API_error(*variable_names)
    if (unit_x_axis is not None or unit_y_axis is not None) and axes_units is not None:
        _raise_API_error("unit_x_axis and/or unit_y_axis", "axes_units")
    if axes_units is None:
        variable_names = ("unit_x_axis and unit_y_axis", "axes_units")
        if unit_x_axis is not None:
            _raise_101_API_deprecation_warning(*variable_names)
            if len(plot_axis_indices) == 1:
                axes_units = unit_x_axis
            elif len(plot_axis_indices) == 2:
                if unit_y_axis is None:
                    axes_units = [unit_x_axis, None]
                else:
                    axes_units = [unit_x_axis, unit_y_axis]
            else:
                raise ValueError("Length of image_axes must be less than 3.")
        else:
            if unit_y_axis is not None:
                _raise_101_API_deprecation_warning(*variable_names)
                axes_units = [None, unit_y_axis]
    if unit is not None:
        variable_names = ("unit", "data_unit")
        _raise_101_API_deprecation_warning(*variable_names)
        if data_unit is None:
            data_unit = unit
        else:
            _raise_API_error(*variable_names)
    # Return values of new API
    return plot_axis_indices, axes_coordinates, axes_units, data_unit, kwargs


def _raise_API_error(old_name, new_name):
    raise ValueError(
        "Conflicting inputs: {0} (old API) cannot be set if {1} (new API) is set".format(
            old_name, new_name))

def _raise_101_API_deprecation_warning(old_name, new_name):
    warn("{0} is deprecated and will not be supported in version 2.0.  It will be replaced by {1}.  See docstring.".format(old_name, new_name), DeprecationWarning)
