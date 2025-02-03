from .DataLoader import DataLoader

## init the singleton ##
data = DataLoader()

## export the singleton ##
__all__ = ['data']