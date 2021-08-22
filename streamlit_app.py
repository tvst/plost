import streamlit as st
import numpy as np
import pandas as pd
import plost

@st.cache
def get_datasets():
    data = dict(
        seattle=pd.read_csv('./data/seattle-weather.csv'),
        sp500=pd.read_csv('./data/sp500.csv'),
        randn=pd.DataFrame(
            np.random.randn(500, 3),
            columns=['a', 'b', 'c'],
        ),
        rand=pd.DataFrame(
            np.random.rand(100, 3),
            columns=['a', 'b', 'c'],
        ),
        stocks=pd.DataFrame(dict(
            company=['goog', 'fb', 'ms', 'amazon'],
            q2=[4, 6, 8, 2],
            q3=[2, 5, 2, 6],
        )),
        pageviews=pd.DataFrame(dict(
            pagenum=[f'page-{i:03d}' for i in range(200)],
        )),
        events=pd.DataFrame(
            np.random.randn(500, 1),
            columns=['time'],
        ),
    )

    data['pageviews']['pageviews'] = np.random.randint(0, 1000, data['pageviews'].shape[0])
    data['events']['servers'] = np.random.choice(['server 1', 'server 2', 'server 3'], data['events'].shape[0])

    return data


data = get_datasets()

"""
# Plost

You've been writing "plots" wrong all this time.
"""

"""
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
        y='servers',
        color='#ff3322')

""

with st.echo():
    plost.event_chart(
        data['events'],
        x='time',
        y='servers',
        color='servers',
        legend='disable')

"""
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



"""
# Bugs

* Vega Lite charts don't recover from errors unless you reload
* Some specs don't work. Vega Lite version?
* Hide Streamlit's inner workings from stack traces. May be related to use of venv
* PLEASE UPGRADE THE VEGA LITE VERSION!!!!
"""
