# :tomato: Plost

A deceptively simple plotting library for [Streamlit](https://github.com/streamlit/streamlit).

Because you've been writing _plots_ wrong all this time.

👇 **THE REAL README IS ACTUALLY HERE:**

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/tvst/plost)

👆 You can find interactive examples, documentation, and much more in the app above.

## Our goal

* What you need 99% of the time is insanely easy
* The other 1% is impossible. Use Vega-Lite instead!

## Getting started

```
pip install plost
```

## Basics

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

Check out the [the sample app / docs](https://share.streamlit.io/tvst/plost) for
a taste of other amazing things you can do!


## Juicy examples

Check out [the documentation app](https://share.streamlit.io/tvst/plost)!


## Documentation

This is in [the documentation app](https://share.streamlit.io/tvst/plost) too!
