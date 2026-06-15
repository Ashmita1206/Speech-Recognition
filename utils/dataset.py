import os
import numpy as np
from utils.audio_processing import load_audio, extract_mfcc

def load_dataset(data_path):
    X = []
    y = []

    labels = os.listdir(data_path)
    label_map = {label: i for i, label in enumerate(labels)}

    for label in labels:
        folder = os.path.join(data_path, label)
        if not os.path.isdir(folder):
            continue

        for file in os.listdir(folder):
            if not file.endswith('.wav'):
                continue
            file_path = os.path.join(folder, file)

            audio, sr = load_audio(file_path)
            mfcc = extract_mfcc(audio, sr)
            
            if mfcc is not None:
                X.append(mfcc)
                y.append(label_map[label])

    X = np.array(X)          # (samples, 13, 150)
    y = np.array(y)

    # RNN expects (samples, timesteps, features)
    X = X.transpose(0, 2, 1)   # (samples, 150, 13)

    return X, y, label_map