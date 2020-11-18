import numpy as np


class RMSE:
    """
    Root mean square error, with optional normalization
    """

    def __init__(self, observations, norm=None):

        self.observations = observations

        if norm == 'mean':
            self.norm = observations.mean()
        elif norm == 'range':
            self.norm = observations.max() - observations.min()
        elif norm == 'square':
            self.norm = (observations * observations).mean()
        else:
            self.norm = norm

    def __call__(self, simulation):

        diff = self.observations - simulation
        rmse = np.sqrt((diff * diff).mean())

        if self.norm:
            return rmse / self.norm
        else:
            return rmse


class NSE:
    """
    Nash-Sutcliffe Efficiency
    """

    def __init__(self, observations):
        self.observations = observations
        self.square_mean = (observations * observations).mean()

    def __call__(self, simulation):
        diff = self.observations - simulation
        return 1 - np.sqrt((diff * diff).mean() / self.square_mean)


class KGE:
    """
    Kling-Gupta Efficiency
    """

    def __init__(self, observations):
        self.observations = observations
        self.mean = observations.mean()
        self.std = observations.std()

    def __call__(self, simulation):
        x = self.observations.corr(simulation) - 1
        y = simulation.mean() / self.mean - 1
        z = simulation.std() / self.std - 1

        return 1 - np.sqrt(x * x + y * y + z * z)
