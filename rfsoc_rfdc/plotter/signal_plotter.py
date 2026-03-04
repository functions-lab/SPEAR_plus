import plotly.graph_objs as go
import numpy as np
from rfsoc_rfdc.rfdc import MyRFdcType
from IPython.display import display


class SignalPlotter:
    """Base class for plotting ADC samples in the time domain.
    """

    def __init__(self, title, auto_range=False):
        range_min, range_max = -MyRFdcType.DAC_MAX_SCALE, MyRFdcType.DAC_MAX_SCALE

        self.fig = go.FigureWidget(layout={
            'title': title,
            'xaxis': {'title': 'ADC Sample Index'},
            'yaxis': {'title': 'Amplitude', 'range': [range_min, range_max] if not auto_range else None}
        })

        if auto_range:
            self.fig.layout.yaxis.autorange = True
            self.fig.layout.shapes = [
                dict(type='line', xref='paper', x0=0, x1=1, yref='y', y0=range_min, y1=range_min,
                     line=dict(dash='dash', color='red')),
                dict(type='line', xref='paper', x0=0, x1=1, yref='y', y0=range_max, y1=range_max,
                     line=dict(dash='dash', color='red'))
            ]

        display(self.fig)

    def update_plot(self, data, plot_ratio=1.0):
        raise NotImplementedError(
            "This method should be overridden by subclasses")


class RealSignalPlotter(SignalPlotter):
    """
    Plot real ADC samples in the time domain
    """

    def __init__(self, title, auto_range=False):
        super().__init__(title, auto_range)
        self.fig.add_scattergl(x=[], y=[], name='Real Samples')

    def update_plot(self, data, plot_ratio=1.0):
        window_size = int(len(data) * plot_ratio)
        self.fig.data[0].x = np.arange(0, window_size, 1)
        self.fig.data[0].y = data[0:window_size]


class ComplexSignalPlotter(SignalPlotter):
    """
    Plot complex ADC samples in the time domain
    """

    def __init__(self, title='Complex Signal Plot', auto_range=False):
        super().__init__(title, auto_range)
        self.fig.add_scattergl(x=[], y=[], name='Real Samples')
        self.fig.add_scattergl(x=[], y=[], name='Complex Samples')

    def update_plot(self, iq_data, plot_ratio=1.0):
        window_size = int(len(iq_data) * plot_ratio)
        self.fig.data[0].x = np.arange(0, window_size, 1)
        self.fig.data[0].y = iq_data.real[0:window_size]
        self.fig.data[1].x = np.arange(0, window_size, 1)
        self.fig.data[1].y = iq_data.imag[0:window_size]
