import streamlit as st
import numbers
import copy

# Syntactic sugar to make VegaLite more fun.
_ = dict

# TODO: Improve stack='columns' bar chart API
# TODO: If you don't pick an 'x' we use the 0th index
# TODO: If you don't pick a 'y' we use the 1st column (or all the columns??)
# TODO: Figure out why tooltip only shows on minimap
# TODO: Only send the columns that are actually used. (Same in all other charts)
# TODO: Ability to set x or y annotations

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


def _maybe_melt(data, x, y, color, legend):
    if color:
        # Dataframe is already in long format.
        value_enc = _clean_encoding(data, y)
        variable_enc = _clean_encoding(data, color, legend=_get_legend_dict(legend))

    else:
        # Dataframe is in wide format. Need to convert to long format for Vega-Lite.
        id_vars = [x]
        value_vars = _as_list_like(y)

        if len(value_vars) == 1:
            value_enc = _clean_encoding(data, value_vars[0])
            variable_enc = None

        else:
            data = data.melt(id_vars=id_vars, value_vars=value_vars)
            data['variable'] = data['variable'].astype('string')

            value_enc = _clean_encoding(data, 'value', title=None)
            variable_enc = _(field='variable', title=None, legend=_get_legend_dict(legend))

    return data, value_enc, variable_enc


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


def line(
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
        Column name to use for the x axis, or Vega-Lite encoding dict for the x axis.
    y : str or list of str or dict
        Column name to use for the y axis, or Vega-Lite encoding dict for the y axis.
        If a list of strings, draws several lines on the same chart. This is only useful for
        long-format tables; for wide-format tables, use color parameter instead.
    color : str or dict
        Column name to use for chart colors, or Vega-Lite encoding dict for color values.
        This is only useful for wide-format tables; for long-format tables, pass a list to the
        y parameter instead.
    opacity : number or str or dict or None
        Value to use for the opacity, or column name, or Vega-Lite encoding dict.
        If None, opacity is left unspecified (meaning full opacity).
    width : number or None
        Chart width. See also, use_container_width.
    height : number or None
        Chart height.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. If None, draws the legend at Vega-Lite's default (i.e. 'right'). To hide, use
        'disable'.
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
    data, y_enc, color_enc = _maybe_melt(data, x, y, color, legend)

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


def area(
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
    data, y_enc, color_enc = _maybe_melt(data, x, y, color, legend)

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


def bar(
        data,
        bars,
        values,
        color=None,
        opacity=None,
        stack='columns',
        direction='vertical',
        width=None,
        height=None,
        title=None,
        legend=None,
        pan_zoom=None,
        use_container_width=False,
    ):
    x_enc = _clean_encoding(data, bars, title=None)
    values = _as_list_like(values)
    data, y_enc, color_enc = _maybe_melt(data, bars, values, color, legend)

    column_enc = None

    if not stack:
        y_enc['stack'] = None
    elif stack is True:
        y_enc['stack'] = 'zero'
    elif stack is 'columns':
        if (len(values) > 1 or color):
            column_enc = x_enc
            column_enc['spacing'] = 10
            x_enc = color_enc
    else:
        y_enc['stack'] = stack

    if direction == 'horizontal':
        x_enc, y_enc = y_enc, x_enc
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


def scatter(
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



def pie(
        data,
        theta,
        color,
        width=None,
        height=None,
        title=None,
        legend=None,
        use_container_width=True,
    ):

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


def donut(
        data,
        theta,
        color,
        width=None,
        height=None,
        title=None,
        legend=None,
        use_container_width=True,
    ):

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
            x=_(field=date, timeUnit=x_unit, title=None),
            y=_(field=date, timeUnit=y_unit, title=None),
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
