import streamlit as st
import numpy as np
import pandas as pd
import plost

st.set_page_config(page_title='Plost', page_icon=':tomato:')

"""
# 🍅 Plost

A deceptively simple plotting library for [Streamlit](https://github.com/streamlit/streamlit).

_“Because you've been writing plots wrong all this time”_

Below you'll find documentation and live examples showing how to use Plost. Of course,
the first step is:

```
pip install streamlit
pip install plost
```

---

## Intro

Plost makes it easy to build common plots using the
[Vega-Lite](https://vega.github.io/vega-lite/)
library but without having to delve into Vega-Lite specs (unless you're doing
something tricky), and without having to melt your DataFrame from long format to wide
format (the bane of most Vega-Lite plots!)

For example, let's say you have a "long-format" table like this:

| time | stock_name | stock_value |
|------|------------|-------------|
| ...  | stock1     | 1           |
| ...  | stock2     | 2           |
| ...  | stock1     | 100         |
| ...  | stock2     | 200         |


Then you can draw a line chart by simply calling `line_chart()` with some
column names:

```python
import plost

plost.line_chart(
  my_dataframe,
  x='time',  # The name of the column to use for the x axis.
  y='stock_value',  # The name of the column to use for the data itself.
  color='stock_name', # The name of the column to use for the line colors.
)
```

Simple enough! But what if you instead have a "wide-format" table like this, which is
super common in reality:

| time | stock1 | stock2 |
|------|--------|--------|
| ...  | 1      | 100    |
| ...  | 2      | 200    |

Normally you'd have to `melt()` the table with Pandas first or create a complex
Vega-Lite layered plot. But with Plost, you can just specify what you're trying
to accomplish and it will melt the data internally for you:

```python
import plost

plost.line_chart(
  my_dataframe,
  x='time',
  y=('stock1', 'stock2'),  # 👈 This is magic!
)
```

Ok, now let's add a mini-map to make panning/zooming even easier:


```python
import plost

plost.line_chart(
  my_dataframe,
  x='time',
  y=('stock1', 'stock2'),
  pan_zoom='minimap',  # 👈 This is magic!
)
```

But we're just scratching the surface. Basically the idea is that Plost allows
you to make beautiful Vega-Lite-driven charts for your most common needs, without
having to learn about the powerful yet complex language behind Vega-Lite.
"""

@st.cache
def get_datasets():
    N = 50
    rand = pd.DataFrame()
    rand['a'] = np.arange(N)
    rand['b'] = np.random.rand(N)
    rand['c'] = np.random.rand(N)

    N = 500
    events = pd.DataFrame()
    events['time_delta_s'] = np.random.randn(N)
    events['servers'] = np.random.choice(['server 1', 'server 2', 'server 3'], N)

    N = 500
    randn = pd.DataFrame(
        np.random.randn(N, 4),
        columns=['a', 'b', 'c', 'd'],
    )

    stocks = pd.DataFrame(dict(
        company=['goog', 'fb', 'ms', 'amazon'],
        q2=[4, 6, 8, 2],
        q3=[2, 5, 2, 6],
    ))

    N = 200
    pageviews = pd.DataFrame()
    pageviews['pagenum'] = [f'page-{i:03d}' for i in range(N)]
    pageviews['pageviews'] = np.random.randint(0, 1000, N)

    return dict(
        rand=rand,
        randn=randn,
        events=events,
        pageviews=pageviews,
        stocks=stocks,
        seattle_weather=pd.read_csv('./data/seattle-weather.csv', parse_dates=['date']),
        sp500=pd.read_csv('./data/sp500.csv', parse_dates=['date']),
    )


datasets = get_datasets()

"""
---

## Basic examples
"""

with st.expander("Expand to see the datasets used in the examples below"):

  dataset_name = st.selectbox("Datasets", datasets)
  st.write(datasets[dataset_name])

  "Where the columns have the following types:"

  datasets[dataset_name].dtypes.to_dict(),

""

"### line_chart()"

with st.expander('Documentation'):
    st.write(plost.line_chart)

""

with st.echo():
    plost.line_chart(
        data=datasets['seattle_weather'],
        x='date',
        y='temp_max')

""

with st.echo():
    plost.line_chart(
        data=datasets['seattle_weather'],
        x='date',
        y=('temp_max', 'temp_min'))

"---"

"### area_chart()"

with st.expander('Documentation'):
    st.write(plost.area_chart)
""

with st.echo():
    plost.area_chart(
        data=datasets['rand'],
        x='a',
        y=('b', 'c'))

""

with st.echo():
    plost.area_chart(
        data=datasets['rand'],
        x='a',
        y=('b', 'c'),
        opacity=0.5,
        stack=False)

""

with st.echo():
    plost.area_chart(
        data=datasets['rand'],
        x='a',
        y=('b', 'c'),
        stack='normalize')

"---"

"### bar_chart()"

with st.expander('Documentation'):
    st.write(plost.bar_chart)
""

with st.echo():
    plost.bar_chart(
        data=datasets['stocks'],
        bar='company',
        value='q2')

""

with st.echo():
    plost.bar_chart(
        data=datasets['stocks'],
        bar='company',
        value='q2',
        direction='horizontal')

""

with st.echo():
    plost.bar_chart(
        data=datasets['stocks'],
        bar='company',
        value=['q2', 'q3'],
    )

""

with st.echo():
    plost.bar_chart(
        data=datasets['stocks'],
        bar='company',
        value=['q2', 'q3'],
        stack='normalize')

""

with st.echo():
    plost.bar_chart(
        data=datasets['stocks'],
        bar='company',
        value=['q2', 'q3'],
        group=True)
""

with st.echo():
    plost.bar_chart(
        data=datasets['stocks'],
        bar='company',
        value=['q2', 'q3'],
        group='value',
        color='company',
        legend=None,
    )

"---"

"### pie_chart()"

with st.expander('Documentation'):
    st.write(plost.pie_chart)
""

with st.echo():
    plost.pie_chart(
        data=datasets['stocks'],
        theta='q2',
        color='company')

"---"

"### donut_chart()"

with st.expander('Documentation'):
    st.write(plost.donut_chart)
""

with st.echo():
    plost.donut_chart(
        data=datasets['stocks'],
        theta='q2',
        color='company')

"---"

"### scatter_chart()"

with st.expander('Documentation'):
    st.write(plost.scatter_chart)
""

with st.echo():
    plost.scatter_chart(
        data=datasets['randn'],
        x='a',
        y='b',
        size='c',
        opacity='b',
        height=500)

""

with st.echo():
    plost.scatter_chart(
        data=datasets['randn'],
        x='a',
        y=['b', 'c'],
        size='d',
        height=500)

"---"

"### event_chart()"

with st.expander('Documentation'):
    st.write(plost.event_chart)
""

with st.echo():
    plost.event_chart(
        data=datasets['events'],
        x='time_delta_s',
        y='servers')

""

with st.echo():
    plost.event_chart(
        data=datasets['events'],
        x='time_delta_s',
        y='servers',
        color='servers',
        legend=None)

"""
---

## Histograms
"""

"### hist()"

with st.expander('Documentation'):
    st.write(plost.hist)
""

with st.echo():
    plost.hist(
        data=datasets['randn'],
        x='a',
        aggregate='count')

""

with st.echo():
    plost.hist(
        data=datasets['seattle_weather'],
        x='date',
        y='temp_max',
        aggregate='median')

"---"

"### time_hist()"

with st.expander('Documentation'):
    st.write(plost.time_hist)
""

with st.echo():
    plost.time_hist(
        data=datasets['seattle_weather'],
        date='date',
        x_unit='week',
        y_unit='day',
        color='temp_max',
        aggregate='median',
        legend=None,
    )

"---"

"### xy_hist()"

with st.expander('Documentation'):
    st.write(plost.xy_hist)
""

with st.echo():
    plost.xy_hist(
        data=datasets['randn'],
        x='a',
        y='b',
    )

"---"

with st.echo():
    plost.xy_hist(
        data=datasets['randn'],
        x='a',
        y='b',
        x_bin=dict(maxbins=20),
        y_bin=dict(maxbins=20),
        height=400,
    )

"---"

"""
Woah, double histogram :rainbow:
"""

"### scatter_hist()"

with st.expander('Documentation'):
    st.write(plost.scatter_hist)
""

with st.echo():
    plost.scatter_hist(
        data=datasets['randn'],
        x='a',
        y='b',
        size='c',
        color='c',
        opacity=0.5,
        aggregate='count',
        width=500,
        height=500)

"""
---

# Advanced features

## Vega-Lite encoding dicts

You can use [Vega-Lite encoding dicts](https://vega.github.io/vega-lite/docs/encoding.html) for
the `x`, `y`, `color`, `size`, and `opacity` arguments to do all sorts of fun things. For example,
the chart below is computing the mean of the `y` values, grouped by month.
"""

with st.echo():
    plost.area_chart(
        data=datasets['seattle_weather'],
        x=dict(field='date', timeUnit='month'),
        y=dict(field='temp_max', aggregate='mean'),
        color='weather',
    )

"""
Plost also supports [Altair-style
shorthands](https://altair-viz.github.io/user_guide/encoding.html#encoding-data-types), like
"column_name:T" for temporal.
"""

"""
---

## Annotations

Use `x_annot` and `y_annot` to add vertical or horizontal lines with annotations:
"""

with st.echo():
    plost.area_chart(
        data=datasets['rand'],
        x='a',
        y=('b', 'c'),
        x_annot={
            12: "This is when things became random",
            33: "Actually they were always random. Back to normal now.",
        },
    )


"""
---

## Minimaps

You can add a minimap to many of the charts above my simply passing `pan_zoom='minimap'`.
"""

with st.echo():
    plost.line_chart(
        data=datasets['sp500'],
        x='date',
        y='price',
        width=500,
        pan_zoom='minimap')

"---"

with st.echo():
    plost.area_chart(
        data=datasets['sp500'],
        x='date',
        y='price',
        width=500,
        pan_zoom='minimap')

"---"

with st.echo():
    plost.scatter_chart(
        data=datasets['randn'],
        x='a',
        y='b',
        size='c',
        opacity='b',
        width=500,
        height=500,
        pan_zoom='minimap')

"---"

with st.echo():
    plost.bar_chart(
        data=datasets['pageviews'],
        bar='pagenum',
        value='pageviews',
        width=500,
        pan_zoom='minimap')

"---"

with st.echo():
    plost.bar_chart(
        data=datasets['pageviews'],
        bar='pagenum',
        value='pageviews',
        direction='horizontal',
        width=500,
        height=500,
        pan_zoom='minimap')

""
""
""
""
"🍅"
