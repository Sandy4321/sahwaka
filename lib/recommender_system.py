#!/usr/bin/env python
"""
This is a module that contains the main class and functionalities of the recommender systems.
"""
import numpy
from lib.collaborative_filtering import CollaborativeFiltering
from lib.content_based import ContentBased
from lib.evaluator import Evaluator
from lib.LDA import LDARecommender
from lib.LDA2Vec import LDA2VecRecommender
from util.top_recommendations import TopRecommendations
from util.data_parser import DataParser
from util.recommender_configuer import RecommenderConfiguration


class RecommenderSystem(object):
    """
    A class that will combine the content-based and collaborative-filtering,
    in order to provide the main functionalities of recommendations.
    """
    def __init__(self, abstracts=None, ratings=None, process_parser=False, verbose=False):
        """
        Constructor of the RecommenderSystem.
        @param (list[str]) abstracts: List of abstracts; if None, abstracts get queried from the database.
        @param (int[][]) ratings: Ratings matrix; if None, matrix gets queried from the database.
        @param (boolean) process_parser: A Flag deceiding process the dataparser.
        @param (boolean) verbose: A flag deceiding to print progress.
        """
        if process_parser:
            DataParser.process()

        if ratings is None:
            self.ratings = numpy.array(DataParser.get_ratings_matrix())
        else:
            self.ratings = ratings

        self.predictions = numpy.zeros(self.ratings.shape)

        if abstracts is None:
            self.abstracts = DataParser.get_abstracts().values()
        else:
            self.abstracts = abstracts

        self.config = RecommenderConfiguration()
        self.hyperparameters = self.config.get_hyperparameters()
        self.n_iterations = self.config.get_options()['n_iterations']
        self._v = verbose
        if self.config.get_error_metric() == 'RMS':
            self.evaluator = Evaluator(self.ratings, self.abstracts)
        else:
            raise NameError("Not a valid error metric " + self.config.get_error_metric())

        self.content_based = ContentBased(self.abstracts, self.evaluator, self.hyperparameters, self._v)
        if self.config.get_content_based() == 'LDA':
            self.content_based = LDARecommender(self.abstracts, self.evaluator, self.hyperparameters, self._v)
        elif self.config.get_content_based() == 'LDA2Vec':
            self.content_based = LDA2VecRecommender(self.abstracts, self.evaluator, self.hyperparameters, self._v)
        else:
            raise NameError("Not a valid content based " + self.config.get_content_based())

        if self.config.get_collaborative_filtering() == 'ALS':
            self.collaborative_filtering = CollaborativeFiltering(self.ratings, self.evaluator,
                                                                  self.hyperparameters, self._v)
        else:
            raise NameError("Not a valid collaborative filtering " + self.config.get_collaborative_filtering())

    def train(self):
        """
        Train the recommender on the given data.
        @returns (float) The error of the predictions.
        """
        if self._v:
            print("Training content-based %s..." % self.content_based)
        self.content_based.train(self.n_iterations)
        theta = self.content_based.get_document_topic_distribution()
        train, test = self.collaborative_filtering.split()
        if self._v:
            print("Training collaborative-filtering %s..." % self.collaborative_filtering)
        self.collaborative_filtering.train(theta, self.n_iterations)
        error = self.evaluator.recall_at_x(50, self.collaborative_filtering.get_predictions())
        self.predictions = self.collaborative_filtering.get_predictions()
        if self._v:
            print("done training...")
        return error

    def recommend_items(self, user_id, num_recommendations=10):
        """
        Get recommendations for a user.
        @param (int) user_id: The id of the user.
        @param (int) num_recommendations: The number of recommended items.
        @returns (zip) a zipped object containing list of tuples; first index is the id of the document
                       and the second is the value of the calculated recommendation.
        """
        top_recommendations = TopRecommendations(num_recommendations)
        user_ratings = self.predictions[user_id]
        for i in range(len(user_ratings)):
            top_recommendations.insert(i, user_ratings[i])
        return zip(top_recommendations.get_indices(), top_recommendations.get_values())

