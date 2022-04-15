import tensorflow as tf

"""
Set memory growth on the GPU, reducing initial memory usage.
"""
def limit_gpu_memory_usage():
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

"""
Disable eager execution, which is enabled by default from TensorFlow 2.0 onwards.
"""
def disable_eager_execution():
    from tf.python.framework.ops import disable_eager_execution
    disable_eager_execution()
    if tf.executing_eagerly():
        print("Warning: Eager execution is still enabled, performance will be severely impacted")