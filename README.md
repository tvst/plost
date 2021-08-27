# 🍅 Plost

A deceptively simple plotting library for [Streamlit](https://github.com/streamlit/streamlit).

Because you've been writing _plots_ wrong all this time.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/tvst/plost)

## Getting started

```
pip install plost
```

## Basics

Plost makes it easy to make common plots using the Vega-Lite library but without having to specify
complex Vega-Lite specs (unless you're doing something tricky), and without having to melt your
DataFrame from long format to wide format (the bane of most Vega-Lite plots!)

For example, this is a how you draw line chart where Plost internally melts the input data
appropriately for you:

```python
import plost

plost.line_chart(
  my_dataframe,
  x='time',  # The name of the column to use for the x axis.
  y=('stock1', 'stock2'),  # The name of the colums to use for the data itself.
)
```

But this is just the simplest possible example. You can do a lot more with Plost!
Check out the [the sample app](https://share.streamlit.io/tvst/plost) for a taste.


## Documentation

This is in [the sample app](https://share.streamlit.io/tvst/plost) too!
