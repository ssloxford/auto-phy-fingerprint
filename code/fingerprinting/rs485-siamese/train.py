import argparse

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1' # 0 = all messages are logged (default behavior), 1 = INFO messages are not printed, 2 = INFO and WARNING messages are not printed, 3 = INFO, WARNING, and ERROR messages are not printed

import tensorflow as tf
from tensorflow.keras import layers, models

import common.dataset as dataset
import common.tf_tweak as tf_tweak

# Limit GPU usage
tf_tweak.limit_gpu_memory_usage()


def getSiameseModel():
    left_input = layers.Input((waveform_len, 2))
    right_input = layers.Input((waveform_len, 2))

    dummy_input = layers.Input((waveform_len, 2))
    l = layers.BatchNormalization()(dummy_input)
    l = layers.ZeroPadding1D(padding=2)(l)

    # General inception-style layers
    l = layers.Conv1D(64, 2, activation='relu')(l)
    l = layers.MaxPooling1D()(l)
    l = layers.Conv1D(64, 4, activation='relu')(l)
    l = layers.MaxPooling1D()(l)
    l = layers.Conv1D(32, 8, activation='relu')(l)
    l = layers.MaxPooling1D()(l)
    l = layers.Conv1D(32, 16, activation='relu')(l)
    l = layers.MaxPooling1D()(l)
    l = layers.Conv1D(32, 32, activation='relu')(l)
    l = layers.MaxPooling1D()(l)

    l = layers.Flatten()(l)

    l = layers.Dense(256, activation="sigmoid")(l)

    extractor = models.Model(inputs=[dummy_input], outputs=[l])

    #intermediate model with fingerprints on both sides
    encoded_l = models.Model(inputs=[left_input], outputs=[extractor.call(left_input)])			#call() cuts off old input layer and attaches new one
    encoded_r = models.Model(inputs=[right_input], outputs=[extractor.call(right_input)])

    # Add a customized layer to compute the absolute difference between the encodings
    L1_layer = layers.Lambda(lambda tensors: tf.keras.backend.abs(tensors[0] - tensors[1]))
    L1_distance = L1_layer([encoded_l.output, encoded_r.output])

    # Add a dense layer with a sigmoid unit to generate the similarity score
    prediction = layers.Dense(1,activation='sigmoid')(L1_distance)

    # Connect the inputs with the outputs
    siamese_net = models.Model(inputs=[left_input,right_input],outputs=prediction)

    # return the model
    return siamese_net


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Train a siamese network on ADS-B data")
    parser.add_argument("--h5siamese", type=str, required=True, help="H5 file containing the siamese dataset")
    parser.add_argument("--oversampling_factor", type=int, default=275, help="Oversampling factor used when creating the dataset")
    parser.add_argument("--model_filename", type=str, default="models/model.h5", help="Filename to save the model to")

    args = parser.parse_args()
    h5siamese_filename = args.h5siamese
    oversampling_factor = args.oversampling_factor
    mask = args.mask
    model_filename = args.model_filename

    (train_in, train_out, case_count, waveform_len, feature_count) = dataset.loadSiameseDatasets(h5siamese_filename, oversampling_factor)
    print((train_in.shape, train_out.shape, case_count, waveform_len, feature_count))

    ##no identifiers in RS-485 case, so no masking
    #print("Masking identifiers")
    #train_in = dataset.maskDataset(train_in, oversampling_factor, mask)
    (case_count, waveform_len, feature_count) = train_in.shape
    print(train_in.shape)

    model = getSiameseModel()
    model.summary()

    model.compile(optimizer='adam', loss='binary_crossentropy')

    hist = model.fit(x=dataset.halfhalf_generator(train_in, train_out, 100), epochs=15, steps_per_epoch=len(train_in)//100)

    # Create parent folder
    if not os.path.exists(os.path.dirname(model_filename)):
        os.makedirs(os.path.dirname(model_filename))
    print("Saving model")
    model.save(model_filename)