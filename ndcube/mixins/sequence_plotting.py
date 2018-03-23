import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import astropy.units as u
from sunpy.visualization.imageanimator import ImageAnimatorWCS, LineAnimator

from ndcube import utils

__all__ = ['NDCubePlotMixin']

NON_COMPATIBLE_UNIT_MESSAGE = \
  "All sequence sub-cubes' unit attribute are not compatible with unit_y_axis set by user."

class NDCubeSequencePlotMixin:
    def plot(self, cubesequence, axes=None, plot_axis_indices=None,
             axes_coordinates=None, axes_units=None, data_unit=None, **kwargs):
        """
        Visualizes data in the NDCubeSequence with the sequence axis as a separate dimension.

        Based on the dimensionality of the sequence and value of plot_axis_indices kwarg,
        a Line/Image Animation/Plot is produced.

        Parameters
        ----------
        axes: `astropy.visualization.wcsaxes.core.WCSAxes` or ??? or None.
            The axes to plot onto. If None the current axes will be used.

        plot_axis_indices: `int` or iterable of one or two `int`.
            If two axis indices are given, the sequence is visualized as an image or
            2D animation, assuming the sequence has at least 2 dimensions.
            The dimension indicated by the 0th index is displayed on the
            x-axis while the dimension indicated by the 1st index is displayed on the y-axis.
            If only one axis index is given (either as an int or a list of one int),
            then a 1D line animation is produced with the indicated dimension on the x-axis
            and other dimensions represented by animations sliders.
            Default=[-1, -2].  If sequence only has one dimension,
            plot_axis_indices is ignored and a static 1D line plot is produced.

        axes_coordinates: `None` or `list` of `None` `astropy.units.Quantity` `numpy.ndarray` `str`
            Denotes physical coordinates for plot and slider axes.
            If None coordinates derived from the WCS objects will be used for all axes.
            If a list, its length should equal either the number sequence dimensions or
            the length of plot_axis_indices.
            If the length equals the number of sequence dimensions, each element describes
            the coordinates of the corresponding sequence dimension.
            If the length equals the length of plot_axis_indices,
            the 0th entry describes the coordinates of the x-axis
            while (if length is 2) the 1st entry describes the coordinates of the y-axis.
            Slider axes are implicitly set to None.
            If the number of sequence dimensions equals the length of plot_axis_indices,
            the latter convention takes precedence.
            The value of each entry should be either
            `None` (implies derive the coordinates from the WCS objects),
            an `astropy.units.Quantity` or a `numpy.ndarray` of coordinates for each pixel,
            or a `str` denoting a valid extra coordinate.

        axes_units: `None or `list` of `None`, `astropy.units.Unit` and/or `str`
            If None units derived from the WCS objects will be used for all axes.
            If a list, its length should equal either the number sequence dimensions or
            the length of plot_axis_indices.
            If the length equals the number of sequence dimensions, each element gives the
            unit in which the coordinates along the corresponding sequence dimension should
            displayed whether they be a plot axes or a slider axes.
            If the length equals the length of plot_axis_indices,
            the 0th entry describes the unit in which the x-axis coordinates should be displayed
            while (if length is 2) the 1st entry describes the unit in which the y-axis should
            be displayed.  Slider axes are implicitly set to None.
            If the number of sequence dimensions equals the length of plot_axis_indices,
            the latter convention takes precedence.
            The value of each entry should be either
            `None` (implies derive the unit from the WCS object of the 0th sub-cube),
            `astropy.units.Unit` or a valid unit `str`.

        data_unit: `astropy.unit.Unit` or valid unit `str` or None
            Unit in which data be displayed.  If the length of plot_axis_indices is 2,
            a 2D image/animation is produced and data_unit determines the unit represented by
            the color table.  If the length of plot_axis_indices is 1,
            a 1D plot/animation is produced and data_unit determines the unit in which the
            y-axis is displayed.

        Returns
        -------
        ax: ???
        
        """
        # Check kwargs are in consistent formats and set default values if not done so by user.
        naxis = len(cubesequence.dimensions)
        plot_axis_indices, axes_coordinates, axes_units = _prep_axes_kwargs(
            naxis, plot_axis_indices, axes_coordinates, axes_units)
        if naxis == 1:
            # Make 1D line plot.
            ax = self._plot_1D_sequence(cubesequence, x_axis_coordinates,
                                        unit_x_axis, data_unit, **kwargs)
        else:
            if len(plot_axis_indices) == 1:
                # Since sequence has more than 1 dimension and number of plot axes is 1,
                # produce a 1D line animation.
                if axes_units is not None:
                    unit_x_axis = axes_units[plot_axis_indices[0]]
                else:
                    unit_x_axis = None
                ax = LineAnimatorNDCubeSequence(cubesequence, plot_axis_indices[0], axes_coordinates,
                                                unit_x_axis, data_unit, **kwargs)
            elif len(plot_axis_indices) == 2:
                if naxis == 2:
                    # Since sequence has 2 dimensions and number of plot axes is 2,
                    # produce a 2D image.
                    ax = self._plot_2D_sequence(cubesequence, plot_axis_indices, axes_coordinates,
                                                axes_units, data_unit, **kwargs)
                else:
                    # Since sequence has more than 2 dimensions and number of plot axes is 2,
                    # produce a 2D animation.
                    if axes_units is None:
                        axes_units = [None] * naxis
                    ax = ImageAnimatorNDCubeSequence(
                        cubesequence, image_axes=plot_axis_indices,
                        axis_ranges=axes_coordinates, unit_x_axis=axes_units[plot_axis_indices[0]],
                        unit_y_axis=axes_units[plot_axis_indices[1]], **kwargs)

        return ax

    def plot_as_cube(self, cubesequence, axes=None, plot_axis_indices=None,
                     axes_coordinates=None, axes_units=None, data_unit=None, **kwargs):
        """
        Visualizes data in the NDCubeSequence with the sequence axis folded into the common axis.

        Based on the cube-like dimensionality of the sequence and value of plot_axis_indices
        kwarg, a Line/Image Plot/Animation is produced.

         Parameters
        ----------
        axes: `astropy.visualization.wcsaxes.core.WCSAxes` or ??? or None.
            The axes to plot onto. If None the current axes will be used.

        plot_axis_indices: `int` or iterable of one or two `int`.
            If two axis indices are given, the sequence is visualized as an image or
            2D animation, assuming the sequence has at least 2 cube-like dimensions.
            The cube-like dimension indicated by the 0th index is displayed on the
            x-axis while the cube-like dimension indicated by the 1st index is
            displayed on the y-axis. If only one axis index is given (either as an int
            or a list of one int), then a 1D line animation is produced with the indicated
            cube-like dimension on the x-axis and other cube-like dimensions represented
            by animations sliders.
            Default=[-1, -2].  If sequence only has one cube-like dimension,
            plot_axis_indices is ignored and a static 1D line plot is produced.

        axes_coordinates: `None` or `list` of `None` `astropy.units.Quantity` `numpy.ndarray` `str`
            Denotes physical coordinates for plot and slider axes.
            If None coordinates derived from the WCS objects will be used for all axes.
            If a list, its length should equal either the number cube-like dimensions or
            the length of plot_axis_indices.
            If the length equals the number of cube-like dimensions, each element describes
            the coordinates of the corresponding cube-like dimension.
            If the length equals the length of plot_axis_indices,
            the 0th entry describes the coordinates of the x-axis
            while (if length is 2) the 1st entry describes the coordinates of the y-axis.
            Slider axes are implicitly set to None.
            If the number of cube-like dimensions equals the length of plot_axis_indices,
            the latter convention takes precedence.
            The value of each entry should be either
            `None` (implies derive the coordinates from the WCS objects),
            an `astropy.units.Quantity` or a `numpy.ndarray` of coordinates for each pixel,
            or a `str` denoting a valid extra coordinate.

        axes_units: `None or `list` of `None`, `astropy.units.Unit` and/or `str`
            If None units derived from the WCS objects will be used for all axes.
            If a list, its length should equal either the number cube-like dimensions or
            the length of plot_axis_indices.
            If the length equals the number of cube-like dimensions, each element gives the
            unit in which the coordinates along the corresponding cube-like dimension should
            displayed whether they be a plot axes or a slider axes.
            If the length equals the length of plot_axis_indices,
            the 0th entry describes the unit in which the x-axis coordinates should be displayed
            while (if length is 2) the 1st entry describes the unit in which the y-axis should
            be displayed.  Slider axes are implicitly set to None.
            If the number of cube-like dimensions equals the length of plot_axis_indices,
            the latter convention takes precedence.
            The value of each entry should be either
            `None` (implies derive the unit from the WCS object of the 0th sub-cube),
            `astropy.units.Unit` or a valid unit `str`.

        data_unit: `astropy.unit.Unit` or valid unit `str` or None
            Unit in which data be displayed.  If the length of plot_axis_indices is 2,
            a 2D image/animation is produced and data_unit determines the unit represented by
            the color table.  If the length of plot_axis_indices is 1,
            a 1D plot/animation is produced and data_unit determines the unit in which the
            y-axis is displayed.

        Returns
        -------
        ax: ???
        
        """
        # Verify common axis is set.
        if cubesequence._common_axis is None:
            raise TypeError("Common axis must be set.")
        # Check kwargs are in consistent formats and set default values if not done so by user.
        naxis = len(cubesequence.cube_like_dimensions)
        plot_axis_indices, axes_coordinates, axes_units = _prep_axes_kwargs(
            naxis, plot_axis_indices, axes_coordinates, axes_units)
        # Produce plot/image/animation based on cube-like dimensions of sequence.
        if naxis == 1:
            # Since sequence has 1 cube-like dimension, produce a 1D line plot.
            ax = self._plot_2D_sequence_as_1Dline(
                cubesequence, x_axis_coordinates=x_axis_coordinates,
                unit_x_axis=unit_x_axis, data_unit=data_unit, **kwargs)
        else:
            if len(plot_axis_indices) == 1:
                # Since sequence has more than 1 cube-like dimension and
                # number of plot axes is 1, produce a 1D line animation.
                if axes_units is not None:
                    unit_x_axis = axes_units[plot_axis_indices[0]]
                else:
                    unit_x_axis = None
                ax = LineAnimatorCubeLikeNDCubeSequence(cubesequence, plot_axis_indices[0],
                                                        axes_coordinates, unit_x_axis,
                                                        data_unit=data_unit, **kwargs)
            elif len(plot_axis_indices) == 2:
                if naxis == 2:
                    # Since sequence has 2 cube-like dimensions and
                    # number of plot axes is 2, produce a 2D image.
                    ax = self._plot_3D_sequence_as_2Dimage(axes, plot_axis_indices,
                                                           axes_coordinates, axes_units,
                                                           data_unit, **kwargs)
                else:
                    # Since sequence has more than 2 cube-like dimensions and
                    # number of plot axes is 2, produce a 2D animation.
                    ax = ImageAnimatorCubeLikeNDCubeSequence(cubesequence, plot_axis_indices,
                                                             axes_coordinates,
                                                             axes_units[plot_axis_indices[0]],
                                                             axes_units[plot_axis_indices[1]],
                                                             **kwargs)
        return ax

    def _plot_1D_sequence(self, cubesequence, axes_coordinates=None,
                          axes_units=None, data_unit=None, **kwargs):
        """
        Visualizes an NDCubeSequence of scalar NDCubes as a line plot.

        A scalar NDCube is one whose NDCube.data is a scalar rather than an array.

        Parameters
        ----------
        axes_coordinates: `numpy.ndarray` `astropy.unit.Quantity` `str` `None` or length 1 `list`
            Denotes the physical coordinates of the x-axis.
            If list, must be of length 1 containing one object of one of the other allowed types.
            If None, coordinates are derived from the WCS objects.
            If an  `astropy.units.Quantity` or a `numpy.ndarray` gives the coordinates for
            each pixel along the x-axis.
            If a `str`, denotes the extra coordinate to be used.  The extra coordinate must
            correspond to the sequence axis.

        axes_units: `astropy.unit.Unit` or valid unit `str` or length 1 `list` of those types.
            Unit in which X-axis should be displayed.  Must be compatible with the unit of
            the coordinate denoted by x_axis_range.  Not used if x_axis_range is a
            `numpy.ndarray` or the designated extra coordinate is a `numpy.ndarray`

        data_unit: `astropy.units.unit` or valid unit `str`
            The units into which the y-axis should be displayed.  The unit attribute of all
            the sub-cubes must be compatible to set this kwarg.

        """
        # Derive x-axis coordinates and unit from inputs.
        x_axis_coordinates, unit_x_axis = _derive_1D_coordinates_and_units(axes_coordinates,
                                                                           axes_units)
        # Check that the unit attribute is a set in all cubes and derive unit_y_axis if not set.
        unit_y_axis = data_unit
        sequence_units, unit_y_axis = _determine_sequence_units(cubesequence.data, unit_y_axis)
        # If all cubes have unit set, create a data quantity from cubes' data.
        if sequence_units is not None:
            ydata = u.Quantity([cube.data * sequence_units[i]
                                for i, cube in enumerate(cubesequence.data)], unit=unit_y_axis).value
            yerror = u.Quantity([cube.uncertainty.array * sequence_units[i]
                                 for i, cube in enumerate(cubesequence.data)], unit=unit_y_axis).value
        # If not all cubes have their unit set, create a data array from cube's data.
        else:
            if unit_y_axis is not None:
                raise ValueError(NON_COMPATIBLE_UNIT_MESSAGE)
            ydata = np.array([cube.data for cube in cubesequence.data])
            yerror = np.array([cube.uncertainty for cube in cubesequence.data])
        if all(yerror == None):
            yerror = None
        # Define x-axis data.
        if x_axis_coordinates is None:
            # Since scalar NDCubes have no array/pixel indices, WCS translations don't work.
            # Therefore x-axis values will be unitless sequence indices unless supplied by user
            # or an extra coordinate is designated.
            xdata = np.arange(int(cubesequence.dimensions[0].value))
            xname = cubesequence.world_axis_physical_types[0]
        elif isinstance(x_axis_coordinates, str):
            xdata = cubesequence.sequence_axis_extra_coords[x_axis_coordinates]
            xname = x_axis_coordinate
        else:
            xdata = x_axis_coordinates
            xname = cubesequence.world_axis_physical_types[0]
        if isinstance(xdata, u.Quantity):
            if unit_x_axis is None:
                unit_x_axis = xdata.unit
            else:
                xdata = xdata.to(unit_x_axis)
        else:
            unit_x_axis = None
        default_xlabel = "{0} [{1}]".format(xname, unit_x_axis)
        fig, ax = _make_1D_sequence_plot(xdata, ydata, yerror, unit_y_axis, default_xlabel, kwargs)
        return ax

    def _plot_2D_sequence_as_1Dline(self, cubesequence, x_axis_coordinates=None,
                                    axes_units=None, data_unit=None, **kwargs):
        """
        Visualizes an NDCubeSequence of 1D NDCubes with a common axis as a line plot.

        Called if plot_as_cube=True.

        Parameters
        ----------
        Same as _plot_1D_sequence

        """
        # Derive x-axis coordinates and unit from inputs.
        x_axis_coordinates, unit_x_axis = _derive_1D_coordinates_and_units(axes_coordinates,
                                                                           axes_units)
        # Check that the unit attribute is set of all cubes and derive unit_y_axis if not set.
        unit_y_axis = data_unit
        sequence_units, unit_y_axis = _determine_sequence_units(cubesequence.data, unit_y_axis)
        # If all cubes have unit set, create a y data quantity from cube's data.
        if sequence_units is not None:
            ydata = np.concatenate([(cube.data * sequence_units[i]).to(unit_y_axis).value
                                    for i, cube in enumerate(cubesequence.data)])
            yerror = np.concatenate(
                [(cube.uncertainty.array * sequence_units[i]).to(unit_y_axis).value
                 for i, cube in enumerate(cubesequence.data)])
        else:
            if unit_y_axis is not None:
                raise ValueError(NON_COMPATIBLE_UNIT_MESSAGE)
            # If not all cubes have unit set, create a y data array from cube's data.
            ydata = np.concatenate([cube.data for cube in cubesequence.data])
            yerror = np.array([cube.uncertainty for cube in cubesequence.data])
            if all(yerror == None):
                yerror = None
            else:
                if any(yerror == None):
                    w = np.where(yerror == None)[0]
                    for i in w:
                        yerror[i] = np.zeros(int(cubesequence[i].dimensions.value))
                yerror = np.concatenate(yerror)
        # Define x-axis data.
        if x_axis_coordinates is None:
            if unit_x_axis is None:
                unit_x_axis = np.asarray(cubesequence[0].wcs.wcs.cunit)[
                    np.invert(cubesequence[0].missing_axis)][0]
            xdata = u.Quantity(np.concatenate([cube.axis_world_coords().to(unit_x_axis).value
                                               for cube in cubesequence]), unit=unit_x_axis)
            xname = cubesequence.cube_like_world_axis_physical_types[0]
        elif isinstance(x_axis_coordinates, str):
            xdata = cubesequence.common_axis_extra_coords[x_axis_coordinates]
            xname = x_axis_coordinates
        else:
            xdata = x_axis_coordinates
        if isinstance(xdata, u.Quantity):
            if unit_x_axis is None:
                unit_x_axis = xdata.unit
            else:
                xdata = xdata.to(unit_x_axis)
        else:
            unit_x_axis = None
        default_xlabel = "{0} [{1}]".format(xname, unit_x_axis)
        # Plot data
        fig, ax = _make_1D_sequence_plot(xdata, ydata, yerror, unit_y_axis, default_xlabel, kwargs)
        return ax


    def _plot_2D_sequence(self, cubesequence, plot_axis_indices=None, axes_coordinates=None,
                          axes_units=None, data_unit=None, **kwargs):
        """
        Visualizes an NDCubeSequence of 1D NDCubes as a 2D image.

        **kwargs are fed into matplotlib.image.NonUniformImage.

        Parameters
        ----------
        Same as self.plot()

        """
        # Set default values of kwargs if not set.
        if axes_coordinates is None:
            axes_coordinates = [None, None]
        if axes_units is None:
            axes_units = [None, None]
        if plot_axis_indices is None:
            plot_axis_indices = [-1, -2]
        # Convert plot_axis_indices to array for function operations.
        plot_axis_indices = np.asarray(plot_axis_indices)
        # Check that the unit attribute is set of all cubes and derive unit_y_axis if not set.
        sequence_units, data_unit = _determine_sequence_units(cubesequence.data, data_unit)
        # If all cubes have unit set, create a data quantity from cube's data.
        if sequence_units is not None:
            data = np.stack([(cube.data * sequence_units[i]).to(data_unit).value
                             for i, cube in enumerate(cubesequence.data)])
        else:
            data = np.stack([cube.data for i, cube in enumerate(cubesequence.data)])
        # Transpose data if user-defined images_axes require it.
        if plot_axis_indices[0] < plot_axis_indices[1]:
            data = data.transpose()
        # Determine index of above axes variables corresponding to cube axis.
        cube_axis_index = 1
        # Determine index of above variables corresponding to sequence axis.
        sequence_axis_index = 0
        # Derive the coordinates, unit, and default label of the cube axis.
        cube_axis_unit = axes_units[cube_axis_index]
        if axes_coordinates[cube_axis_index] is None:
            if cube_axis_unit is None:
                cube_axis_unit = np.array(cubesequence[0].wcs.wcs.cunit)[
                    np.invert(cubesequence[0].missing_axis)][0]
            cube_axis_coords = cubesequence[0].axis_world_coords().to(cube_axis_unit).value
            cube_axis_name = cubesequence.world_axis_physical_types[1]
        else:
            if isinstance(axes_coordinates[cube_axis_index], str):
                cube_axis_coords = \
                  cubesequence[0].extra_coords[axes_coordinates[cube_axis_index]]["value"]
                cube_axis_name = axes_coordinates[cube_axis_index]
            else:
                cube_axis_coords = axes_coordinates[cube_axis_index]
                cube_axis_name = cubesequence.world_axis_physical_types[1]
            if isinstance(cube_axis_coords, u.Quantity):
                if cube_axis_unit is None:
                    cube_axis_unit = cube_axis_coords.unit
                    cube_axis_coords = cube_axis_coords.value
                else:
                    cube_axis_coords = cube_axis_coords.to(cube_axis_unit).value
            else:
                cube_axis_coords = None
        default_cube_axis_label = "{0} [{1}]".format(cube_axis_name, cube_axis_unit)
        axes_coordinates[cube_axis_index] = cube_axis_coords
        axes_units[cube_axis_index] = cube_axis_unit
        # Derive the coordinates, unit, and default label of the sequence axis.
        sequence_axis_unit = axes_units[sequence_axis_index]
        if axes_coordinates[sequence_axis_index] is None:
            sequence_axis_coords = np.arange(len(cubesequence.data))
            sequence_axis_name = cubesequence.world_axis_physical_types[0]
        elif isinstance(axes_coordinates[sequence_axis_index], str):
            sequence_axis_coords = \
              cubesequence.sequence_axis_extra_coords[axes_coordinates[sequence_axis_index]]
            sequence_axis_name = axes_coordinates[sequence_axis_index]
        else:
            sequence_axis_coords = axes_coordinates[sequence_axis_index]
            sequence_axis_name = cubesequence.world_axis_physical_types[0]
        if isinstance(sequence_axis_coords, u.Quantity):
            if sequence_axis_unit is None:
                sequence_axis_unit = sequence_axis_coords.unit
                sequence_axis_coords = sequence_axis_coords.value
            else:
                sequence_axis_coords = sequence_axis_coords.to(sequence_axis_unit).value
        else:
            sequence_axis_unit = None
        default_sequence_axis_label = "{0} [{1}]".format(sequence_axis_name, sequence_axis_unit)
        axes_coordinates[sequence_axis_index] = sequence_axis_coords
        axes_units[sequence_axis_index] = sequence_axis_unit
        axes_labels = [None, None]
        axes_labels[cube_axis_index] = default_cube_axis_label
        axes_labels[sequence_axis_index] = default_sequence_axis_label
        # Plot image.
        # Create figure and axes objects.
        fig, ax = plt.subplots(1, 1)
        # Since we can't assume the x-axis will be uniform, create NonUniformImage
        # axes and add it to the axes object.
        im_ax = mpl.image.NonUniformImage(
            ax, extent=(axes_coordinates[plot_axis_indices[0]][0], axes_coordinates[plot_axis_indices[0]][-1],
                        axes_coordinates[plot_axis_indices[1]][0], axes_coordinates[plot_axis_indices[1]][-1]),
            **kwargs)
        im_ax.set_data(axes_coordinates[plot_axis_indices[0]], axes_coordinates[plot_axis_indices[1]], data)
        ax.add_image(im_ax)
        # Set the limits, labels, etc. of the axes.
        ax.set_xlim((axes_coordinates[plot_axis_indices[0]][0], axes_coordinates[plot_axis_indices[0]][-1]))
        ax.set_ylim((axes_coordinates[plot_axis_indices[1]][0], axes_coordinates[plot_axis_indices[1]][-1]))
        ax.set_xlabel(axes_labels[plot_axis_indices[0]])
        ax.set_ylabel(axes_labels[plot_axis_indices[1]])

        return ax

    def _plot_3D_sequence_as_2Dimage(self, cubesequence, plot_axis_indices=None,
                                     axes_coordinates=None, axes_units=None, data_unit=None,
                                     **kwargs):
        """
        Visualizes an NDCubeSequence of 2D NDCubes with a common axis as a 2D image.

        Called if plot_as_cube=True.

        """
        # Set default values of kwargs if not set.
        if axes_coordinates is None:
            axes_coordinates = [None, None]
        if axes_units is None:
            axes_units = [None, None]
        if plot_axis_indices is None:
            plot_axis_indices = [-1, -2]
        # Convert plot_axis_indices to array for function operations.
        plot_axis_indices = np.asarray(plot_axis_indices)
        # Check that the unit attribute is set of all cubes and derive unit_y_axis if not set.
        sequence_units, data_unit = _determine_sequence_units(cubesequence.data, data_unit)
        # If all cubes have unit set, create a data quantity from cube's data.
        if sequence_units is not None:
            data = np.concatenate([(cube.data * sequence_units[i]).to(data_unit).value
                                   for i, cube in enumerate(cubesequence.data)],
                                   axis=cubesequence._common_axis)
        else:
            data = np.concatenate([cube.data for cube in cubesequence.data],
                                  axis=cubesequence._common_axis)
        if plot_axis_indices[0] < plot_axis_indices[1]:
            data = data.transpose()
        # Determine index of common axis and other cube axis.
        common_axis_index = cubesequence._common_axis
        cube_axis_index = [0, 1]
        cube_axis_index.pop(common_axis_index)
        cube_axis_index = cube_axis_index[0]
        # Derive the coordinates, unit, and default label of the cube axis.
        cube_axis_unit = axes_units[cube_axis_index]
        if axes_coordinates[cube_axis_index] is None:
            if cube_axis_unit is None:
                cube_axis_unit = np.array(cubesequence[0].wcs.wcs.cunit)[
                    np.invert(cubesequence[0].missing_axis)][0]
            cube_axis_coords = \
              cubesequence[0].axis_world_coords()[cube_axis_index].to(cube_axis_unit).value
            cube_axis_name = cubesequence.world_axis_physical_types[1]
        else:
            if isinstance(axes_coordinates[cube_axis_index], str):
                cube_axis_coords = \
                  cubesequence[0].extra_coords[axes_coordinates[cube_axis_index]]["value"]
                cube_axis_name = axes_coordinates[cube_axis_index]
            else:
                cube_axis_coords = axes_coordinates[cube_axis_index]
                cube_axis_name = cubesequence.world_axis_physical_types[1]
            if isinstance(cube_axis_coords, u.Quantity):
                if cube_axis_unit is None:
                    cube_axis_unit = cube_axis_coords.unit
                    cube_axis_coords = cube_axis_coords.value
                else:
                    cube_axis_coords = cube_axis_coords.to(cube_axis_unit).value
            else:
                cube_axis_coords = None
        default_cube_axis_label = "{0} [{1}]".format(cube_axis_name, cube_axis_unit)
        axes_coordinates[cube_axis_index] = cube_axis_coords
        axes_units[cube_axis_index] = cube_axis_unit
        # Derive the coordinates, unit, and default label of the common axis.
        common_axis_unit = axes_units[common_axis_index]
        if axes_coordinates[common_axis_index] is None:
            # Concatenate values along common axis for each cube.
            if common_axis_unit is None:
                wcs_common_axis_index = utils.cube.data_axis_to_wcs_axis(
                    common_axis_index, cubesequence[0].missing_axis)
                common_axis_unit = np.array(cubesequence[0].wcs.wcs.cunit)[wcs_common_axis_index]
            common_axis_coords = u.Quantity(np.concatenate(
                [cube.axis_world_coords()[common_axis_index].to(common_axis_unit).value
                 for cube in cubesequence.data]), unit=common_axis_unit)
            common_axis_name = cubesequence.cube_like_world_axis_physical_types[common_axis_index]
        elif isinstance(axes_coordinates[common_axis_index], str):
            common_axis_coords = \
              cubesequence.common_axis_extra_coords[axes_coordinates[common_axis_index]]
            sequence_axis_name = axes_coordinates[common_axis_index]
        else:
            common_axis_coords = axes_coordinates[common_axis_index]
            common_axis_name = cubesequence.cube_like_world_axis_physical_types[common_axis_index]
        if isinstance(common_axis_coords, u.Quantity):
            if common_axis_unit is None:
                common_axis_unit = common_axis_coords.unit
                common_axis_coords = common_axis_coords.value
            else:
                common_axis_coords = common_axis_coords.to(common_axis_unit).value
        else:
            common_axis_unit = None
        default_common_axis_label = "{0} [{1}]".format(common_axis_name, common_axis_unit)
        axes_coordinates[common_axis_index] = common_axis_coords
        axes_units[common_axis_index] = common_axis_unit
        axes_labels = [None, None]
        axes_labels[cube_axis_index] = default_cube_axis_label
        axes_labels[common_axis_index] = default_common_axis_label
        # Plot image.
        # Create figure and axes objects.
        fig, ax = plt.subplots(1, 1)
        # Since we can't assume the x-axis will be uniform, create NonUniformImage
        # axes and add it to the axes object.
        im_ax = mpl.image.NonUniformImage(
            ax, extent=(axes_coordinates[plot_axis_indices[0]][0], axes_coordinates[plot_axis_indices[0]][-1],
                        axes_coordinates[plot_axis_indices[1]][0], axes_coordinates[plot_axis_indices[1]][-1]),
            **kwargs)
        im_ax.set_data(axes_coordinates[plot_axis_indices[0]], axes_coordinates[plot_axis_indices[1]], data)
        ax.add_image(im_ax)
        # Set the limits, labels, etc. of the axes.
        ax.set_xlim((axes_coordinates[plot_axis_indices[0]][0], axes_coordinates[plot_axis_indices[0]][-1]))
        ax.set_ylim((axes_coordinates[plot_axis_indices[1]][0], axes_coordinates[plot_axis_indices[1]][-1]))
        ax.set_xlabel(axes_labels[plot_axis_indices[0]])
        ax.set_ylabel(axes_labels[plot_axis_indices[1]])

        return ax


    def _animate_ND_sequence(self, cubesequence, *args, **kwargs):
        """
        Visualizes an NDCubeSequence of >2D NDCubes as 2D an animation with N-2 sliders.

        """
        return ImageAnimatorNDCubeSequence(cubesequence, *args, **kwargs)

    def _animate_ND_sequence_as_Nminus1Danimation(self, cubesequence, *args, **kwargs):
        """
        Visualizes a common axis NDCubeSequence of >3D NDCubes as 2D animation with N-3 sliders.

        Called if plot_as_cube=True.

        """
        return ImageAnimatorCommonAxisNDCubeSequence(cubesequence, *args, **kwargs)


class ImageAnimatorNDCubeSequence(ImageAnimatorWCS):
    """
    Animates N-dimensional data with the associated astropy WCS object.

    The following keyboard shortcuts are defined in the viewer:

    left': previous step on active slider
    right': next step on active slider
    top': change the active slider up one
    bottom': change the active slider down one
    'p': play/pause active slider

    This viewer can have user defined buttons added by specifying the labels
    and functions called when those buttons are clicked as keyword arguments.

    Parameters
    ----------
    seq: `ndcube.datacube.CubeSequence`
        The list of cubes.

    image_axes: `list`
        The two axes that make the image

    fig: `matplotlib.figure.Figure`
        Figure to use

    axis_ranges: list of physical coordinates for array or None
        If None array indices will be used for all axes.
        If a list it should contain one element for each axis of the numpy array.
        For the image axes a [min, max] pair should be specified which will be
        passed to :func:`matplotlib.pyplot.imshow` as extent.
        For the slider axes a [min, max] pair can be specified or an array the
        same length as the axis which will provide all values for that slider.
        If None is specified for an axis then the array indices will be used
        for that axis.

    interval: `int`
        Animation interval in ms

    colorbar: `bool`
        Plot colorbar

    button_labels: `list`
        List of strings to label buttons

    button_func: `list`
        List of functions to map to the buttons

    unit_x_axis: `astropy.units.Unit`
        The unit of x axis.

    unit_y_axis: `astropy.units.Unit`
        The unit of y axis.

    Extra keywords are passed to imshow.

    """
    def __init__(self, seq, wcs=None, **kwargs):
        if wcs is None:
            wcs = seq[0].wcs
        self.sequence = seq.data
        self.cumul_cube_lengths = np.cumsum(np.ones(len(self.sequence)))
        data_concat = np.stack([cube.data for cube in seq.data])
        # Add dimensions of length 1 of concatenated data array
        # shape for an missing axes.
        if seq[0].wcs.naxis != len(seq.dimensions) - 1:
            new_shape = list(data_concat.shape)
            for i in np.arange(seq[0].wcs.naxis)[seq[0].missing_axis[::-1]]:
                new_shape.insert(i+1, 1)
            data_concat = data_concat.reshape(new_shape)
        # Add dummy axis to WCS object to represent sequence axis.
        new_wcs = utils.wcs.append_sequence_axis_to_wcs(wcs)

        super(ImageAnimatorNDCubeSequence, self).__init__(data_concat, wcs=new_wcs, **kwargs)


class ImageAnimatorCubeLikeNDCubeSequence(ImageAnimatorWCS):
    """
    Animates N-dimensional data with the associated astropy WCS object.

    The following keyboard shortcuts are defined in the viewer:

    left': previous step on active slider
    right': next step on active slider
    top': change the active slider up one
    bottom': change the active slider down one
    'p': play/pause active slider

    This viewer can have user defined buttons added by specifying the labels
    and functions called when those buttons are clicked as keyword arguments.

    Parameters
    ----------
    seq: `ndcube.datacube.CubeSequence`
        The list of cubes.

    image_axes: `list`
        The two axes that make the image

    fig: `matplotlib.figure.Figure`
        Figure to use

    axis_ranges: list of physical coordinates for array or None
        If None array indices will be used for all axes.
        If a list it should contain one element for each axis of the numpy array.
        For the image axes a [min, max] pair should be specified which will be
        passed to :func:`matplotlib.pyplot.imshow` as extent.
        For the slider axes a [min, max] pair can be specified or an array the
        same length as the axis which will provide all values for that slider.
        If None is specified for an axis then the array indices will be used
        for that axis.

    interval: `int`
        Animation interval in ms

    colorbar: `bool`
        Plot colorbar

    button_labels: `list`
        List of strings to label buttons

    button_func: `list`
        List of functions to map to the buttons

    unit_x_axis: `astropy.units.Unit`
        The unit of x axis.

    unit_y_axis: `astropy.units.Unit`
        The unit of y axis.

    Extra keywords are passed to imshow.

    """
    def __init__(self, seq, wcs=None, **kwargs):
        if seq._common_axis is None:
            raise ValueError("Common axis must be set to use this class. "
                             "Use ImageAnimatorNDCubeSequence.")
        if wcs is None:
            wcs = seq[0].wcs
        self.sequence = seq.data
        self.cumul_cube_lengths = np.cumsum(np.array(
            [c.dimensions[0].value for c in self.sequence], dtype=int))
        data_concat = np.concatenate([cube.data for cube in seq.data], axis=seq._common_axis)
        # Add dimensions of length 1 of concatenated data array
        # shape for an missing axes.
        if seq[0].wcs.naxis != len(seq.dimensions) - 1:
            new_shape = list(data_concat.shape)
            for i in np.arange(seq[0].wcs.naxis)[seq[0].missing_axis[::-1]]:
                new_shape.insert(i, 1)
            data_concat = data_concat.reshape(new_shape)

        super(ImageAnimatorCommonAxisNDCubeSequence, self).__init__(
            data_concat, wcs=wcs, **kwargs)

    def update_plot(self, val, im, slider):
        val = int(val)
        ax_ind = self.slider_axes[slider.slider_ind]
        ind = np.argmin(np.abs(self.axis_ranges[ax_ind] - val))
        self.frame_slice[ax_ind] = ind
        list_slices_wcsaxes = list(self.slices_wcsaxes)
        sequence_slice = utils.sequence._convert_cube_like_index_to_sequence_slice(
            val, self.cumul_cube_lengths)
        sequence_index = sequence_slice.sequence_index
        cube_index = sequence_slice.common_axis_item
        list_slices_wcsaxes[self.wcs.naxis-ax_ind-1] = cube_index
        self.slices_wcsaxes = list_slices_wcsaxes
        if val != slider.cval:
            self.axes.reset_wcs(
                wcs=self.sequence[sequence_index].wcs, slices=self.slices_wcsaxes)
            self._set_unit_in_axis(self.axes)
            im.set_array(self.data[self.frame_slice])
            slider.cval = val


class LineAnimatorNDCubeSequence(LineAnimator):
    """
    Animates N-dimensional data with the associated astropy WCS object.

    The following keyboard shortcuts are defined in the viewer:

    left': previous step on active slider
    right': next step on active slider
    top': change the active slider up one
    bottom': change the active slider down one
    'p': play/pause active slider

    This viewer can have user defined buttons added by specifying the labels
    and functions called when those buttons are clicked as keyword arguments.

    Parameters
    ----------
    seq: `ndcube.datacube.CubeSequence`
        The list of cubes.

    image_axes: `list`
        The two axes that make the image

    fig: `matplotlib.figure.Figure`
        Figure to use

    axis_ranges: list of physical coordinates for array or None
        If None array indices will be used for all axes.
        If a list it should contain one element for each axis of the numpy array.
        For the image axes a [min, max] pair should be specified which will be
        passed to :func:`matplotlib.pyplot.imshow` as extent.
        For the slider axes a [min, max] pair can be specified or an array the
        same length as the axis which will provide all values for that slider.
        If None is specified for an axis then the array indices will be used
        for that axis.

    interval: `int`
        Animation interval in ms

    colorbar: `bool`
        Plot colorbar

    button_labels: `list`
        List of strings to label buttons

    button_func: `list`
        List of functions to map to the buttons

    unit_x_axis: `astropy.units.Unit`
        The unit of x axis.

    unit_y_axis: `astropy.units.Unit`
        The unit of y axis.

    Extra keywords are passed to imshow.

    """
    def __init__(self, seq, plot_axis_index=None, axis_ranges=None, unit_x_axis=None,
                 data_unit=None, xlabel=None, ylabel=None, xlim=None, ylim=None, **kwargs):
        if plot_axis_index is None:
            plot_axis_index = -1
        #try:
        #    sequence_units, data_unit = _determine_sequence_units(seq.data, data_unit)
        #except ValueError:
        #    sequence_error = None
        # Form single cube of data from sequence.
        #if sequence_error is None:
        #    data_concat = np.stack([cube.data for i, cube in enumerate(seq.data)])
        #else:
        #    data_concat = np.stack([(cube.data * sequence_units[i]).to(data_unit).value
        #                            for i, cube in enumerate(seq.data)])

        # Combine data from cubes in sequence.
        # If cubes have masks, make result a masked array.
        cubes_with_mask = np.array([False if cube.mask is None else True for cube in seq.data])
        if not cubes_with_mask.all():
            data_concat = np.stack([cube.data for cube in seq.data])
        else:
            datas = []
            masks = []
            for i, cube in enumerate(seq.data):
                datas.append(cube.data)
                if cubes_with_mask[i]:
                    masks.append(cube.mask)
                else:
                    masks.append(np.zeros_like(cube.data, dtype=bool))
            data_concat = np.ma.masked_array(np.stack(datas), np.stack(masks))
        # Ensure plot_axis_index is represented in the positive convention.
        if plot_axis_index < 0:
            plot_axis_index = len(seq.dimensions) + plot_axis_index
        # Calculate the x-axis values if axis_ranges not supplied.
        cube_plot_axis_index = plot_axis_index - 1
        if axis_ranges is None:
            axis_ranges = [None] * len(seq.dimensions)
            if plot_axis_index == 0:
                axis_ranges[plot_axis_index] = np.arange(len(seq.data))
            else:
                # Define unit of x-axis if not supplied by user.
                if unit_x_axis is None:
                    wcs_plot_axis_index = utils.cube.data_axis_to_wcs_axis(
                        cube_plot_axis_index, seq[0].missing_axis)
                    unit_x_axis = np.asarray(seq[0].wcs.wcs.cunit)[wcs_plot_axis_index]
                # Get x-axis values from each cube and combine into a single
                # array for axis_ranges kwargs.
                x_axis_coords = _get_non_common_axis_x_axis_coords(seq.data, cube_plot_axis_index)
                axis_ranges[plot_axis_index] = np.stack(x_axis_coords)
            # Set x-axis label.
            if xlabel is None:
                xlabel = "{0} [{1}]".format(seq.world_axis_physical_types[plot_axis_index],
                                            unit_x_axis)
        else:
            # If the axis range is being defined by an extra coordinate...
            if isinstance(axis_ranges[plot_axis_index], str):
                axis_extra_coord = axis_ranges[plot_axis_index]
                if plot_axis_index == 0:
                    # If the sequence axis is the plot axis, use
                    # sequence_axis_extra_coords to get the extra coord values
                    # for whole sequence.
                    x_axis_coords = seq.sequence_axis_extra_coords[axis_extra_coord]
                    if isinstance(x_axis_coords, u.Quantity) and (unit_x_axis is not None):
                        x_axis_coords = x_axis_coords.to(unit_x_axis).value
                else:
                    # Else get extra coord values from each cube and
                    # combine into a single array for axis_ranges kwargs.
                    # First, confirm extra coord is of same type and corresponds
                    # to same axes in each cube.
                    extra_coord_type = np.empty(len(seq.data), dtype=object)
                    extra_coord_axes = np.empty(len(seq.data), dtype=object)
                    x_axis_coords = []
                    for i, cube in enumerate(seq.data):
                        cube_axis_extra_coord = cube.extra_coords[axis_extra_coord]
                        extra_coord_type[i] = type(cube_axis_extra_coord["value"])
                        extra_coord_axes[i] = cube_axis_extra_coord["axis"]
                        x_axis_coords.append(cube_axis_extra_coord["value"])
                    if not extra_coord_type.all() == extra_coord_type[0]:
                        raise TypeError("Extra coord {0} must be of same type for all NDCubes to "
                                        "use it to define a plot axis.".format(axis_extra_coord))
                    else:
                        extra_coord_type = extra_coord_type[0]
                    if not extra_coord_axes.all() == extra_coord_axes[0]:
                        raise ValueError("Extra coord {0} must correspond to same axes in each "
                                         "NDCube to use it to define a plot axis.".format(
                                             axis_extra_coord))
                    else:
                        if isinstance(extra_coord_axes[0], (int, np.int64)):
                            extra_coord_axes = [int(extra_coord_axes[0])]
                        else:
                            extra_coord_axes = list(extra_coord_axes[0]).sort()
                    # If the extra coord is a quantity, convert to the correct unit.
                    if extra_coord_type is u.Quantity:
                        if unit_x_axis is None and extra_coord_type is u.Quantity:
                            unit_x_axis = seq[0].extra_coords[axis_extra_coord]["value"].unit
                        x_axis_coords = [x_axis_value.to(unit_x_axis).value
                                         for x_axis_value in x_axis_coords]
                    # If extra coord is same for each cube, storing
                    # values as single 1D axis range will suffice.
                    if ((np.array(x_axis_coords) == x_axis_coords[0]).all() and
                        (len(extra_coord_axes) == 1)):
                        x_axis_coords = x_axis_coords[0]
                    else:
                        if len(extra_coord_axes) != data_concat.ndim:
                            independent_axes = list(range(seq[0].data.ndim))
                            for i in list(extra_coord_axes)[::-1]:
                                independent_axes.pop(i)
                            x_axis_coords_copy = copy.deepcopy(x_axis_coords)
                            x_axis_coords = []
                            for i, x_axis_cube_coords in enumerate(x_axis_coords_copy):
                                tile_shape = tuple(list(
                                    np.array(seq[i].data.shape)[independent_axes]) + \
                                    [1]*len(x_axis_cube_coords))
                                x_axis_cube_coords = np.tile(x_axis_cube_coords, tile_shape)
                                # Since np.tile puts original array's dimensions as last,
                                # reshape x_axis_cube_coords to cube's shape.
                                x_axis_cube_coords = x_axis_cube_coords.reshape(seq[i].data.shape)
                                x_axis_coords.append(x_axis_cube_coords)
                        x_axis_coords = np.stack(x_axis_coords)
                # Set x-axis label.
                if xlabel is None:
                    xlabel = "{0} [{1}]".format(axis_extra_coord, unit_x_axis)
                # Re-enter x-axis values into axis_ranges
                axis_ranges[plot_axis_index] = x_axis_coords
        # Make label for y-axis.
        if ylabel is None:
            ylabel = "Data [{0}]".format(data_unit)

        super(LineAnimatorNDCubeSequence, self).__init__(
            data_concat, plot_axis_index=plot_axis_index, axis_ranges=axis_ranges,
            xlabel=xlabel, ylabel=ylabel, xlim=xlim, ylim=ylim, **kwargs)


class LineAnimatorCubeLikeNDCubeSequence(LineAnimator):
    """
    Animates N-dimensional data with the associated astropy WCS object.

    The following keyboard shortcuts are defined in the viewer:

    left': previous step on active slider
    right': next step on active slider
    top': change the active slider up one
    bottom': change the active slider down one
    'p': play/pause active slider

    This viewer can have user defined buttons added by specifying the labels
    and functions called when those buttons are clicked as keyword arguments.

    Parameters
    ----------
    seq: `ndcube.datacube.CubeSequence`
        The list of cubes.

    image_axes: `list`
        The two axes that make the image

    fig: `matplotlib.figure.Figure`
        Figure to use

    axis_ranges: list of physical coordinates for array or None
        If None array indices will be used for all axes.
        If a list it should contain one element for each axis of the numpy array.
        For the image axes a [min, max] pair should be specified which will be
        passed to :func:`matplotlib.pyplot.imshow` as extent.
        For the slider axes a [min, max] pair can be specified or an array the
        same length as the axis which will provide all values for that slider.
        If None is specified for an axis then the array indices will be used
        for that axis.

    interval: `int`
        Animation interval in ms

    colorbar: `bool`
        Plot colorbar

    button_labels: `list`
        List of strings to label buttons

    button_func: `list`
        List of functions to map to the buttons

    unit_x_axis: `astropy.units.Unit`
        The unit of x axis.

    unit_y_axis: `astropy.units.Unit`
        The unit of y axis.

    Extra keywords are passed to imshow.

    """
    def __init__(self, seq, plot_axis_index=None, axis_ranges=None, unit_x_axis=None,
                 data_unit=None, xlabel=None, ylabel=None, xlim=None, ylim=None, **kwargs):
        if plot_axis_index is None:
            plot_axis_index = -1
        #try:
        #    sequence_units, data_unit = _determine_sequence_units(seq.data, data_unit)
        #except ValueError:
        #    sequence_error = None
        # Form single cube of data from sequence.
        #if sequence_error is None:
        #    data_concat = np.concatenate([cube.data for i, cube in enumerate(seq.data)],
        #                                 axis=seq._common_axis))
        #else:
        #    data_concat = np.concatenate([(cube.data * sequence_units[i]).to(data_unit).value
        #                                  for i, cube in enumerate(seq.data)],
        #                                 axis=seq._common_axis)
        data_concat = np.concatenate([cube.data for i, cube in enumerate(seq.data)],
                                     axis=seq._common_axis)
        # Ensure plot_axis_index is represented in the positive convention.
        if plot_axis_index < 0:
            plot_axis_index = len(seq.cube_like_dimensions) + plot_axis_index
        # Calculate the x-axis values if axis_ranges not supplied.
        if axis_ranges is None:
            axis_ranges = [None] * len(seq.cube_like_dimensions)
            # Define unit of x-axis if not supplied by user.
            if unit_x_axis is None:
                wcs_plot_axis_index = utils.cube.data_axis_to_wcs_axis(
                    plot_axis_index, seq[0].missing_axis)
                unit_x_axis = np.asarray(
                    seq[0].wcs.wcs.cunit)[np.invert(seq[0].missing_axis)][wcs_plot_axis_index]
            if plot_axis_index == seq._common_axis:
                # Determine whether common axis is dependent.
                x_axis_coords = np.concatenate(
                    [cube.axis_world_coords(plot_axis_index).to(unit_x_axis).value
                    for cube in seq.data], axis=plot_axis_index)
                dependent_axes = utils.wcs.get_dependent_data_axes(
                    seq[0].wcs, plot_axis_index, seq[0].missing_axis)
                if len(dependent_axes) > 1:
                    independent_axes = list(range(data_concat.ndim))
                    for i in list(dependent_axes)[::-1]:
                        independent_axes.pop(i)
                    # Expand dimensionality of x_axis_cube_coords using np.tile
                    tile_shape = tuple(list(np.array(
                        data_concat.shape)[independent_axes]) + [1]*len(dependent_axes))
                    x_axis_coords = np.tile(x_axis_cube_coords, tile_shape)
                    # Since np.tile puts original array's dimensions as last,
                    # reshape x_axis_cube_coords to cube's shape.
                    x_axis_coords = x_axis_coords.reshape(seq.cube_like_dimensions.value)
            else:
                # Get x-axis values from each cube and combine into a single
                # array for axis_ranges kwargs.
                x_axis_coords = _get_non_common_axis_x_axis_coords(seq.data, plot_axis_index)
                axis_ranges[plot_axis_index] = np.concatenate(x_axis_coords, axis=seq._common_axis)
            # Set axis labels and limits, etc.
            if xlabel is None:
                xlabel = "{0} [{1}]".format(
                    seq.cube_like_world_axis_physical_types[plot_axis_index], unit_x_axis)
            if ylabel is None:
                ylabel = "Data [{0}]".format(data_unit)

        super(LineAnimatorCubeLikeNDCubeSequence, self).__init__(
            data_concat, plot_axis_index=plot_axis_index, axis_ranges=axis_ranges,
            xlabel=xlabel, ylabel=ylabel, xlim=xlim, ylim=ylim, **kwargs)


def _get_non_common_axis_x_axis_coords(seq_data, plot_axis_index):
    """Get coords of an axis from NDCubes and combine into single array."""
    x_axis_coords = []
    for i, cube in enumerate(seq_data):
        # Get the x-axis coordinates for each cube.
        #x_axis_cube_coords = cube.axis_world_coords(plot_axis_index).to(unit_x_axis).value
        x_axis_cube_coords = cube.axis_world_coords(plot_axis_index).value
        # If the returned x-values have fewer dimensions than the cube,
        # repeat the x-values through the higher dimensions.
        if x_axis_cube_coords.shape != cube.data.shape:
            # Get sequence axes dependent and independent of plot_axis_index.
            dependent_axes = utils.wcs.get_dependent_data_axes(
                cube.wcs, plot_axis_index, cube.missing_axis)
            independent_axes = list(range(len(cube.dimensions)))
            for i in list(dependent_axes)[::-1]:
                independent_axes.pop(i)
            # Expand dimensionality of x_axis_cube_coords using np.tile
            tile_shape = tuple(list(np.array(
                cube.data.shape)[independent_axes]) + [1]*len(dependent_axes))
            x_axis_cube_coords = np.tile(x_axis_cube_coords, tile_shape)
            # Since np.tile puts original array's dimensions as last,
            # reshape x_axis_cube_coords to cube's shape.
            x_axis_cube_coords = x_axis_cube_coords.reshape(cube.data.shape)
        x_axis_coords.append(x_axis_cube_coords)
    return x_axis_coords


def _determine_sequence_units(cubesequence_data, unit=None):
    """
    Returns units of cubes in sequence and derives data unit if not set.

    If not all cubes have their unit attribute set, an error is raised.

    Parameters
    ----------
    cubesequence_data: `list` of `ndcube.NDCube`
        Taken from NDCubeSequence.data attribute.

    unit: `astropy.units.Unit` or `None`
        If None, an appropriate unit is derived from first cube in sequence.

    Returns
    -------
    sequence_units: `list` of `astropy.units.Unit`
        Unit of each cube.

    unit: `astropy.units.Unit`
        If input unit is not None, then the same as input.  Otherwise it is
        the unit of the first cube in the sequence.

    """
    # Check that the unit attribute is set of all cubes.  If not, unit_y_axis
    try:
        sequence_units = np.array(_get_all_cube_units(cubesequence_data))
    except ValueError:
        sequence_units = None
    # If all cubes have unit set, create a data quantity from cube's data.
    if sequence_units is not None:
        if unit is None:
            unit = sequence_units[0]
    else:
        unit = None
    return sequence_units, unit


def _derive_1D_x_data(cubesequence, x_axis_values, unit_x_axis, sequence_is_1d=True):
    # Derive x data from wcs is extra_coord not set.
    if x_axis_values is None:
        if sequence_is_1d:
            # Since scalar NDCubes have no array/pixel indices, WCS translations don't work.
            # Therefore x-axis values will be unitless sequence indices unless supplied by user
            # or an extra coordinate is designated.
            unit_x_axis = None
            xdata = np.arange(int(cubesequence.dimensions[0].value))
            default_xlabel = "{0} [{1}]".format(cubesequence.world_axis_physical_types[0],
                                                unit_x_axis)
        else:
            if unit_x_axis is None:
                unit_x_axis = np.asarray(cubesequence[0].wcs.wcs.cunit)[
                    np.invert(cubesequence[0].missing_axis)][0]
            xdata = u.Quantity(np.concatenate([cube.axis_world_coords().to(unit_x_axis).value
                                               for cube in cubesequence]), unit=unit_x_axis)
            default_xlabel = "{0} [{1}]".format(cubesequence.cube_like_world_axis_physical_types[0],
                                                unit_x_axis)
    elif isinstance(x_axis_values, str):
        # Else derive x-axis from extra coord.
        if sequence_is_1d:
            xdata = cubesequence.sequence_axis_extra_coords[x_axis_extra_coord]
        else:
            xdata = cubesequence.common_axis_extra_coords[x_axis_extra_coord]
        if unit_x_axis is None and isinstance(xdata, u.Quantity):
            unit_x_axis = xdata.unit
        default_xlabel = "{0} [{1}]".format(x_axis_extra_coord, unit_x_axis)

    return xdata, unit_x_axis, default_xlabel


def _make_1D_sequence_plot(xdata, ydata, yerror, unit_y_axis, default_xlabel, kwargs):
    # Define plot settings if not set in kwargs.
    xlabel = kwargs.pop("xlabel", default_xlabel)
    ylabel = kwargs.pop("ylabel", "Data [{0}]".format(unit_y_axis))
    title = kwargs.pop("title", "")
    xlim = kwargs.pop("xlim", None)
    ylim = kwargs.pop("ylim", None)
    # Plot data
    fig, ax = plt.subplots(1, 1)
    ax.errorbar(xdata, ydata, yerror, **kwargs)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    return fig, ax


def _get_all_cube_units(sequence_data):
    """
    Return units of a sequence of NDCubes.

    Raises an error if any of the cube's don't have the unit attribute set.

    Parameters
    ----------
    sequence_data: iterable of `ndcube.NDCube` of `astropy.nddata.NDData`.

    Returns
    -------
    sequence_units: `list` of `astropy.units.Unit`
       The unit of each cube in the sequence.

    """
    sequence_units = []
    for i, cube in enumerate(sequence_data):
        if cube.unit is None:
            raise ValueError("{0}th cube in sequence does not have unit set.".format(i))
        else:
            sequence_units.append(cube.unit)
    return sequence_units


def _prep_axes_kwargs(naxis, plot_axis_indices, axes_coordinates, axes_units):
    """
    Checks input values are correct based on number of sequence dimensions and sets defaults.

    Parameters
    ----------
    plot_axis_indices: As for NDCubeSequencePlotMixin.plot or NDCubeSequencePlotMixin.plot_as_cube

    axes_coordinates: As for NDCubeSequencePlotMixin.plot or NDCubeSequencePlotMixin.plot_as_cube

    axes_units: As for NDCubeSequencePlotMixin.plot or NDCubeSequencePlotMixin.plot_as_cube

    Returns
    -------
    plot_axis_indices: None or `list` of `int` of length 1 or 2.

    axes_coordinates: `None` or `list` of `None` `astropy.units.Quantity` `numpy.ndarray` `str`
        Length of list equals number of sequence axes.

    axes_units: None or `list` of `None` `astropy.units.Unit` or `str`
        Length of list equals number of sequence axes.

    """
    # If plot_axis_indices, axes_coordinates, axes_units are not None and not lists,
    # convert to lists for consistent indexing behaviour.
    if (not isinstance(plot_axis_indices, list)) and (plot_axis_indices is not None):
        plot_axis_indices = [plot_axis_indices]
    if (not isinstance(axes_coordinates, list)) and (axes_coordinates is not None):
        axes_coordinates = [axes_coordinates]
    if (not isinstance(axes_units, list)) and (axes_units is not None):
        axes_units = [axes_units]
    # Set default value of plot_axis_indices if not set by user.
    if plot_axis_indices is None:
        plot_axis_indices = [-1, -2]
    # If number of sequence dimensions is greater than 1,
    # ensure length of plot_axis_indices is 1 or 2.
    # No need to check case where number of sequence dimensions is 1
    # as plot_axis_indices is ignored in that case.
    if naxis > 1:
        len(plot_axis_indices) not in [1, 2]:
            raise ValueError("plot_axis_indices can have at most length 2.")
        # If convention of axes_coordinates and axes_units being length of
        # plot_axis_index is being used, convert to convention where their
        # length equals sequence dimensions.  Only do this if number of dimensions if
        # greater than 1 as the conventions are equivalent if there is only one dimension.
        if axes_coordinates is not None:
            if len(axes_coordinates) == len(plot_axis_indices):
                none_axes_coordinates = np.array([None] * naxis)
                none_axes_coordinates[plot_axis_indices] = plot_axis_indices
                axes_coordinates = list(none_axes_coordinates)
        if axes_units is not None:
            if len(axes_units) == len(plot_axis_indices):
                none_axes_units = np.array([None] * naxis)
                none_axes_units[plot_axis_indices] = plot_axis_indices
                axes_units = list(none_axes_units)
    if axes_coordinates is not None:
        # Now axes_coordinates have been converted to a consistent convention,
        # ensure their length equals the number of sequence dimensions.
        len(axes_coordinates) != naxis:
            raise ValueError("length of axes_coordinates must be {0}.".format(naxis))
        # Ensure all elements in axes_coordinates are of correct types.
        ax_coord_types = (u.Quantity, np.ndarray, str)
        for axis_coordinate in axes_coordinates:
            if axis_coordinate is not None and not instance(axis_coordinate, ax_coord_types):
                raise TypeError("axes_coordinates must be one of {0} or list of {0}.".format(
                    [None] + list(ax_coord_types)))
    if axes_units is not None:
        # Now axes_units have been converted to a consistent convention,
        # ensure their length equals the number of sequence dimensions.
        if len(axes_units) != naxis:
            raise ValueError("length of axes_units must be {0}.".format(naxis))
        # Ensure all elements in axes_units are of correct types.
        ax_unit_types = (u.Unit, str)
        for axis_unit in axes_units:
            if axis_unit is not None and not instance(axis_unit, ax_unit_types):
                raise TypeError("axes_units must be one of {0} or list of {0}.".format(
                    ax_unit_types))

    return plot_axis_indices, axes_coordinates, axes_units


def _derive_1D_coordinates_and_units(axes_coordinates, axes_units):
    if axes_coordinates is None:
        x_axis_coordinates = axes_coordinates
    else:
        if not isinstance(axes_coordinates, list):
            axes_coordinates = [axes_coordinates]
        x_axis_coordinates = axes_coordinates[0]
    if axes_units is None:
        unit_x_axis = axes_units
    else:
        if not isinstance(axes_units, list):
            axes_units = [axes_units]
        unit_x_axis = axes_units[0]
    return x_axis_coordinates, unit_x_axis
