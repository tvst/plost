"""Plost

A deceptively simple plotting library for Streamlit.
You've been writing *plots* wrong all this time!
"""
import copy
import numbers
import streamlit as st

# Syntactic sugar to make VegaLite more fun.
D = dict

def _clean_encoding(data, enc, **kwargs):
    if isinstance(enc, str):
        if 'type' in kwargs:
            enc_type = kwargs['type']
        else:
            enc, enc_type = _guess_string_encoding_type(data, enc)

    # Re-check because _guess_string_encoding_type can return a different type of enc.
    if isinstance(enc, str):
        enc = D(
            field=enc,
            type=kwargs.get('type', enc_type),
        )
        enc.update(kwargs)
        return enc

    elif isinstance(enc, numbers.Number):
        enc = D(value=enc)
        enc.update(kwargs)
        return enc

    elif isinstance(enc, dict):
        kwargs.update(enc)
        return kwargs

    return kwargs


# Accept Altair-style shorthands.
SUFFIX_TO_ENCODING = {
    ':Q': 'quantitative',
    ':O': 'ordinal',
    ':N': 'nominal',
    ':T': 'temporal',
    ':G': 'geojson',
}


def _split_encoding_suffix(enc):
    if isinstance(enc, str) and len(enc) > 2:
        enc_suffix = enc[-2:]

        if enc_suffix in SUFFIX_TO_ENCODING:
            enc_prefix = enc[:-2]
            return enc_prefix, SUFFIX_TO_ENCODING[enc_suffix]

    return enc, None

def _guess_string_encoding_type(data, enc):
    enc_prefix, enc_type = _split_encoding_suffix(enc)
    if enc_type:
        return enc_prefix, enc_type

    try:
        dtype = data[enc].dtype.name
    except KeyError:
        # If it's not a column, then maybe it's a value.
        return D(value=enc), None

    if dtype in {'object', 'string', 'bool', 'categorical'}:
        return enc, 'nominal'
    elif dtype in {'float64', 'float32', 'int64', 'int32', 'int8', 'string'}:
        return enc, 'quantitative'
    elif dtype.startswith('datetime64'):
        return enc, 'temporal'

    return enc, None


VAR_NAME = 'variable' # Singular because it makes tooltips nicer
VALUE_NAME = 'value' # Singular because it makes tooltips nicer


def _maybe_melt(data, x, y, legend, *columns_to_keep):
    melted = False
    variable_enc = None

    # We can only melt if you're not passing a complex spec into x or y.
    if isinstance(x, dict) or isinstance(y, dict):
        value_enc = _clean_encoding(data, y)

    # Check if dataframe is already in long format. If so, nothing to do!
    elif isinstance(y, str):
        value_enc = _clean_encoding(data, y)

    else:
        # Dataframe is in wide format. Lets melt it into long format for Vega-Lite.
        x_prefix, _ = _split_encoding_suffix(x)
        id_vars = _as_list_like(x_prefix)
        value_vars = _as_list_like(y)

        id_vars = list(id_vars) + list(c for c in columns_to_keep if c in data.columns)

        if VAR_NAME in data.columns:
            raise TypeError(f'Data already contains a column called {VAR_NAME}')
        if VALUE_NAME in data.columns:
            raise TypeError(f'Data already contains a column called {VALUE_NAME}')

        data = data.melt(
            id_vars=id_vars, value_vars=value_vars, var_name=VAR_NAME, value_name=VALUE_NAME)

        # Don't show titles in axes since they're no longer the original names and make no sense to
        # the user.
        value_enc = _clean_encoding(data, VALUE_NAME, title=None)
        variable_enc = D(field=VAR_NAME, title=None, legend=legend)
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

    selection = D(
        type='interval',
        bind='scales',
    )

    if pan_zoom == 'pan':
        selection['zoom'] = False

    if pan_zoom == 'zoom':
        selection['translate'] = False

    return D(foo=selection)


def _get_legend_dict(legend):
    if legend is None:
        return D(disable=True)
    return D(orient=legend)


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

    minimap_spec['selection'] = D(
        brush=D(type='interval', encodings=encodings),
    )

    if filter:
        # Filter data out according to the brush.
        inner_spec['transform'] = [D(filter=D(selection='brush'))]
    else:
        # Change the scale of differen encodings according to the brush.
        for k in encodings:
            enc = inner_spec['encoding'][k]
            enc['scale'] = enc.get('scale', {})
            enc['scale']['domain'] = D(selection='brush', encoding=k)
            enc['title'] = None

    if location == 'right':
        outer_spec['hconcat'] = [inner_spec, minimap_spec]
    elif location == 'top':
        outer_spec['vconcat'] = [minimap_spec, inner_spec]
    else:
        outer_spec['vconcat'] = [inner_spec, minimap_spec]

    return outer_spec


def _add_annotations(spec, x_annot, y_annot):
    annotation_layers = []

    _add_encoding_annotations(annotation_layers, 'x', x_annot)
    _add_encoding_annotations(annotation_layers, 'y', y_annot)

    if annotation_layers:
        spec = D(
            layer=[
                spec,
                *annotation_layers,
            ]
        )

    return spec


def _add_encoding_annotations(annotation_layers, encoding, annot):
    if not annot:
        return

    if isinstance(annot, dict):
        annot_iter = annot.items()
    else:
        annot_iter = ((coord, "") for coord in _as_list_like(annot))

    for coord, label in annot_iter:
        annotation_layers.append(D(
            mark='rule',
            encoding={
                encoding: D(datum=coord),
                "tooltip": D(value=f'{label} ({coord})'),
            },
        ))


def line_chart(
        data,
        x,
        y,
        color=None,
        opacity=None,
        x_annot=None,
        y_annot=None,
        width=None,
        height=None,
        title=None,
        legend='bottom',
        pan_zoom='both',
        use_container_width=True,
    ):
    """Draw a line chart.

    Parameters
    ----------
    data : DataFrame
    x : str or dict
        Column name to use for the x axis, or Vega-Lite dict for the x encoding.
        See https://vega.github.io/vega-lite/docs/encoding.html#position-datum-def.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    y : str or list of str or dict
        Column name to use for the y axis, or Vega-Lite dict for the y encoding.
        If a list of strings, draws several series on the same chart by melting your wide-format
        table into a long-format table behind the scenes. If your table is already in long-format,
        the way to draw multiple series is by using the color parameter instead.
        See https://vega.github.io/vega-lite/docs/encoding.html#position-datum-def.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    color : str or dict or None
        Column name to use for chart colors, or Vega-Lite dict for the color encoding.
        May also be a literal value, like "#223344" or "green".
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    opacity : number or str or dict or None
        Value to use for the opacity, or column name, or Vega-Lite encoding dict.
        None means the default opacity (1.0) will be used.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    x_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific X-axis values.
        Can be specified as a dict or a list:
            - list style: [x_value_1, x_value_2, ...]
            - dict style: {x_value_1: label_1, x_value_2: label_2, ...}
    y_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific Y-axis values.
        Can be specified as a dict or a list:
            - list style: [y_value_1, y_value_2, ...]
            - dict style: {y_value_1: label_1, y_value_2: label_2, ...}
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. To hide, use None.
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
    legend = _get_legend_dict(legend)
    melted, data, y_enc, color_enc = _maybe_melt(data, x, y, legend, opacity)

    if color:
        color_enc = _clean_encoding(data, color, legend=legend)

    meta = D(
        data=data,
        width=width,
        height=height,
        title=title,
    )

    spec = D(
        mark=D(type='line', tooltip=True),
        encoding=D(
            x=_clean_encoding(data, x),
            y=y_enc,
            color=color_enc,
            opacity=_clean_encoding(data, opacity),
        ),
        selection=_get_selection(pan_zoom),
    )

    spec = _add_annotations(spec, x_annot, y_annot)
    spec.update(meta)

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
        x_annot=None,
        y_annot=None,
        width=None,
        height=None,
        title=None,
        legend='bottom',
        pan_zoom='both',
        use_container_width=True,
    ):
    """Draw an area chart.

    Parameters
    ----------
    data : DataFrame
    x : str or dict
        Column name to use for the x axis, or Vega-Lite dict for the x encoding.
        See https://vega.github.io/vega-lite/docs/encoding.html#position-datum-def.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    y : str or list of str or dict
        Column name to use for the y axis, or Vega-Lite dict for the y encoding.
        If a list of strings, draws several series on the same chart by melting your wide-format
        table into a long-format table behind the scenes. If your table is already in long-format,
        the way to draw multiple series is by using the color parameter instead.
        See https://vega.github.io/vega-lite/docs/encoding.html#position-datum-def.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    color : str or dict or None
        Column name to use for chart colors, or Vega-Lite dict for the color encoding.
        May also be a literal value, like "#223344" or "green".
        None means the default color will be used.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    opacity : number or str or dict or None
        Value to use for the opacity, or column name, or Vega-Lite encoding dict.
        None means the default opacity (1.0) will be used.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    stack : bool or str
        True means areas of different colors will be stacked. False means there will be no
        stacking, A Vega-Lite stack spec like 'normalized' is also accepted.
    x_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific X-axis values.
        Can be specified as a dict or a list:
            - list style: [x_value_1, x_value_2, ...]
            - dict style: {x_value_1: label_1, x_value_2: label_2, ...}
    y_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific Y-axis values.
        Can be specified as a dict or a list:
            - list style: [y_value_1, y_value_2, ...]
            - dict style: {y_value_1: label_1, y_value_2: label_2, ...}
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. To hide, use None.
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
    legend = _get_legend_dict(legend)
    melted, data, y_enc, color_enc = _maybe_melt(data, x, y, legend, opacity)

    if color:
        color_enc = _clean_encoding(data, color, legend=legend)

    if stack is not None:
        if stack is True:
            y_enc['stack'] = 'zero'
        else:
            y_enc['stack'] = stack

    meta = D(
        data=data,
        width=width,
        height=height,
        title=title,
    )

    spec = D(
        mark=D(type='area', tooltip=True),
        encoding=D(
            x=_clean_encoding(data, x),
            y=y_enc,
            color=color_enc,
            opacity=_clean_encoding(data, opacity),
        ),
        selection=_get_selection(pan_zoom),
    )

    spec = _add_annotations(spec, x_annot, y_annot)
    spec.update(meta)

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
        legend='bottom',
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
        stacking, A Vega-Lite stack spec like 'normalized' or 'layered' is also accepted.
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
        for more. To hide, use None.
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
    legend = _get_legend_dict(legend)
    melted, data, y_enc, color_enc = _maybe_melt(data, bar, value, legend, opacity)

    if color:
        if color == 'value': # 'value', as in the value= arg.
            color = VAR_NAME
        color_enc = _clean_encoding(data, color, legend=legend)

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

    meta = D(
        data=data,
        width=width,
        height=height,
        title=title,
    )

    spec = D(
        mark=D(type='bar', tooltip=True),
        encoding=D(
            x=x_enc,
            y=y_enc,
            color=color_enc,
            opacity=_clean_encoding(data, opacity),
            column=column_enc,
            row=row_enc,
        ),
    )

    spec.update(meta)

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
        x_annot=None,
        y_annot=None,
        width=None,
        height=None,
        title=None,
        legend='right',
        pan_zoom='both',
        use_container_width=True,
    ):
    """Draw a scatter-plot chart.

    Parameters
    ----------
    data : DataFrame
    x : str or dict
        Column name to use for the x axis, or Vega-Lite dict for the x encoding.
        See https://vega.github.io/vega-lite/docs/encoding.html#position-datum-def.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    y : str or list of str or dict
        Column name to use for the y axis, or Vega-Lite dict for the y encoding.
        If a list of strings, draws several series on the same chart by melting your wide-format
        table into a long-format table behind the scenes. If your table is already in long-format,
        the way to draw multiple lines is by using the color parameter instead.
        See https://vega.github.io/vega-lite/docs/encoding.html#position-datum-def.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    color : str or dict or None
        Column name to use for chart colors, or Vega-Lite dict for the color encoding.
        May also be a literal value, like "#223344" or "green".
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
        None means the default color will be used.
    size : str or dict or None
        Column name to use for the size of plotted datapoints, or Vega-Lite dict for the size
        encoding. May also be a literal value, like 10.
        None means the default size will be used.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    opacity : number or str or dict or None
        Value to use for the opacity, or column name, or Vega-Lite encoding dict.
        None means the default opacity (1.0) will be used.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    x_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific X-axis values.
        Can be specified as a dict or a list:
            - list style: [x_value_1, x_value_2, ...]
            - dict style: {x_value_1: label_1, x_value_2: label_2, ...}
    y_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific Y-axis values.
        Can be specified as a dict or a list:
            - list style: [y_value_1, y_value_2, ...]
            - dict style: {y_value_1: label_1, y_value_2: label_2, ...}
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. To hide, use None.
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
    legend = _get_legend_dict(legend)
    melted, data, y_enc, color_enc = _maybe_melt(data, x, y, legend, size, opacity)

    meta = D(
        data=data,
        width=width,
        height=height,
        title=title,
    )

    spec = D(
        mark=D(type='circle', tooltip=True),
        encoding=D(
            x=_clean_encoding(data, x),
            y=y_enc,
            color=color_enc,
            size=_clean_encoding(data, size, legend=legend),
            opacity=_clean_encoding(data, opacity, legend=legend),
        ),
        selection=_get_selection(pan_zoom),
    )

    spec = _add_annotations(spec, x_annot, y_annot)
    spec.update(meta)

    if pan_zoom == 'minimap':
        spec = _add_minimap(spec, ['x', 'y'], 'bottom')

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def _pie_spec(
        data,
        theta,
        color,
        legend,
    ):
    return D(
        mark=D(type='arc', tooltip=True),
        view=D(stroke=None),
        encoding=D(
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
        legend='right',
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
        for more. To hide, use None.
    use_container_width : bool
        If True, sets the chart to use all available space. This takes precedence over the width
        parameter.
    """

    meta = D(
        data=data,
        width=width,
        height=height,
        title=title,
    )

    spec = _pie_spec(
        data,
        theta,
        color,
        legend,
    )

    spec.update(meta)

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def donut_chart(
        data,
        theta,
        color,
        width=None,
        height=None,
        title=None,
        legend='right',
        use_container_width=True,
    ):
    """Draw a donut chart.

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
        for more. To hide, use None.
    use_container_width : bool
        If True, sets the chart to use all available space. This takes precedence over the width
        parameter.
    """

    meta = D(
        data=data,
        width=width,
        height=height,
        title=title,
    )

    spec = _pie_spec(
        data,
        theta,
        color,
        legend,
    )

    if height:
        innerRadius = height // 4
    else:
        innerRadius = 50 # Default height is 200 in Streamlit's Vega-Lite element.

    spec['mark']['innerRadius'] = innerRadius

    spec.update(meta)

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def event_chart(
        data,
        x,
        y,
        color=None,
        size=None,
        opacity=0.5,
        thickness=2,
        x_annot=None,
        y_annot=None,
        width=None,
        height=None,
        title=None,
        legend='bottom',
        pan_zoom='both',
        use_container_width=True,
    ):
    """Draw an event chart.

    Parameters
    ----------
    data : DataFrame
    x : str or dict
        Column name to use for the x axis, or Vega-Lite dict for the x encoding.
        See https://vega.github.io/vega-lite/docs/encoding.html#position-datum-def.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    y : str or list of str or dict
        Column name to use for the y axis, or Vega-Lite dict for the y encoding.
        If a list of strings, draws several series on the same chart by melting your wide-format
        table into a long-format table behind the scenes. If your table is already in long-format,
        the way to draw multiple series is by using the color parameter instead.
        See https://vega.github.io/vega-lite/docs/encoding.html#position-datum-def.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    color : str or dict or None
        Column name to use for chart colors, or Vega-Lite dict for the color encoding.
        May also be a literal value, like "#223344" or "green".
        None means the default color will be used.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    size : number or str or dict or None
        Column name to use for chart sizes, or Vega-Lite dict for the size encoding.
        May also be a literal value, like 123. None means the size will be inferred.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    opacity : number or str or dict or None
        Value to use for the opacity, or column name, or Vega-Lite encoding dict.
        None means the default opacity (1.0) will be used.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    thickness : number or str or dict
        The thickness of the tick marks in the chart.
    x_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific X-axis values.
        Can be specified as a dict or a list:
            - list style: [x_value_1, x_value_2, ...]
            - dict style: {x_value_1: label_1, x_value_2: label_2, ...}
    y_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific Y-axis values.
        Can be specified as a dict or a list:
            - list style: [y_value_1, y_value_2, ...]
            - dict style: {y_value_1: label_1, y_value_2: label_2, ...}
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. To hide, use None.
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

    legend = _get_legend_dict(legend)

    meta = D(
        data=data,
        width=width,
        height=height,
        title=title,
    )

    spec = D(
        mark=D(type='tick', tooltip=True, thickness=thickness),
        encoding=D(
            x=_clean_encoding(data, x),
            y=_clean_encoding(data, y),
            color=_clean_encoding(data, color, legend=legend),
            size=_clean_encoding(data, size, legend=legend),
            opacity=_clean_encoding(data, opacity, legend=legend),
        ),
        selection=_get_selection(pan_zoom),
    )

    spec = _add_annotations(spec, x_annot, y_annot)
    spec.update(meta)

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
        x_annot=None,
        y_annot=None,
        width=None,
        height=None,
        title=None,
        legend='bottom',
        pan_zoom=None,
        use_container_width=True,
    ):
    """Calculate and draw a time histogram.

    Parameters
    ----------
    data : DataFrame
    date: str
        Column name to use for the date.
    x_unit : str
        Vega-Lite time unit to use for the x axis, such as 'seconds', 'minutes', 'hours', 'day' (day
        of week), 'date' (day of month), 'week', 'month', 'year'.
        See https://vega.github.io/vega-lite/docs/timeunit.html
    y_unit : str
        Vega-Lite time unit to use for the y axis, such as 'seconds', 'minutes', 'hours', 'day' (day
        of week), 'date' (day of month), 'week', 'month', 'year'.
        See https://vega.github.io/vega-lite/docs/timeunit.html
    color : str or dict or None
        Column name to use for chart colors, or Vega-Lite dict for the color encoding.
        May be a literal value, like "#223344" or "green".
        If using aggregate is not None, this is the column that will be aggregated.
        None means the default color will be used, or that the aggregation function does not require
        a column.
    aggregate : str or None
        The Vega-Lite aggregation operation to use for this histogram. Defaults to 'count'.
        Common operations are 'count', 'distinct', 'sum', 'mean', 'median', 'max', 'min',
        'valid', and 'missing'.
        See https://vega.github.io/vega-lite/docs/aggregate.html#ops.
    x_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific X-axis values.
        Can be specified as a dict or a list:
            - list style: [x_value_1, x_value_2, ...]
            - dict style: {x_value_1: label_1, x_value_2: label_2, ...}
    y_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific Y-axis values.
        Can be specified as a dict or a list:
            - list style: [y_value_1, y_value_2, ...]
            - dict style: {y_value_1: label_1, y_value_2: label_2, ...}
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. To hide, use None.
    pan_zoom : str or None
        Specify the method for panning and zooming the chart, if any. Allowed values:
            - 'both': drag canvas to pan, use scroll with mouse to zoom.
            - 'pan': drag canvas to pan.
            - 'zoom': scroll with mouse to zoom.
            - 'minimap': Not supported for histograms.
            - None: chart will not be pannable/zoomable.
    use_container_width : bool
        If True, sets the chart to use all available space. This takes precedence over the width
        parameter.
    """

    meta = D(
        data=data,
        width=width,
        height=height,
        title=title,
    )

    spec = D(
        mark=D(type='rect', tooltip=True),
        encoding=D(
            x=D(field=date, type='ordinal', timeUnit=x_unit, title=None, axis=D(tickBand='extent')),
            y=D(field=date, type='ordinal', timeUnit=y_unit, title=None, axis=D(tickBand='extent')),
            color=_clean_encoding(data, color, aggregate=aggregate, legend=legend)
        ),
        selection=_get_selection(pan_zoom),
    )

    spec = _add_annotations(spec, x_annot, y_annot)
    spec.update(meta)

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def xy_hist(
        data,
        x,
        y,
        color=None,
        aggregate='count',
        x_bin=True,
        y_bin=True,
        x_annot=None,
        y_annot=None,
        width=None,
        height=None,
        title=None,
        legend='bottom',
        pan_zoom=None,
        use_container_width=True,
    ):
    """Calculate and draw an x-y histogram (i.e. 2D histogram).

    Parameters
    ----------
    x : str or dict
        Column name to use for the x axis, or Vega-Lite dict for the x encoding.
        See https://vega.github.io/vega-lite/docs/encoding.html#position-datum-def.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    y : str or list of str or dict
        Column name to use for the y axis, or Vega-Lite dict for the y encoding.
        If a list of strings, draws several series on the same chart by melting your wide-format
        table into a long-format table behind the scenes. If your table is already in long-format,
        the way to draw multiple series is by using the color parameter instead.
        See https://vega.github.io/vega-lite/docs/encoding.html#position-datum-def.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    color : str or dict or None
        Column name to use for chart colors, or Vega-Lite dict for the color encoding.
        May be a literal value, like "#223344" or "green".
        If using aggregate is not None, this is the column that will be aggregated.
        None means the default color will be used, or that the aggregation operation does not require
        a column.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    aggregate : str or None
        The Vega-Lite aggregation operation to use for this histogram. Defaults to 'count'.
        Common operations are 'count', 'distinct', 'sum', 'mean', 'median', 'max', 'min',
        'valid', and 'missing'.
        See https://vega.github.io/vega-lite/docs/aggregate.html#ops.
    x_bin : dict or None
        Allows you to customize the binning properties for the x axis.
        If None, uses the default binning properties.
        See https://vega.github.io/vega-lite/docs/bin.html#bin-parameters>
    y_bin : dict or None
        Allows you to customize the binning properties for the y axis.
        If None, uses the default binning properties.
        See https://vega.github.io/vega-lite/docs/bin.html#bin-parameters>
    x_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific X-axis values.
        Can be specified as a dict or a list:
            - list style: [x_value_1, x_value_2, ...]
            - dict style: {x_value_1: label_1, x_value_2: label_2, ...}
    y_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific Y-axis values.
        Can be specified as a dict or a list:
            - list style: [y_value_1, y_value_2, ...]
            - dict style: {y_value_1: label_1, y_value_2: label_2, ...}
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. To hide, use None.
    pan_zoom : str or None
        Specify the method for panning and zooming the chart, if any. Allowed values:
            - 'both': drag canvas to pan, use scroll with mouse to zoom.
            - 'pan': drag canvas to pan.
            - 'zoom': scroll with mouse to zoom.
            - 'minimap': Not supported for histograms.
            - None: chart will not be pannable/zoomable.
    use_container_width : bool
        If True, sets the chart to use all available space. This takes precedence over the width
        parameter.
    """

    meta = D(
        data=data,
        width=width,
        height=height,
        title=title,
    )

    spec = D(
        mark=D(type='rect', tooltip=True),
        encoding=D(
            x=_clean_encoding(data, x, bin=x_bin),
            y=_clean_encoding(data, y, bin=y_bin),
            color=_clean_encoding(data, color, aggregate=aggregate, legend=legend)
        ),
        selection=_get_selection(pan_zoom),
    )

    spec = _add_annotations(spec, x_annot, y_annot)
    spec.update(meta)

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def hist(
        data,
        x,
        y=None,
        aggregate='count',
        bin=None,
        x_annot=None,
        y_annot=None,
        width=None,
        height=None,
        title=None,
        legend='bottom',
        pan_zoom=None,
        use_container_width=True,
    ):
    """Calculate and draw a histogram.

    Parameters
    ----------
    x : str or dict
        Column name to use for the x axis, or Vega-Lite dict for the x encoding.
        See https://vega.github.io/vega-lite/docs/encoding.html#position-datum-def.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    y : str or dict or None
        Column to be aggregated. See aggregate parameter.
        None means the aggregation operation does not require a column.
        See https://vega.github.io/vega-lite/docs/encoding.html#position-datum-def.
        Also supports Altair-style shorthands, like "foo:T" for temporal. See
        https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types.
    aggregate : str or None
        The Vega-Lite aggregation operation to use for this histogram. Defaults to 'count'.
        Common operations are 'count', 'distinct', 'sum', 'mean', 'median', 'max', 'min',
        'valid', and 'missing'.
        See https://vega.github.io/vega-lite/docs/aggregate.html#ops.
    bin : dict or None
        Allows you to customize the binning properties for the histogram.
        If None, uses the default binning properties.
        See https://vega.github.io/vega-lite/docs/bin.html#bin-parameters>
    x_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific X-axis values.
        Can be specified as a dict or a list:
            - list style: [x_value_1, x_value_2, ...]
            - dict style: {x_value_1: label_1, x_value_2: label_2, ...}
    y_annot : dict or list or None
        Annotations to draw on top the chart, tied to specific Y-axis values.
        Can be specified as a dict or a list:
            - list style: [y_value_1, y_value_2, ...]
            - dict style: {y_value_1: label_1, y_value_2: label_2, ...}
    width : number or None
        Chart width in pixels or None for default. See also, use_container_width.
    height : number or None
        Chart height in pixels, or None for default.
    title : str or None
        Chart title, or None for no title.
    legend : str or None
        Legend orientation: 'top', 'left', 'bottom', 'right', etc. See Vega-Lite docs
        for more. To hide, use None.
    pan_zoom : str or None
        Specify the method for panning and zooming the chart, if any. Allowed values:
            - 'both': drag canvas to pan, use scroll with mouse to zoom.
            - 'pan': drag canvas to pan.
            - 'zoom': scroll with mouse to zoom.
            - 'minimap': Not supported for histograms.
            - None: chart will not be pannable/zoomable.
    use_container_width : bool
        If True, sets the chart to use all available space. This takes precedence over the width
        parameter.
    """

    meta = D(
        data=data,
        width=width,
        height=height,
        title=title,
    )

    spec = D(
        mark=D(type='bar', tooltip=True),
        encoding=D(
            x=_clean_encoding(data, x, bin=bin or True),
            y=_clean_encoding(data, y, aggregate=aggregate),
        ),
        selection=_get_selection(pan_zoom),
    )

    spec = _add_annotations(spec, x_annot, y_annot)
    spec.update(meta)

    st.vega_lite_chart(spec, use_container_width=use_container_width)


def scatter_hist(
        data,
        x,
        y,
        color=None,
        size=None,
        opacity=None,
        aggregate='count',
        x_bin=None,
        y_bin=None,
        width=None,
        height=None,
        title=None,
        legend='bottom',
        pan_zoom=None,
        use_container_width=True,
    ):

    legend = _get_legend_dict(legend)

    scatter_spec = D(
        mark=D(type='circle', tooltip=True),
        width=width,
        height=height,
        title=title,
        encoding=D(
            x=_clean_encoding(data, x),
            y=_clean_encoding(data, y),
            color=_clean_encoding(data, color, legend=legend),
            size=_clean_encoding(data, size, legend=legend),
            opacity=_clean_encoding(data, opacity, legend=legend),
        ),
    )

    x_hist_spec = D(
        mark=D(type='bar', tooltip=True),
        width=width,
        height=_MINI_CHART_SIZE,
        encoding=D(
            x=_clean_encoding(data, x, bin=x_bin or True, title=None, axis=None),
            y=_clean_encoding(data, y, aggregate=aggregate, title=None),
        ),
    )

    y_hist_spec = D(
        mark=D(type='bar', tooltip=True),
        height=height,
        width=_MINI_CHART_SIZE,
        encoding=D(
            x=_clean_encoding(data, x, aggregate=aggregate, title=None),
            y=_clean_encoding(data, y, bin=y_bin or True, title=None, axis=None),
        ),
    )

    spec = D(
        data=data,
        title=title,
        vconcat=[x_hist_spec, D(hconcat=[scatter_spec, y_hist_spec])],
    )

    st.vega_lite_chart(spec, use_container_width=use_container_width)
