import numpy as np
import argparse

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1' # 0 = all messages are logged (default behavior), 1 = INFO messages are not printed, 2 = INFO and WARNING messages are not printed, 3 = INFO, WARNING, and ERROR messages are not printed

import tensorflow as tf
from tensorflow.keras import layers, models

import common.dataset as dataset

# Limit GPU usage
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        # Currently, memory growth needs to be the same across GPUs
        print("Setting GPU memory policy to 'grow as needed'")
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        logical_gpus = tf.config.experimental.list_logical_devices('GPU')
        print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
    except RuntimeError as e:
        # Memory growth must be set before GPUs have been initialized
        print(e)

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Test Siamese model on ADS-B data")
    parser.add_argument("--model_filename", type=str, required=True, default="model.h5", help="Filename to save the model to")
    parser.add_argument("--h5siamese", type=str, required=True, help="H5 file containing the siamese dataset")
    parser.add_argument("--oversampling_factor", type=int, default=10, help="Oversampling factor used when creating the dataset")
    parser.add_argument("--mask", choices=["NONE", "HEADERONLY", "NOICAO", "INVERSE-ICAOONLY", "NOICAOORLATLON"], default="NONE", help="Mask to apply to the dataset")
    parser.add_argument("--test_batches", type=int, default=1000000, help="Number of batches to test")
    parser.add_argument("--batch_size", type=int, default=10, help="Testing batch size")

    args = parser.parse_args()
    model_filename = args.model_filename
    h5siamese = args.h5siamese
    oversampling_factor = args.oversampling_factor
    mask = args.mask
    test_batches = args.test_batches
    batch_size = args.batch_size

    # Load the model
    model = models.load_model(model_filename)
    (test_in, test_out, case_count, waveform_len, feature_count) = dataset.loadSiameseDatasets(h5siamese, oversampling_factor)

    # Mask the test dataset
    test_in = dataset.maskDataset(test_in, oversampling_factor, mask)
    (case_count, waveform_len, feature_count) = test_in.shape

    test_sum = 0
    test_count = 0
    for ([in_l, in_r], matches, out_l, out_r) in dataset.halfhalf_generator_testing(test_in, test_out, batch_size):
        if test_batches <= 0:
            break

        distances = model.predict([in_l, in_r])
        decisions = np.round(distances).astype(int)

        ##detailed information on each value (inc. how often that icao appears in the dataset)
        #for i in range(len(matches)):
        #	occurrences_l = np.sum((test_out == out_l[i]).astype(int))
        #	occurrences_r = np.sum((test_out == out_r[i]).astype(int))
        #	print("{} vs. {} ({} and {}) : {} --> {} ({})".format(out_l[i], out_r[i], occurrences_l, occurrences_r, matches[i], distances[i], np.round(distances[i]).astype(int)))

        #print((matches == decisions).flatten())
        #print(np.sum((matches == decisions).astype(int)))

        correct = matches == decisions
        ncorrect = np.sum(correct.astype(int))
        #if ncorrect != batch_size:		#at least one was wrong
        #	for i in range(batch_size):
        #		if not correct[i]:
        #			occurrences_l = np.sum((test_out == out_l[i]).astype(int))
        #			occurrences_r = np.sum((test_out == out_r[i]).astype(int))
        #			print("Failed: {} vs. {} ({} and {}) : {} --> {} ({})".format(out_l[i], out_r[i], occurrences_l, occurrences_r, matches[i], distances[i], np.round(distances[i]).astype(int)))

        test_sum += ncorrect
        test_count += batch_size
        if test_batches % 100 == 0:
            print(test_sum, test_count, test_sum / test_count)

        test_batches -= 1
