from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
import unittest
from unittest import skip
import sys
import os
import numpy as np
import deeplift.blobs as blobs
import theano


class TestActivations(unittest.TestCase):

    def setUp(self):
        self.input_layer = blobs.Input_FixedDefault(
                            default=0.0,
                            num_dims=None,
                            shape=(4,))
        self.w1 = [1.0, 2.0, 3.0, 4.0]
        self.w2 = [-1.0, -2.0, -3.0, -4.0]
        W = np.array([self.w1, self.w2]).T
        b = np.array([-1.0, 1.0])
        self.dense_layer = blobs.Dense(W=W, b=b)
        self.dense_layer.set_inputs(self.input_layer)
        self.inp = [[1.0, 1.0, 1.0, 1.0],
                    [2.0, 2.0, 2.0, 2.0]]
        
    def set_up_prediction_func_and_deeplift_func(self, out_layer):
        
        out_layer.set_inputs(self.dense_layer)
        out_layer.build_fwd_pass_vars()
        self.input_layer.reset_mxts_updated()
        out_layer.set_scoring_mode(blobs.ScoringMode.OneAndZeros)
        out_layer.set_active()
        self.input_layer.update_mxts()

        fprop_func = theano.function([self.input_layer.get_activation_vars()],
                                out_layer.get_activation_vars(),
                                allow_input_downcast=True)
        fprop_results = [list(x) for x in fprop_func(self.inp)] 

        bprop_func = theano.function(
                          [self.input_layer.get_activation_vars()],
                          self.input_layer.get_mxts(),
                          allow_input_downcast=True)
        bprop_results_each_task = []
        for task_idx in range(len(fprop_results[0])):
            out_layer.update_task_index(task_index=task_idx)
            bprop_results_task = [list(x) for x in bprop_func(self.inp)]
            bprop_results_each_task.append(bprop_results_task)

        #out_layer.set_inactive()
        return fprop_results, bprop_results_each_task

    def test_relu_deeplift(self): 
        out_layer = blobs.ReLU(mxts_mode=blobs.MxtsMode.DeepLIFT,
                                expo_upweight_factor=1)
        fprop_results, bprop_results_each_task =\
            self.set_up_prediction_func_and_deeplift_func(out_layer) 

        self.assertListEqual(fprop_results,
                             [[9.0,0.0], [19.0, 0.0]])
        #post-activation under default would be [0.0, 1.0]
        #post-activation diff from default = [9.0, -1.0], [19.0, -1.0]
        #pre-activation under default would be [-1.0, 1.0]
        #pre-activation diff-from-default is [10.0, -10.0], [20.0, -20.0]
        #scale-factors: [[9.0/10.0, -1.0/-10.0], [19.0/20.0, -1.0/-20.0]]

        print(bprop_results_each_task)

        np.testing.assert_almost_equal(np.array(bprop_results_each_task[0]),
                                     np.array([(9.0/10.0)*np.array(self.w1),
                                              (19.0/20.0)*np.array(self.w1)]))
        np.testing.assert_almost_equal(np.array(bprop_results_each_task[1]),
                                     np.array([(-1.0/-10.0)*np.array(self.w2),
                                              (-1.0/-20.0)*np.array(self.w2)]))

