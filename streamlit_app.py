import streamlit as st
import numpy as np
import pandas as pd
import plost

@st.cache
def get_datasets():
    N = 50
    rand = pd.DataFrame()
    rand['a'] = np.arange(N)
    rand['b'] = np.random.rand(N)
    rand['c'] = np.random.rand(N)

    N = 500
    events = pd.DataFrame()
    events['time'] = np.random.randn(N)
    events['servers'] = np.random.choice(['server 1', 'server 2', 'server 3'], N)

    N = 500
    randn = pd.DataFrame(
        np.random.randn(N, 3),
        columns=['a', 'b', 'c'],
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
        seattle=pd.read_csv('./data/seattle-weather.csv'),
        sp500=pd.read_csv('./data/sp500.csv'),
    )


data = get_datasets()

"""
# Plost

You've been writing _plots_ wrong all this time.

---

## Datasets used for these examples

Let's say you have some datasets like these:
"""

dataset_name = st.selectbox("Datasets", data)
st.write(data[dataset_name])

"""
Now let's take this data and go plost some plosts!

---

## The basics
"""

"### line_chart()"

with st.echo():
    plost.line_chart(
        data['rand'],
        x='a',
        y='b')

""

with st.echo():
    plost.line_chart(
        data['rand'],
        x='a',
        y=('b', 'c'))

"---"

"### area_chart()"

with st.echo():
    plost.area_chart(
        data['rand'],
        x='a',
        y=('b', 'c'))

""

with st.echo():
    plost.area_chart(
        data['rand'],
        x='a',
        y=('b', 'c'),
        opacity=0.5,
        stack=False)

""

with st.echo():
    plost.area_chart(
        data['rand'],
        x='a',
        y=('b', 'c'),
        stack='normalize')

""

with st.echo():
    plost.area_chart(
        data['seattle'],
        x=dict(field='date', timeUnit='month'),
        y=dict(field='temp_max', aggregate='mean'),
        color='weather',
    )

"---"

"### bar_chart()"

with st.echo():
    plost.bar_chart(
        data['stocks'],
        bar='company',
        value='q2')

""

with st.echo():
    plost.bar_chart(
        data['stocks'],
        bar='company',
        value='q2',
        direction='horizontal')

""

with st.echo():
    plost.bar_chart(
        data['stocks'],
        bar='company',
        value=['q2', 'q3'],
    )

""

with st.echo():
    plost.bar_chart(
        data['stocks'],
        bar='company',
        value=['q2', 'q3'],
        stack='normalize')

""

with st.echo():
    plost.bar_chart(
        data['stocks'],
        bar='company',
        value=['q2', 'q3'],
        group=True)
""

with st.echo():
    plost.bar_chart(
        data['stocks'],
        bar='company',
        value=['q2', 'q3'],
        group='value',
        color='company',
    )

"---"

"### pie_chart()"

with st.echo():
    plost.pie_chart(
        data['stocks'],
        theta='q2',
        color='company')

"---"

"### donut_chart()"

with st.echo():
    plost.donut_chart(
        data['stocks'],
        theta='q2',
        color='company')

"---"

"### scatter_chart()"

with st.echo():
    plost.scatter_chart(
        data['randn'],
        x='a',
        y='b',
        size='c',
        opacity='b',
        height=500)

"---"

"### event_chart()"

with st.echo():
    plost.event_chart(
        data['events'],
        x='time',
        y='servers')

""

with st.echo():
    plost.event_chart(
        data['events'],
        x='time',
        y='servers',
        color='servers',
        legend='disable')

"""
---

## Histograms
"""

"### hist()"

with st.echo():
    plost.hist(
        data['randn'],
        x='a',
        aggregate='count')

"---"

"### time_hist()"

with st.echo():
    plost.time_hist(
        data['seattle'],
        date='date',
        x_unit='date',
        y_unit='month',
        color='temp_max',
        aggregate='max')

""

with st.echo():
    plost.time_hist(
        data['seattle'],
        date='date',
        x_unit='week',
        y_unit='day',
        color='temp_max',
        aggregate='sum')

"---"

"### xy_hist()"

with st.echo():
    plost.xy_hist(
        data['randn'],
        x='a',
        y='b',
    )

"---"

with st.echo():
    plost.xy_hist(
        data['randn'],
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

with st.echo():
    plost.scatter_hist(
        data['randn'],
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

## Minimaps
"""

with st.echo():
    plost.line_chart(
        data['sp500'],
        x='date:T',
        y='price',
        width=500,
        pan_zoom='minimap')

"---"

with st.echo():
    plost.area_chart(
        data['sp500'],
        x='date:T',
        y='price',
        width=500,
        pan_zoom='minimap')

"---"

with st.echo():
    plost.scatter_chart(
        data['randn'],
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
        data['pageviews'],
        bar='pagenum',
        value='pageviews',
        width=500,
        pan_zoom='minimap')

"---"

with st.echo():
    plost.bar_chart(
        data['pageviews'],
        bar='pagenum',
        value='pageviews',
        direction='horizontal',
        width=500,
        height=500,
        pan_zoom='minimap')
