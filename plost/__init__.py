"""🍅 Plost

A deceptively simple plotting library for Streamlit.
You've been writing plots wrong all this time!
"""
import streamlit as st
import numbers
import copy

# Syntactic sugar to make VegaLite more fun.
_ = dict

def _clean_encoding(data, enc, **kwargs):
    if isinstance(enc, str):
        if 'type' in kwargs:
            enc_type = kwargs['type']
        else:
            enc, enc_type = _guess_string_encoding_type(data, enc)

    # Re-check because _guess_string_encoding_type can return a different type of enc.
    if isinstance(enc, str):
        enc = _(
            field=enc,
            type=kwargs.get('type', enc_type),
        )
        enc.update(kwargs)
        return enc

    elif isinstance(enc, numbers.Number):
        enc = _(value=enc)
        enc.update(kwargs)
        return enc

    elif isinstance(enc, dict):
        kwargs.update(enc)
        return kwargs

    return kwargs


def _guess_string_encoding_type(data, enc):
    # Accept Altair-style shorthands.
    if enc.endswith(':Q'):
        return enc[:-2], 'quantitative'
    elif enc.endswith(':O'):
        return enc[:-2], 'ordinal'
    elif enc.endswith(':N'):
        return enc[:-2], 'nominal'
    elif enc.endswith(':T'):
        return enc[:-2], 'temporal'
    elif enc.endswith(':G'):
        return enc[:-2], 'geojson'

    try:
        dtype = data[enc].dtype.name
    except KeyError:
        # If it's not a column, then maybe it's a value.
        return _(value=enc), None

    if dtype in {'object', 'string', 'bool', 'categorical'}:
        return enc, 'nominal'
    elif dtype in {'float64', 'float32', 'int64', 'int32', 'int8', 'string'}:
        return enc, 'quantitative'
    elif dtype.startswith('datetime64'):
        return enc, 'temporal'

    return enc, None


VAR_NAME = 'variable' # Singular because it makes tooltips nicer
VALUE_NAME = 'value' # Singular because it makes tooltips nicer

def _maybe_melt(data, x, y, legend):
    melted = False

    # Dataframe is in wide format. Need to convert to long format for Vega-Lite.
    id_vars = [x]
    value_vars = _as_list_like(y)

    if len(value_vars) == 1:
        value_enc = _clean_encoding(data, value_vars[0])
        variable_enc = None

    else:
        if VAR_NAME in data.columns:
            raise TypeError(f'Data already contains a column called {VAR_NAME}')
        if VALUE_NAME in data.columns:
            raise TypeError(f'Data already contains a column called {VALUE_NAME}')

        data = data.melt(
            id_vars=id_vars, value_vars=value_vars, var_name=VAR_NAME, value_name=VALUE_NAME)
        data[VAR_NAME] = data[VAR_NAME].astype('string')

        value_enc = _clean_encoding(data, VALUE_NAME, title=None)
        variable_enc = _(field=VAR_NAME, title=None, legend=_get_legend_dict(legend))
        melted = True

    return melted, data, value_enc, variable_enc


def _as_list_like(x):
    if isinstance(x, list):
        return x

    elif isinstance(x, tuple):
        return x

    return [x]


def _get_selection(pan_zoom):
    if pan_zoom is None or pan_zoom == 'minimap':
        return None

    selection = _(
        type='interval',
        bind='scales',
    )

    if pan_zoom == 'pan':
        selection['zoom'] = False

    if pan_zoom == 'zoom':
        selection['translate'] = False

    return _(foo=selection)


def _get_legend_dict(legend):
    if legend == 'disable':
        return _(disable=True)
    return _(orient=legend)


_MINI_CHART_SIZE = 50


def _add_minimap(orig_spec, encodings, location, filter=False):
    inner_props = {'mark', 'encoding', 'selection', 'width', 'height'}

    inner_spec = {k: v for (k, v) in orig_spec.items() if k in inner_props}
    outer_spec = {k: v for (k, v) in orig_spec.items() if k not in inner_props}

    minimap_spec = copy.deepcopy(inner_spec)

    is_2d = False

    if len(encodings) == 2:
        is_2d = True

    if location in {'bottom', 'top'}:
        if not is_2d:
            minimap_spec['height'] = _MINI_CHART_SIZE
        minimap_spec['encoding']['y']['title'] = None
        minimap_spec['encoding']['y']['axis'] = None

    if filter:
        minimap_spec['encoding']['y']['title'] = None
        minimap_spec['encoding']['y']['axis'] = None
        minimap_spec['encoding']['x']['title'] = None
        minimap_spec['encoding']['x']['axis'] = None

    if location == 'right':
        if not is_2d:
            minimap_spec['width'] = _MINI_CHART_SIZE
        minimap_spec['height'] = _MINI_CHART_SIZE * 5
        minimap_spec['encoding']['x']['title'] = None
        minimap_spec['encoding']['x']['axis'] = None

    if is_2d:
        minimap_spec['height'] //= 2
        minimap_spec['width'] //= 2
        minimap_spec['encoding']['x']['title'] = None
        minimap_spec['encoding']['x']['axis'] = None
        minimap_spec['encoding']['y']['title'] = None
        minimap_spec['encoding']['y']['axis'] = None

    minimap_spec['selection'] = _(
        brush=_(type='interval', encodings=encodings),
    )

    if filter:
        # Filter data out according to the brush.
        inner_spec['transform'] = [_(filter=_(selection='brush'))]
    else:
        # Change the scale of differen encodings according to the brush.
        for k in encodings:
            enc = inner_spec['encoding'][k]
            enc['scale'] = enc.get('scale', {})
            enc['scale']['domain'] = _(selection='brush', encoding=k)
            enc['title'] = None

    if location == 'right':
        outer_spec['hconcat'] = [inner_spec, minimap_spec]
    elif location == 'top':
        outer_spec['vconcat'] = [minimap_spec, inner_spec]
    else:
        outer_spec['vconcat'] = [inner_spec, minimap_spec]

    return outer_spec


def line_chart(
        data,
        x,
        y,
        color=None,
        opacity=None,
        width=None,
        height=None,
        title=None,
        legend=None,
        pan_zoom='both',
        use_container_width=True,
    ):
    """Draw a line chart.

    Parameters
    ----------
    data : DataFrame
    x : str or dict
        Column name to use for the x axis, or Vega-Lite dict for the x encoding.
    y : str or list of str or dict
        Column name to use for the y axis, or Vega-Lite dict for the y encoding.
        If a list of strings, draws several series on the same chart by melting your wide-format
        table into a long-format table behind the scenes. If your table is already in long-format,
        the way to draw multiple series is by using the color parameter instead.
    color : str or dict or None
        Column name to use for chart colors, or Vega-Lite dict for the color encoding.
        May also be a literal value, like "#223344" or "green".
        None means the default color will be used.
    opacity : number or str or dict or None
        Value to use for the opacity, or column name, or Vega-Lite encoding dict.
        None means the default opacity (1.0) will be used.
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. If None, draws the legend at default location. To hide, use 'disable'.
    pan_zoom : str or None
        Specify the method for panning and zooming the chart, if any. Allowed values:
        - 'both': drag canvas to pan, use scroll with mouse to zoom.
        - 'pan': drag canvas to pan.
        - 'zoom': scroll with mouse to zoom.
        - 'minimap': drag onto minimap to select viewport area.
        - None: chart will not be pannable/zoomable.
    use_container_width : bool
        If True, sets the chart to use all available space. This takes precedence over the width
        parameter.
    """
    melted, data, y_enc, color_enc = _maybe_melt(data, x, y, legend)

    if color:
        color_enc = _clean_encoding(data, color)

    spec = _(
        data=data,
        mark=_(type='line', tooltip=True),
        width=width,
        height=height,
        title=title,
        encoding=_(
            x=_clean_encoding(data, x),
            y=y_enc,
            color=color_enc,
            opacity=_clean_encoding(data, opacity),
        ),
        selection=_get_selection(pan_zoom),
    )

    if pan_zoom == 'minimap':
        spec = _add_minimap(spec, ['x'], 'bottom')

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def area_chart(
        data,
        x,
        y,
        color=None,
        opacity=None,
        stack=True,
        width=None,
        height=None,
        title=None,
        legend=None,
        pan_zoom='both',
        use_container_width=True,
    ):
    """Draw an area chart.

    Parameters
    ----------
    data : DataFrame
    x : str or dict
        Column name to use for the x axis, or Vega-Lite dict for the x encoding.
    y : str or list of str or dict
        Column name to use for the y axis, or Vega-Lite dict for the y encoding.
        If a list of strings, draws several series on the same chart by melting your wide-format
        table into a long-format table behind the scenes. If your table is already in long-format,
        the way to draw multiple series is by using the color parameter instead.
    color : str or dict or None
        Column name to use for chart colors, or Vega-Lite dict for the color encoding.
        May also be a literal value, like "#223344" or "green".
        None means the default color will be used.
    opacity : number or str or dict or None
        Value to use for the opacity, or column name, or Vega-Lite encoding dict.
        None means the default opacity (1.0) will be used.
    stack : bool or str
        True means areas of different colors will be stacked. False means there will be no
        stacking, A Vega-Lite stack spec like 'normalized' is also accepted.
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. If None, draws the legend at default location. To hide, use 'disable'.
    pan_zoom : str or None
        Specify the method for panning and zooming the chart, if any. Allowed values:
        - 'both': drag canvas to pan, use scroll with mouse to zoom.
        - 'pan': drag canvas to pan.
        - 'zoom': scroll with mouse to zoom.
        - 'minimap': drag onto minimap to select viewport area.
        - None: chart will not be pannable/zoomable.
    use_container_width : bool
        If True, sets the chart to use all available space. This takes precedence over the width
        parameter.
    """
    melted, data, y_enc, color_enc = _maybe_melt(data, x, y, legend)

    if color:
        color_enc = _clean_encoding(data, color)

    if stack is not None:
        if stack is True:
            y_enc['stack'] = 'zero'
        else:
            y_enc['stack'] = stack

    spec = _(
        data=data,
        mark=_(type='area', tooltip=True),
        width=width,
        height=height,
        title=title,
        encoding=_(
            x=_clean_encoding(data, x),
            y=y_enc,
            color=color_enc,
            opacity=_clean_encoding(data, opacity),
        ),
        selection=_get_selection(pan_zoom),
    )

    if pan_zoom == 'minimap':
        spec = _add_minimap(spec, ['x'], 'bottom')

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def bar_chart(
        data,
        bar,
        value,
        color=None,
        opacity=None,
        group=None,
        stack=True,
        direction='vertical',
        width=None,
        height=None,
        title=None,
        legend=None,
        pan_zoom=None,
        use_container_width=False,
    ):
    """Draw a bar chart.

    Parameters
    ----------
    data : DataFrame
    bar : str or dict
        Column name to use for the domain axis, or Vega-Lite dict for x/y encoding.
    value : str or list of str or dict
        Column name to use for the codomain axis, or Vega-Lite dict for the x/y encoding.  If a list
        of strings, draws several series on the same chart by melting your wide-format table into a
        long-format table behind the scenes. If your table is already, the way to draw multiple
        series is by using the color or group parameters instead.
    color : str or dict or None
        Column name to use for chart colors, or Vega-Lite dict for the color encoding.
        May also be a literal value, like "#223344" or "green".
        None means the default color will be used.
    opacity : number or str or dict or None
        Value to use for the opacity, or column name, or Vega-Lite encoding dict.
        None means the default opacity (1.0) will be used.
    group : str or dict or None
        Column name to use for grouping bars, or Vega-Lite dict for column/row encoding.
        If None, no bars will be grouped.
    stack : bool or str
        True means areas of different colors will be stacked. False means there will be no
        stacking, A Vega-Lite stack spec like 'normalized' is also accepted.
    direction : str
        Specifies the orientation of the bars in the chart: 'vertical' or 'horizontal'.
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. If None, draws the legend at default location. To hide, use 'disable'.
    pan_zoom : str or None
        Specify the method for panning and zooming the chart, if any. Allowed values:
        - 'both': drag canvas to pan, use scroll with mouse to zoom.
        - 'pan': drag canvas to pan.
        - 'zoom': scroll with mouse to zoom.
        - 'minimap': drag onto minimap to select viewport area.
        - None: chart will not be pannable/zoomable.
    use_container_width : bool
        If True, sets the chart to use all available space. This takes precedence over the width
        parameter.
    """
    x_enc = _clean_encoding(data, bar, title=None)
    value = _as_list_like(value)
    melted, data, y_enc, color_enc = _maybe_melt(data, bar, value, legend)

    if color:
        if color == 'value': # 'value', as in the value= arg.
            color = VAR_NAME
        color_enc = _clean_encoding(data, color)

    column_enc = None
    row_enc = None

    if group:
        if group is True:
            if not melted:
                raise Exception("bar(..., group=True) requires wide-mode data.")
            column_enc = x_enc
            x_enc = color_enc
        else:
            if group == 'value': # 'value', as in the value= arg.
                group = VAR_NAME
            column_enc = _clean_encoding(data, group, title=None)

        column_enc['spacing'] = 10

    if stack:
        if stack is True:
            y_enc['stack'] = 'zero'

        else:
            y_enc['stack'] = stack

    if direction == 'horizontal':
        x_enc, y_enc = y_enc, x_enc
        row_enc, column_enc = column_enc, row_enc
        use_container_width = True

    spec = _(
        data=data,
        mark=_(type='bar', tooltip=True),
        width=width,
        height=height,
        title=title,
        encoding=_(
            x=x_enc,
            y=y_enc,
            color=color_enc,
            opacity=_clean_encoding(data, opacity),
            column=column_enc,
            row=row_enc,
        ),
    )

    if pan_zoom == 'minimap':
        if direction == 'horizontal':
            enc = ['y']
            loc = 'right'
        else:
            enc = ['x']
            loc = 'top'

        spec = _add_minimap(spec, enc, loc, filter=True)

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def scatter_chart(
        data,
        x,
        y,
        color=None,
        size=None,
        opacity=None,
        width=None,
        height=None,
        title=None,
        legend=None,
        pan_zoom='both',
        use_container_width=True,
    ):
    """Draw a scatter-plot chart.

    Parameters
    ----------
    data : DataFrame
    x : str or dict
        Column name to use for the x axis, or Vega-Lite dict for the x encoding.
    y : str or list of str or dict
        Column name to use for the y axis, or Vega-Lite dict for the y encoding.
        If a list of strings, draws several series on the same chart by melting your wide-format
        table into a long-format table behind the scenes. If your table is already in long-format,
        the way to draw multiple lines is by using the color parameter instead.
    color : str or dict or None
        Column name to use for chart colors, or Vega-Lite dict for the color encoding.
        May also be a literal value, like "#223344" or "green".
        None means the default color will be used.
    size : str or dict or None
        Column name to use for the size of plotted datapoints, or Vega-Lite dict for the size
        encoding. May also be a literal value, like 10.
        None means the default size will be used.
    opacity : number or str or dict or None
        Value to use for the opacity, or column name, or Vega-Lite encoding dict.
        None means the default opacity (1.0) will be used.
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. If None, draws the legend at default location. To hide, use 'disable'.
    pan_zoom : str or None
        Specify the method for panning and zooming the chart, if any. Allowed values:
        - 'both': drag canvas to pan, use scroll with mouse to zoom.
        - 'pan': drag canvas to pan.
        - 'zoom': scroll with mouse to zoom.
        - 'minimap': drag onto minimap to select viewport area.
        - None: chart will not be pannable/zoomable.
    use_container_width : bool
        If True, sets the chart to use all available space. This takes precedence over the width
        parameter.
    """
    # TODO Melt

    spec = _(
        data=data,
        mark=_(type='circle', tooltip=True),
        width=width,
        height=height,
        title=title,
        encoding=_(
            x=_clean_encoding(data, x),
            y=_clean_encoding(data, y),
            color=_clean_encoding(data, color, legend=_get_legend_dict(legend)),
            size=_clean_encoding(data, size),
            opacity=_clean_encoding(data, opacity),
        ),
        selection=_get_selection(pan_zoom),
    )

    if pan_zoom == 'minimap':
        spec = _add_minimap(spec, ['x', 'y'], 'bottom')

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def _pie_spec(
        data,
        theta,
        color,
        width=None,
        height=None,
        title=None,
        legend=None,
    ):
    return _(
        data=data,
        mark=_(type='arc', tooltip=True),
        width=width,
        height=height,
        title=title,
        view=_(stroke=None),
        encoding=_(
            theta=_clean_encoding(data, theta),
            color=_clean_encoding(data, color, title=None, legend=_get_legend_dict(legend)),
        ),
    )



def pie_chart(
        data,
        theta,
        color,
        width=None,
        height=None,
        title=None,
        legend=None,
        use_container_width=True,
    ):
    """Draw a pie chart.

    Parameters
    ----------
    data : DataFrame
    theta : str or dict
        Column name to use for the angle of the pie slices, or Vega-Lite dict for the theta
        encoding.
    color : str or dict or None
        Column name to use for chart colors, or Vega-Lite dict for the color encoding.
        May also be a literal value, like "#223344" or "green".
        None means the default color will be used.
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. If None, draws the legend at default location. To hide, use 'disable'.
    use_container_width : bool
        If True, sets the chart to use all available space. This takes precedence over the width
        parameter.
    """

    spec = _pie_spec(
        data,
        theta,
        color,
        width,
        height,
        title,
        legend,
    )

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def donut_chart(
        data,
        theta,
        color,
        width=None,
        height=None,
        title=None,
        legend=None,
        use_container_width=True,
    ):
    """Draw a pie chart.

    Parameters
    ----------
    data : DataFrame
    theta : str or dict
        Column name to use for the angle of the pie slices, or Vega-Lite dict for the theta
        encoding.
    color : str or dict or None
        Column name to use for chart colors, or Vega-Lite dict for the color encoding.
        May also be a literal value, like "#223344" or "green".
        None means the default color will be used.
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. If None, draws the legend at default location. To hide, use 'disable'.
    use_container_width : bool
        If True, sets the chart to use all available space. This takes precedence over the width
        parameter.
    """

    spec = _pie_spec(
        data,
        theta,
        color,
        width,
        height,
        title,
        legend,
    )

    if height:
        innerRadius = height // 4
    else:
        innerRadius = 50 # Default height is 200 in Streamlit's Vega-Lite element.

    spec['mark']['innerRadius'] = innerRadius

    st.vega_lite_chart(spec, use_container_width=use_container_width)


# Data must be in long format.
def event_chart(
        data,
        x,
        y,
        color=None,
        size=None,
        opacity=0.5,
        thickness=2,
        width=None,
        height=None,
        title=None,
        legend=None,
        pan_zoom='both',
        use_container_width=True,
    ):
    """Draw a line chart.

    Parameters
    ----------
    data : DataFrame
    x : str or dict
        Column name to use for the x axis, or Vega-Lite dict for the x encoding.
    y : str or list of str or dict
        Column name to use for the y axis, or Vega-Lite dict for the y encoding.
        If a list of strings, draws several series on the same chart by melting your wide-format
        table into a long-format table behind the scenes. If your table is already in long-format,
        the way to draw multiple series is by using the color parameter instead.
    color : str or dict or None
        Column name to use for chart colors, or Vega-Lite dict for the color encoding.
        May also be a literal value, like "#223344" or "green".
        None means the default color will be used.
    size : number or str or dict or None
        Column name to use for chart sizes, or Vega-Lite dict for the size encoding.
        May also be a literal value, like 123. None means the size will be inferred.
    opacity : number or str or dict or None
        Value to use for the opacity, or column name, or Vega-Lite encoding dict.
        None means the default opacity (1.0) will be used.
    thickness : number or str or dict
        The thickness of the tick marks in the chart.
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. If None, draws the legend at default location. To hide, use 'disable'.
    pan_zoom : str or None
        Specify the method for panning and zooming the chart, if any. Allowed values:
        - 'both': drag canvas to pan, use scroll with mouse to zoom.
        - 'pan': drag canvas to pan.
        - 'zoom': scroll with mouse to zoom.
        - 'minimap': drag onto minimap to select viewport area.
        - None: chart will not be pannable/zoomable.
    use_container_width : bool
        If True, sets the chart to use all available space. This takes precedence over the width
        parameter.
    """

    spec = _(
        data=data,
        mark=_(type='tick', tooltip=True, thickness=thickness),
        width=width,
        height=height,
        title=title,
        encoding=_(
            x=_clean_encoding(data, x),
            y=_clean_encoding(data, y),
            color=_clean_encoding(data, color, legend=_get_legend_dict(legend)),
            size=_clean_encoding(data, size),
            opacity=_clean_encoding(data, opacity),
        ),
        selection=_get_selection(pan_zoom),
    )

    if pan_zoom == 'minimap':
        spec = _add_minimap(spec, ['x'], 'bottom')

    st.vega_lite_chart(spec, use_container_width=use_container_width)




def time_hist(
        data,
        date,
        x_unit,
        y_unit,
        color=None,
        aggregate='count',
        width=None,
        height=None,
        title=None,
        legend=None,
        pan_zoom=None,
        use_container_width=True,
    ):

    spec = _(
        data=data,
        mark=_(type='rect', tooltip=True),
        width=width,
        height=height,
        title=title,
        encoding=_(
            x=_(field=date, type='ordinal', timeUnit=x_unit, title=None, axis=_(tickBand='extent')),
            y=_(field=date, type='ordinal', timeUnit=y_unit, title=None, axis=_(tickBand='extent')),
            color=_clean_encoding(data, color, aggregate=aggregate, legend=legend)
        ),
        selection=_get_selection(pan_zoom),
    )

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def xy_hist(
        data,
        x,
        y,
        color=None,
        aggregate='count',
        x_bin=True,
        y_bin=True,
        width=None,
        height=None,
        title=None,
        legend=None,
        pan_zoom=None,
        use_container_width=True,
    ):

    spec = _(
        data=data,
        mark=_(type='rect', tooltip=True),
        width=width,
        height=height,
        title=title,
        encoding=_(
            x=_clean_encoding(data, x, bin=x_bin),
            y=_clean_encoding(data, y, bin=y_bin),
            color=_clean_encoding(data, color, aggregate=aggregate, legend=legend)
        ),
        selection=_get_selection(pan_zoom),
    )

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def hist(
        data,
        x,
        y=None,
        aggregate='count',
        bin=True,
        width=None,
        height=None,
        title=None,
        legend=None,
        pan_zoom=None,
        use_container_width=True,
    ):

    spec = _(
        data=data,
        mark=_(type='bar', tooltip=True),
        width=width,
        height=height,
        title=title,
        encoding=_(
            x=_clean_encoding(data, x, bin=bin),
            y=_clean_encoding(data, y, aggregate=aggregate),
        ),
        selection=_get_selection(pan_zoom),
    )

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def scatter_hist(
        data,
        x,
        y,
        color=None,
        size=None,
        opacity=None,
        aggregate='count',
        x_bin=True,
        y_bin=True,
        width=None,
        height=None,
        title=None,
        legend=None,
        pan_zoom=None,
        use_container_width=True,
    ):

    scatter_spec = _(
        mark=_(type='circle', tooltip=True),
        width=width,
        height=height,
        title=title,
        encoding=_(
            x=_clean_encoding(data, x),
            y=_clean_encoding(data, y),
            color=_clean_encoding(data, color, legend=_get_legend_dict(legend)),
            size=_clean_encoding(data, size),
            opacity=_clean_encoding(data, opacity),
        ),
    )

    x_hist_spec = _(
        mark=_(type='bar', tooltip=True),
        width=width,
        height=_MINI_CHART_SIZE,
        encoding=_(
            x=_clean_encoding(data, x, bin=x_bin, title=None, axis=None),
            y=_clean_encoding(data, y, aggregate=aggregate, title=None),
        ),
    )

    y_hist_spec = _(
        mark=_(type='bar', tooltip=True),
        height=height,
        width=_MINI_CHART_SIZE,
        encoding=_(
            x=_clean_encoding(data, x, aggregate=aggregate, title=None),
            y=_clean_encoding(data, y, bin=y_bin, title=None, axis=None),
        ),
    )

    spec = _(
        data=data,
        title=title,
        vconcat=[x_hist_spec, _(hconcat=[scatter_spec, y_hist_spec])],
    )

    st.vega_lite_chart(spec, use_container_width=use_container_width)
