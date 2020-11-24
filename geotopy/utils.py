from datetime import datetime
import pandas as pd
from math import isnan
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
import hiplot as hip
from tqdm.auto import tqdm


class ParametersLogger:

    def __init__(self, massage):

        self.massage = massage
        self.data = []

    def __call__(self, optimizer, candidate, loss):

        data = {"num-tell": optimizer.num_tell,
                "generation": candidate.generation,
                "loss": loss}
        args, kwargs = self.massage(*candidate.args, **candidate.kwargs)
        for position, value in enumerate(args):
            kwargs[repr(position)] = value
        data.update(kwargs)
        self.data.append(data)

    @property
    def experiment(self):

        return hip.Experiment.from_iterable(self.data)

    def parallel_coordinate_plot(self):

        self.experiment.display()


class ProgressBar(tqdm):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.loss = None

    def __call__(self, optimizer, candidate, loss, **kwargs):

        super().update()

        from_none = self.loss is None
        from_nan = self.loss is not None and isnan(self.loss) and not isnan(loss)
        from_greater = self.loss > loss

        if from_none or from_nan or from_greater:
            self.loss = loss
            self.set_description(desc=f"(Current loss: {self.loss:.4f})")


def comparison_plot(observations, simulation, scales=None, desc=None, unit=None, rel=False, figsize=(16, 9),
                    dpi=100):

    if not scales:
        scales = {'Daily': 'D', 'Weekly': 'W', 'Monthly': 'M'}

    fig, axes = plt.subplots(ncols=3,
                             nrows=len(scales),
                             figsize=figsize,
                             dpi=dpi,
                             constrained_layout=True)

    if desc:
        fig.suptitle(desc)

    for i, (Tstr, T) in enumerate(scales.items()):
        comp_plot, diff_plot, hist_plot = axes[i, :]

        obs_resampled = observations.resample(T).mean()
        sim_resampled = simulation.resample(T).mean()

        err = obs_resampled - sim_resampled
        if rel:
            err = err / obs_resampled.abs()

        data = pd.DataFrame({'Observations': obs_resampled, 'Simulation': sim_resampled})
        sns.lineplot(data=data, ax=comp_plot)
        comp_plot.set_title(Tstr)
        comp_plot.set_xlabel('')
        if unit:
            comp_plot.set_ylabel(f"[{unit}]")

        sns.lineplot(data=err, ax=diff_plot)
        plt.setp(diff_plot.get_xticklabels(), rotation=20)
        diff_plot.set_xlabel('')
        if rel:
            diff_plot.set_ylabel("Relative error")
            diff_plot.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
        elif unit:
            diff_plot.set_ylabel(f"Error [{unit}]")
        else:
            diff_plot.set_ylabel("Error")

        sns.histplot(y=err, kde=True, stat='probability', ax=hist_plot)
        y1, y2 = diff_plot.get_ylim()
        hist_plot.set_ylim(y1, y2)
        hist_plot.set_yticklabels([])
        hist_plot.set_ylabel('')

    return fig


def date_parser(x):

    return datetime.strptime(x, '%d/%m/%Y %H:%M')
