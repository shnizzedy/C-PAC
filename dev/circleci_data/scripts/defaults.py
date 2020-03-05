import numpy as np

correlation_matrix = np.zeros((10,30))
motion_list = ['FD']
regressor_list = [
    'GS',
    'CSF',
    'WM',
    'tCompCor0',
    'aCompCor0',
    'aCompCor1',
    'aCompCor2',
    'aCompCor3',
    'aCompCor4'
]
subjects = {
    'start': 25427,
    'stop': 25456
}
sessions = {
    'start': 1,
    'stop': 2
}
