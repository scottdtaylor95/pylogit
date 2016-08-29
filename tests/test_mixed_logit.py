# -*- coding: utf-8 -*-
"""
Created on Sun Jul 17 15:59:25 2016

@author: timothyb0912
"""

import unittest
from collections import OrderedDict
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
import numpy.testing as npt
import pylogit.mixed_logit_calcs as mlc
import pylogit.mixed_logit as mixed_logit


def temp_utility_transform(sys_utility_array, *args, **kwargs):
    """
    Parameters
    ----------
    sys_utility_array : numpy array.
        Should have 1D or 2D. Should have been created by the dot product of a
        design matrix and an array  of index coefficients.

    Returns
    -------
    2D numpy array.
        The returned array will contain a representation of the
        `sys_utility_array`. If `sys_utility_array` is 2D, then
        `sys_utility_array` will be returned unaltered. Else, the function will
        return `sys_utility_array[:, None]`.
    """
    # Return a 2D array of systematic utility values
    if len(sys_utility_array.shape) == 1:
        systematic_utilities = sys_utility_array[:, np.newaxis]
    else:
        systematic_utilities = sys_utility_array

    return systematic_utilities


class NormalDrawsTests(unittest.TestCase):

    def test_return_format(self):
        n_obs = 10
        n_draws = 5
        n_vars = 3
        random_draws = mlc.get_normal_draws(n_obs, n_draws, n_vars)

        self.assertIsInstance(random_draws, list)
        self.assertEqual(len(random_draws), n_vars)
        for draws in random_draws:
            self.assertIsInstance(draws, np.ndarray)
            self.assertAlmostEqual(draws.shape, (n_obs, n_draws))

        return None


class MixingNamesToPositions(unittest.TestCase):

    def test_convert_mixing_names_to_positions(self):
        fake_index_vars = ["foo", "bar", "cake", "cereal"]
        fake_mixing_vars = ["bar", "cereal"]
        args = (fake_mixing_vars, fake_index_vars)
        mix_pos = mlc.convert_mixing_names_to_positions(*args)

        self.assertIsInstance(mix_pos, list)
        self.assertEqual(len(mix_pos), len(fake_mixing_vars))
        for pos, idx_val in enumerate(mix_pos):
            current_var = fake_mixing_vars[pos]
            self.assertEqual(idx_val, fake_index_vars.index(current_var))
        return None


class MixedLogitCalculations(unittest.TestCase):

    # Note that for this set up, we will consider a situation with the
    # following parameters:
    # 3 Alternatives per individual
    # 2 Individuals
    # Individual 1 has 2 observed choice situations
    # Individual 2 has 1 observed choice situation
    # The true systematic utility depends on ASC_1, ASC_2, and a single X
    # The X coefficient is randomly distributed
    def setUp(self):
        # Fake random draws where Row 1 is for observation 1 and row 2 is
        # for observation 2. Column 1 is for draw 1 and column 2 is for draw 2
        self.fake_draws = np.array([[0.4, 0.8], [0.6, 0.2]])
        # Create the betas to be used during the tests
        self.fake_betas = np.array([0.3, -0.6, 0.2])
        self.fake_std = 1
        self.fake_betas_ext = np.concatenate((self.fake_betas,
                                              np.array([self.fake_std])),
                                             axis=0)

        # Create the fake design matrix with columns denoting ASC_1, ASC_2, X
        self.fake_design = np.array([[1, 0, 1],
                                     [0, 1, 2],
                                     [0, 0, 3],
                                     [1, 0, 1.5],
                                     [0, 1, 2.5],
                                     [0, 0, 3.5],
                                     [1, 0, 0.5],
                                     [0, 1, 1.0],
                                     [0, 0, 1.5]])
        # Record what positions in the design matrix are being mixed over
        self.mixing_pos = [2]

        # Create the arrays that specify the choice situation, individual id
        # and alternative ids
        self.situation_ids = np.array([1, 1, 1, 2, 2, 2, 3, 3, 3])
        self.individual_ids = np.array([1, 1, 1, 1, 1, 1, 2, 2, 2])
        self.alternative_ids = np.array([1, 2, 3, 1, 2, 3, 1, 2, 3])
        # Create a fake array of choices
        self.choice_array = np.array([0, 1, 0, 0, 0, 1, 1, 0, 0])

        # Create the 'rows_to_mixers' sparse array for this dataset
        # Denote the rows that correspond to observation 1 and observation 2
        self.obs_1_rows = np.ones(self.fake_design.shape[0])
        # Make sure the rows for observation 2 are given a zero in obs_1_rows
        self.obs_1_rows[-3:] = 0
        self.obs_2_rows = 1 - self.obs_1_rows
        # Create the row_to_mixers scipy.sparse matrix
        self.fake_rows_to_mixers = csr_matrix(self.obs_1_rows[:, None] ==
                                              np.array([1, 0])[None, :])
        # Create the rows_to_obs scipy.sparse matrix
        self.fake_rows_to_obs = csr_matrix(self.situation_ids[:, None] ==
                                           np.arange(1, 4)[None, :])
        # Create the rows_to_alts scipy.sparse matrix
        self.fake_rows_to_alts = csr_matrix(self.alternative_ids[:, None] ==
                                            np.arange(1, 4)[None, :])

        # Create the design matrix that we should see for draw 1 and draw 2
        arrays_to_join = (self.fake_design.copy(),
                          self.fake_design.copy()[:, -1][:, None])
        self.fake_design_draw_1 = np.concatenate(arrays_to_join, axis=1)
        self.fake_design_draw_2 = self.fake_design_draw_1.copy()

        # Multiply the 'random' coefficient draws by the corresponding variable
        self.fake_design_draw_1[:, -1] *= (self.obs_1_rows *
                                           self.fake_draws[0, 0] +
                                           self.obs_2_rows *
                                           self.fake_draws[1, 0])
        self.fake_design_draw_2[:, -1] *= (self.obs_1_rows *
                                           self.fake_draws[0, 1] +
                                           self.obs_2_rows *
                                           self.fake_draws[1, 1])
        extended_design_draw_1 = self.fake_design_draw_1[:, None, :]
        extended_design_draw_2 = self.fake_design_draw_2[:, None, :]
        self.fake_design_3d = np.concatenate((extended_design_draw_1,
                                              extended_design_draw_2),
                                             axis=1)

        # Create the fake systematic utility values
        self.sys_utilities_draw_1 = (self.fake_design_draw_1
                                         .dot(self.fake_betas_ext))
        self.sys_utilities_draw_2 = (self.fake_design_draw_2
                                         .dot(self.fake_betas_ext))

        #####
        # Calculate the probabilities of each alternatve in each choice
        # situation
        #####
        long_exp_draw_1 = np.exp(self.sys_utilities_draw_1)
        long_exp_draw_2 = np.exp(self.sys_utilities_draw_2)
        ind_exp_sums_draw_1 = self.fake_rows_to_obs.T.dot(long_exp_draw_1)
        ind_exp_sums_draw_2 = self.fake_rows_to_obs.T.dot(long_exp_draw_2)
        long_exp_sum_draw_1 = self.fake_rows_to_obs.dot(ind_exp_sums_draw_1)
        long_exp_sum_draw_2 = self.fake_rows_to_obs.dot(ind_exp_sums_draw_2)
        long_probs_draw_1 = long_exp_draw_1 / long_exp_sum_draw_1
        long_probs_draw_2 = long_exp_draw_2 / long_exp_sum_draw_2
        self.prob_array = np.concatenate((long_probs_draw_1[:, None],
                                          long_probs_draw_2[:, None]),
                                         axis=1)

        return None

    def test_create_expanded_design_for_mixing(self):
        # Create the 3d design matrix using the mixed logit functions
        # Note the [2] denotes the fact that the column at position 2 of the
        # fake design matrix is being treated as having random coefficients
        args = (self.fake_design,
                [self.fake_draws],
                [2],
                self.fake_rows_to_mixers)
        actual_3d_design = mlc.create_expanded_design_for_mixing(*args)
        # Actually perform the tests
        npt.assert_allclose(actual_3d_design[:, 0, :], self.fake_design_draw_1)
        npt.assert_allclose(actual_3d_design[:, 1, :], self.fake_design_draw_2)

        return None

    def test_calc_choice_sequence_probs(self):
        # Get the array of probabilities for each alternative under each draw
        # of the random coefficients.
        fake_prob_array = self.prob_array

        # Calculate the average probability of correctly prediicting each
        # person's sequence of choices. Note the 1, 5, 6 are the locations of
        # the "ones" in the self.choice_array. Also, 1 and 5 are grouped
        # because individual 1 has two observed choice situations.
        ind_1_sequence_probs = (fake_prob_array[1, :] *
                                fake_prob_array[5, :]).mean()
        ind_2_sequence_probs = (fake_prob_array[6, :]).mean()
        fake_sequence_probs = np.array([ind_1_sequence_probs,
                                        ind_2_sequence_probs])

        # Calculate the actual, simulated sequence probabilities
        args = (fake_prob_array,
                self.choice_array,
                self.fake_rows_to_mixers,
                "all")
        prob_results = mlc.calc_choice_sequence_probs(*args)
        actual_sequence_probs = prob_results[0]
        sequence_probs_given_draws = prob_results[1]

        # Perform the desired testing
        self.assertEqual(len(prob_results), 2)
        self.assertIsInstance(actual_sequence_probs, np.ndarray)
        self.assertIsInstance(sequence_probs_given_draws, np.ndarray)
        self.assertEqual(len(actual_sequence_probs.shape), 1)
        self.assertEqual(len(sequence_probs_given_draws.shape), 2)
        npt.assert_allclose(actual_sequence_probs, fake_sequence_probs)

        return None

    def test_calc_mixed_log_likelihood(self):
        # Calculate the 'true' log-likelihood
        args_1 = (self.prob_array, self.choice_array, self.fake_rows_to_mixers)
        func_sequence_probs = mlc.calc_choice_sequence_probs(*args_1)
        true_log_likelihood = np.log(func_sequence_probs).sum()

        # Calculate the log-likelihood according to the function being tested
        args_2 = (self.fake_betas_ext,
                  self.fake_design_3d,
                  self.alternative_ids,
                  self.fake_rows_to_obs,
                  self.fake_rows_to_alts,
                  self.fake_rows_to_mixers,
                  self.choice_array,
                  temp_utility_transform)

        function_log_likelihood = mlc.calc_mixed_log_likelihood(*args_2)

        # Perform the required test. AmostEqual used to avoid any issues with
        # floating point representations of numbers.
        self.assertAlmostEqual(true_log_likelihood, function_log_likelihood)
        return None

    def test_calc_mixed_logit_gradient(self):
        # Get the simulated probabilities for each individual and get the
        # array of probabilities given the random draws
        # Calculate the actual, simulated sequence probabilities
        args = (self.prob_array,
                self.choice_array,
                self.fake_rows_to_mixers,
                "all")
        prob_results = mlc.calc_choice_sequence_probs(*args)
        simulated_probs = prob_results[0]
        sequence_probs_given_draws = prob_results[1]

        s_twidle = sequence_probs_given_draws / simulated_probs[:, None]
        long_s_twidle = self.fake_rows_to_mixers.dot(s_twidle)
        error_twidle = ((self.choice_array[:, None] -
                         self.prob_array) *
                        long_s_twidle)

        # Initialize the true gradient
        gradient = np.zeros(self.fake_design_3d.shape[2])

        # Calculate the true gradient in an inefficient but clearly correct way
        for i in xrange(self.fake_design.shape[0]):
            for d in xrange(self.prob_array.shape[1]):
                gradient += (error_twidle[i, d] *
                             self.fake_design_3d[i, d, :])
        gradient *= 1.0 / self.prob_array.shape[1]

        # Get the gradient from the function being tested
        args = (self.fake_betas_ext,
                self.fake_design_3d,
                self.alternative_ids,
                self.fake_rows_to_obs,
                self.fake_rows_to_alts,
                self.fake_rows_to_mixers,
                self.choice_array,
                temp_utility_transform)
        function_gradient = mlc.calc_mixed_logit_gradient(*args)

        # Perform the test.
        self.assertIsInstance(function_gradient, np.ndarray)
        self.assertEqual(len(function_gradient.shape), 1)
        self.assertEqual(function_gradient.shape[0],
                         self.fake_design_3d.shape[2])
        npt.assert_allclose(gradient, function_gradient)

        return None

    def test_calc_bhhh_hessian_approximation_mixed_logit(self):
        # Get the simulated probabilities for each individual and get the
        # array of probabilities given the random draws
        # Calculate the actual, simulated sequence probabilities
        args = (self.prob_array,
                self.choice_array,
                self.fake_rows_to_mixers,
                "all")
        prob_results = mlc.calc_choice_sequence_probs(*args)
        simulated_probs = prob_results[0]
        sequence_probs_given_draws = prob_results[1]

        s_twidle = sequence_probs_given_draws / simulated_probs[:, None]
        long_s_twidle = self.fake_rows_to_mixers.dot(s_twidle)
        error_twidle = ((self.choice_array[:, None] -
                         self.prob_array) *
                        long_s_twidle)

        # Initialize the true gradient, with one row per individual
        gradient = np.zeros((simulated_probs.shape[0],
                             self.fake_design_3d.shape[2]))

        # Calculate the true gradient in an inefficient but clearly correct way
        for pos, i in enumerate(self.individual_ids):
            for d in xrange(self.prob_array.shape[1]):
                gradient[i - 1, :] += (error_twidle[pos, d] *
                                       self.fake_design_3d[pos, d, :])
        gradient *= 1.0 / self.prob_array.shape[1]

        # Calculate the bhhh matrix
        bhhh_matrix = np.zeros((self.fake_design_3d.shape[2],
                                self.fake_design_3d.shape[2]))
        for i in xrange(gradient.shape[0]):
            bhhh_matrix += np.outer(gradient[i, :], gradient[i, :])
        # Multiply by negative one to account for the fact that we're
        # approximating the Fisher Information Matrix
        bhhh_matrix *= -1

        # Get the bhhh matrix from the function being tested
        args = (self.fake_betas_ext,
                self.fake_design_3d,
                self.alternative_ids,
                self.fake_rows_to_obs,
                self.fake_rows_to_alts,
                self.fake_rows_to_mixers,
                self.choice_array,
                temp_utility_transform)
        function_bhhh = mlc.calc_bhhh_hessian_approximation_mixed_logit(*args)

        # Perform the test.
        self.assertIsInstance(function_bhhh, np.ndarray)
        self.assertEqual(len(function_bhhh.shape), 2)
        self.assertEqual(function_bhhh.shape[0],
                         self.fake_design_3d.shape[2])
        self.assertEqual(function_bhhh.shape[1],
                         self.fake_design_3d.shape[2])
        npt.assert_allclose(bhhh_matrix, function_bhhh)

        return None

    def test_panel_predict(self):
        # Specify settings for the test (including seed for reproducibility)
        chosen_seed = 912
        num_test_draws = 3
        num_test_mixing_vars = 1

        # Create the new design matrix for testing
        # There should be two observations. One of which was in in the old
        # data, and one of which was not. One of the observations should have
        # multiple situations being predicted
        new_design = np.array([[1, 0, 1],
                               [0, 1, 2],
                               [0, 0, 1],
                               [1, 0, 0.75],
                               [0, 1, 0.37],
                               [0, 0, 1.5],
                               [1, 0, 2.3],
                               [0, 1, 1.2],
                               [0, 0, 1.1]])
        # Create new arrays that speficy the situation, observation, and
        # alternative ids.
        new_alt_ids = np.array([1, 2, 3, 1, 2, 3, 1, 2, 3])
        new_situation_ids = np.array([1, 1, 1, 2, 2, 2, 3, 3, 3])
        new_obs_ids = np.array([1, 1, 1, 3, 3, 3, 3, 3, 3])

        # Take the chosen number of draws from the normal distribution for each
        # unique observation who has choice situations being predicted.
        new_draw_list = mlc.get_normal_draws(len(np.unique(new_obs_ids)),
                                             num_test_draws,
                                             num_test_mixing_vars,
                                             seed=chosen_seed)

        # Create the new rows_to_mixers for the observations being predicted
        new_row_to_mixer = csr_matrix(new_obs_ids[:, None] ==
                                      np.array([1, 3])[None, :])
        # Create the new rows_to_obs for the observations being predicted
        new_rows_to_obs = csr_matrix(new_situation_ids[:, None] ==
                                     np.array([1, 2, 3])[None, :])
        # Create the new rows_to_alts for the observations being predicted
        new_rows_to_alts = csr_matrix(new_alt_ids[:, None] ==
                                      np.array([1, 2, 3])[None, :])

        # Create the new 3D design matrix
        new_design_3d = mlc.create_expanded_design_for_mixing(new_design,
                                                              new_draw_list,
                                                              self.mixing_pos,
                                                              new_row_to_mixer)

        # Get the array of kernel probabilities for each individual for each
        # choice situation
        prob_args = (self.fake_betas_ext,
                     new_design_3d,
                     new_alt_ids,
                     new_rows_to_obs,
                     new_rows_to_alts,
                     temp_utility_transform)
        prob_kwargs = {"return_long_probs": True}
        new_kernel_probs = mlc.general_calc_probabilities(*prob_args,
                                                          **prob_kwargs)

        # Initialize and calculate the weights needed for prediction with
        # "individualized" coefficient distributions. Should have shape
        # (new_row_to_mixer.shape[1], num_test_draws) == (2, 3)
        weights_per_ind_per_draw = (1.0 / num_test_draws *
                                    np.ones((new_row_to_mixer.shape[1],
                                             num_test_draws)))

        ##########
        # Create the 3D design matrix for the one individual whom we have
        # previously recorded choices for.
        ##########
        # Note rel_old_idx should be np.array([T, T, T, T, T, T, F, F, F])
        rel_old_idx = np.in1d(self.individual_ids, new_obs_ids)
        # rel_old_matrix_2d should have shape (6, 3)
        rel_old_matrix_2d = self.fake_design[rel_old_idx, :]
        rel_old_mixing_var = rel_old_matrix_2d[:, -1][:, None]
        # rel_old_matrix_ext_2d should have shape (6, 4)
        rel_old_matrix_ext_2d = np.concatenate((rel_old_matrix_2d,
                                                rel_old_mixing_var), axis=1)
        # rel_old_matrix_3d should have shape (6, 3, 4)
        rel_old_matrix_3d = np.tile(rel_old_matrix_ext_2d[:, None, :],
                                    (1, num_test_draws, 1))
        # random_vals should have shape(6, 3)
        random_vals = np.tile(new_draw_list[0][0, :][None, :],
                              (rel_old_matrix_3d.shape[0], 1))
        rel_old_matrix_3d[:, :, -1] *= random_vals

        ##########
        # Get the array of kernel probabilities for each individual for whom we
        # have previously recorded choices, for each previously recorded choice
        # situation.
        ##########
        # Get the identifying arrays for the relevant but old observations
        rel_old_alt_ids = self.alternative_ids[rel_old_idx]
        rel_old_rows_to_situations = csr_matrix(np.array([[1, 0],
                                                          [1, 0],
                                                          [1, 0],
                                                          [0, 1],
                                                          [0, 1],
                                                          [0, 1]]))
        rel_old_rows_to_alts = self.fake_rows_to_alts[rel_old_idx, :]
        rel_old_rows_to_mixers = csr_matrix(np.array([[1],
                                                      [1],
                                                      [1],
                                                      [1],
                                                      [1],
                                                      [1]]))

        # Calclulate the desired kernel probabilities for the previously
        # recorded choice situations of those individuals for whom we are
        # predicting future choice situations
        prob_args = (self.fake_betas_ext,
                     rel_old_matrix_3d,
                     rel_old_alt_ids,
                     rel_old_rows_to_situations,
                     rel_old_rows_to_alts,
                     temp_utility_transform)
        prob_kwargs = {"return_long_probs": True}
        rel_old_kernel_probs = mlc.general_calc_probabilities(*prob_args,
                                                              **prob_kwargs)

        ##########
        # Calculate the old sequence probabilities of all the individual's
        # for whom we have recorded observations and for whom we are predicting
        # future choice situations
        ##########
        rel_old_choices = self.choice_array[rel_old_idx]
        sequence_args = (rel_old_kernel_probs,
                         rel_old_choices,
                         rel_old_rows_to_mixers)
        seq_kwargs = {"return_type": 'all'}
        old_sequence_results = mlc.calc_choice_sequence_probs(*sequence_args,
                                                              **seq_kwargs)
        # Note sequence_probs_per_draw should have shape (1, 3)
        sequence_probs_per_draw = old_sequence_results[1]
        # Note rel_old_weights should have shape (1, 3)
        rel_old_weights = (sequence_probs_per_draw /
                           sequence_probs_per_draw.sum(axis=1)[:, None])

        ##########
        # Finish creating the weights for the individualized coefficient
        # distributions.
        ##########
        # Given that this is a test and we know which row corresponds to the
        # individual that has previously recorded observations, we hardcode the
        # assignment to the array of weights
        weights_per_ind_per_draw[0, :] = rel_old_weights

        # Create a 'long' format version of the weights array. This version
        # should have the same number of rows as the new kernel probs but the
        # same number of columns as the weights array (aka the number of draws)
        weights_per_draw = new_row_to_mixer.dot(weights_per_ind_per_draw)

        ##########
        # Calcluate the final probabilities per situation using the
        # individualized coefficients
        ##########
        true_pred_probs = (weights_per_draw * new_kernel_probs).sum(axis=1)
        # Calculate the probabilities per situation without individualized
        # coefficients
        wrong_pred_probs = new_kernel_probs.mean(axis=1)

        ##########
        # Calcluate the predicted probabilities using the function being tested
        ##########

        # Create a fake old long format dataframe for mixed logit model object
        alt_id_column = "alt_id"
        situation_id_column = "situation_id"
        obs_id_column = "observation_id"
        choice_column = "choice"

        fake_old_df = pd.DataFrame({"x": self.fake_design[:, 2],
                                    alt_id_column: self.alternative_ids,
                                    situation_id_column: self.situation_ids,
                                    obs_id_column: self.individual_ids,
                                    choice_column: self.choice_array})
        fake_old_df["intercept"] = 1

        # Create a fake specification
        fake_spec = OrderedDict()
        fake_names = OrderedDict()

        fake_spec["intercept"] = [1, 2]
        fake_names["intercept"] = ["ASC 1", "ASC 2"]

        fake_spec["x"] = [[1, 2, 3]]
        fake_names["x"] = ["beta_x"]

        # Specify the mixing variable
        fake_mixing_vars = ["beta_x"]

        # Create a fake version of a mixed logit model object
        fake_mixl_obj = mixed_logit.MixedLogit(data=fake_old_df,
                                               alt_id_col=alt_id_column,
                                               obs_id_col=situation_id_column,
                                               choice_col=choice_column,
                                               specification=fake_spec,
                                               names=fake_names,
                                               mixing_id_col=obs_id_column,
                                               mixing_vars=fake_mixing_vars)

        # Set all the necessary attributes for prediction:
        # design_3d, coefs, intercepts, shapes, nests, mixing_pos
        fake_mixl_obj.design_3d = self.fake_design_3d
        fake_mixl_obj.coefs = pd.Series(self.fake_betas_ext)
        fake_mixl_obj.intercepts = None
        fake_mixl_obj.shapes = None
        fake_mixl_obj.nests = None

        # Create a fake long format dataframe of the data to be predicted
        predictive_df = pd.DataFrame({"x": new_design[:, 2],
                                      alt_id_column: new_alt_ids,
                                      situation_id_column: new_situation_ids,
                                      obs_id_column: new_obs_ids})
        predictive_df["intercept"] = 1

        # Calculate the probabilities of each alternative being chosen in
        # each choice situation being predictied
        function_pred_probs = fake_mixl_obj.panel_predict(predictive_df,
                                                          num_test_draws,
                                                          seed=chosen_seed)

        ##########
        # Perform the actual tests.
        ##########
        # Test for desired return types and equality of probability arrays
        self.assertIsInstance(function_pred_probs, np.ndarray)
        self.assertEqual(len(function_pred_probs.shape), 1)
        self.assertEqual(function_pred_probs.shape[0],
                         new_design.shape[0])
        assert not np.allclose(wrong_pred_probs, function_pred_probs)
        npt.assert_allclose(true_pred_probs, function_pred_probs)

        return None
