# Copyright 2017 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import sys
import os.path

import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt

from tensorflow.python.platform import gfile


def load_graph(model_file):
    graph = tf.Graph()
    graph_def = tf.GraphDef()

    with open(model_file, "rb") as f:
        graph_def.ParseFromString(f.read())
    with graph.as_default():
        tf.import_graph_def(graph_def)

    return graph


def read_tensor_from_image_file(file_name, input_height=299, input_width=299,
                                input_mean=0, input_std=255):
    input_name = "file_reader"
    output_name = "normalized"
    file_reader = tf.read_file(file_name, input_name)
    if file_name.endswith(".png"):
        image_reader = tf.image.decode_png(file_reader, channels=3,
                                           name='png_reader')
    elif file_name.endswith(".gif"):
        image_reader = tf.squeeze(tf.image.decode_gif(file_reader,
                                                      name='gif_reader'))
    elif file_name.endswith(".bmp"):
        image_reader = tf.image.decode_bmp(file_reader, name='bmp_reader')
    else:
        image_reader = tf.image.decode_jpeg(file_reader, channels=3,
                                            name='jpeg_reader')
    float_caster = tf.cast(image_reader, tf.float32)
    dims_expander = tf.expand_dims(float_caster, 0);
    resized = tf.image.resize_bilinear(dims_expander, [input_height, input_width])
    normalized = tf.divide(tf.subtract(resized, [input_mean]), [input_std])
    sess = tf.Session()
    result = sess.run(normalized)

    return result


def load_labels(label_file):
    label = []
    proto_as_ascii_lines = tf.gfile.GFile(label_file).readlines()
    for l in proto_as_ascii_lines:
        label.append(l.rstrip())
    return label


if __name__ == "__main__":
    file_name = "tensorflow/examples/label_image/data/grace_hopper.jpg"
    folder_name = ""
    model_file = \
        "tensorflow/examples/label_image/data/inception_v3_2016_08_28_frozen.pb"
    label_file = "tensorflow/examples/label_image/data/imagenet_slim_labels.txt"
    input_height = 299
    input_width = 299
    input_mean = 0
    input_std = 255
    input_layer = "input"
    output_layer = "InceptionV3/Predictions/Reshape_1"

    parser = argparse.ArgumentParser()
    parser.add_argument("--image", help="image to be processed")
    parser.add_argument("--vote", type=bool, help="vote over all images in folder")
    parser.add_argument("--graph", help="graph/model to be executed")
    parser.add_argument("--labels", help="name of file containing labels")
    parser.add_argument("--input_height", type=int, help="input height")
    parser.add_argument("--input_width", type=int, help="input width")
    parser.add_argument("--input_mean", type=int, help="input mean")
    parser.add_argument("--input_std", type=int, help="input std")
    parser.add_argument("--input_layer", help="name of input layer")
    parser.add_argument("--output_layer", help="name of output layer")
    parser.add_argument("--top_k_graph", type=bool, help="produce top-k graph")
    parser.add_argument('--summaries_dir',
                        type=str,
                        default='/mnt/storage/home/tc13007/Manta_Inception/tensorflow/retrain_logs',
                        help='Where to save summary logs for TensorBoard.'
                        )
    args = parser.parse_args()

    if args.graph:
        model_file = args.graph
    if args.vote:
        folder_name = "/mnt/storage/scratch/tc13007/mantas_test_augmented"
    if args.image:
        if args.vote:
            file_name = folder_name + "/" + args.image
        else:
            file_name = args.image
    if args.labels:
        label_file = args.labels
    if args.input_height:
        input_height = args.input_height
    if args.input_width:
        input_width = args.input_width
    if args.input_mean:
        input_mean = args.input_mean
    if args.input_std:
        input_std = args.input_std
    if args.input_layer:
        input_layer = args.input_layer
    if args.output_layer:
        output_layer = args.output_layer
    if args.top_k_graph:
        folder_name = "/mnt/storage/scratch/tc13007/mantas_test"

    graph = load_graph(model_file)
    input_name = "import/" + input_layer
    output_name = "import/" + output_layer
    input_operation = graph.get_operation_by_name(input_name)
    output_operation = graph.get_operation_by_name(output_name)

    if args.top_k_graph:

        with tf.Session(graph=graph) as sess:

            accuracy = tf.placeholder(tf.float32)
            top_k_summary = tf.summary.scalar('Top_K', accuracy)
            top_k_writer = tf.summary.FileWriter(args.summaries_dir + '/{model}_top_k'.format(
                model=model_file.split('/')[6].split('_output')[0]),
                                                 sess.graph)

            extensions = ['jpg', 'jpeg', 'JPG', 'JPEG']
            file_list = []
            sess.run(tf.global_variables_initializer())
            evaluated_images = 0
            final_results = np.array([])
            final_results = np.reshape(final_results, [-1, 99])
            ground_truth = np.array([], dtype=int)
            print(final_results.shape)
            for i in range(0, 99):

                truth = i
                file_name = folder_name + '/' + str(i)
                if not gfile.Exists(file_name):
                    tf.logging.error("Image directory '" + file_name + "' not found.")
                for extension in extensions:
                    file_glob = os.path.join(file_name, '*.' + extension)
                    file_list.extend(gfile.Glob(file_glob))
                for file in file_list:
                    ground_truth = np.append(ground_truth, truth)
                    evaluated_images += 1
                    t = read_tensor_from_image_file(file,
                                                    input_height=input_height,
                                                    input_width=input_width,
                                                    input_mean=input_mean,
                                                    input_std=input_std)

                    results = sess.run(output_operation.outputs[0],
                                       {input_operation.outputs[0]: t})
                    final_results = np.append(final_results, results, axis=0)
                file_list = []
            for k in range(1, 100):

                labels = load_labels(label_file)
                prediction = 0
                for results, truth in zip(final_results, ground_truth):
                    results = np.squeeze(results)
                    top_k = results.argsort()[-k:][::-1]
                    for j in top_k:
                        if int(labels[j]) == truth:
                            prediction += 1
                accuracy_str = sess.run(top_k_summary, {accuracy: prediction / evaluated_images})
                top_k_writer.add_summary(accuracy_str, k)
                top_k_writer.flush()
                print('top {} is {}% correct from {} images'.format(k, (prediction / evaluated_images)*100, evaluated_images))

    elif args.vote:

        final_results = np.array([])
        final_results = np.reshape(final_results, [-1, 99])
        extensions = ['jpg', 'jpeg', 'JPG', 'JPEG']
        file_list = []
        if not gfile.Exists(file_name):
            tf.logging.error("Image directory '" + file_name + "' not found.")
        for extension in extensions:
            file_glob = os.path.join(file_name, '*.' + extension)
            file_list.extend(gfile.Glob(file_glob))

        for file in file_list:
            t = read_tensor_from_image_file(file,
                                            input_height=input_height,
                                            input_width=input_width,
                                            input_mean=input_mean,
                                            input_std=input_std)

            with tf.Session(graph=graph) as sess:
                results = sess.run(output_operation.outputs[0],
                                   {input_operation.outputs[0]: t})

            final_results = np.append(final_results, results, axis=0)
            results = np.sum(final_results, axis=0)
            top_k = results.argsort()[-10:][::-1]
            labels = load_labels(label_file)
            for i in top_k:
                print(labels[i], results[i])
    else:
        t = read_tensor_from_image_file(file_name,
                                        input_height=input_height,
                                        input_width=input_width,
                                        input_mean=input_mean,
                                        input_std=input_std)

        with tf.Session(graph=graph) as sess:
            results = sess.run(output_operation.outputs[0],
                               {input_operation.outputs[0]: t})
        results = np.squeeze(results)

        top_k = results.argsort()[-10:][::-1]
        labels = load_labels(label_file)
        for i in top_k:
            print(labels[i], results[i])
