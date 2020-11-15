import pandas as pd
from SALib.sample import latin
from SALib.analyze import delta as delta_mim
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
import hiplot as hip


def sa_sample(variables, n):
    return latin.sample(variables.sa_problem, n)


def sa_analyze(variables, samples):
    columns = variables.names
    samples = samples.dropna(subset=['loss'])
    xs = samples[columns].to_numpy()
    ys = samples['loss'].to_numpy()

    return delta_mim.analyze(variables.sa_problem, xs, ys)


def parallel_coordinates_plot(samples):
    return hip.Experiment.from_dataframe(samples)


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
