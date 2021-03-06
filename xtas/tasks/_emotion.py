# Copyright 2013-2015 Netherlands eScience Center and University of Amsterdam
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

from itertools import chain
import os.path
from shutil import copyfileobj, move
from tempfile import NamedTemporaryFile
from urllib2 import urlopen

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.grid_search import GridSearchCV
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.svm import LinearSVC

from .._downloader import make_data_home


__all__ = ['classify']


_BASE_URL = "https://raw.githubusercontent.com/NLeSC/spudisc-emotion-classification/master/"


def _download():
    import sys
    import os

    if 'nose' in sys.modules:
        selfdir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(selfdir, "mre_test_set.txt")
    else:
        data_home = make_data_home() + os.path.sep
        path = os.path.join(data_home, "movie_review_emotions.txt")
        if not os.path.exists(path):
            tmp = NamedTemporaryFile(prefix=data_home, delete=False)
            try:
                for part in ["train.txt", "test.txt"]:
                    copyfileobj(urlopen(_BASE_URL + part), tmp)
            except:
                tmp.close()
                os.remove(tmp)
                raise
            tmp.close()
            move(tmp.name, path)
    return path


class _GridSearch(GridSearchCV):
    """Wrapper around GridSearchCV; workaround for scikit-learn issue #3484."""

    def decision_function(self, X):
        return super(_GridSearch, self).decision_function(X)

    def predict(self, X):
        return super(_GridSearch, self).predict(X)

def _create_classifier():
    data_train = [ln.rsplit(None, 1) for ln in open(_download())]
    X_train, Y_train = zip(*data_train)
    del data_train

    mlb = MultiLabelBinarizer()
    Y_train = [set(s.split('_')) - {'None'} for s in Y_train]
    Y_train = mlb.fit_transform(Y_train)

    clf = make_pipeline(TfidfVectorizer(sublinear_tf=True, use_idf=False),
                            LinearSVC(dual=False))
    # XXX class_weight="auto" causes a lot of deprecation warnings, but it
    # still fares better than the new class_weight="balanced" heuristic.
    # n_jobs=-1 causes nosetests to hang so that is disabled for now.
    params = {'tfidfvectorizer__use_idf': [True, False],
              'tfidfvectorizer__sublinear_tf': [True, False],
              'linearsvc__class_weight': ["auto", None],
              'linearsvc__C': [.01, .1, 1, 10, 100, 1000],
              'linearsvc__penalty': ['l1', 'l2'],
             }
    clf = OneVsRestClassifier(_GridSearch(clf, params, scoring='f1',
                                              verbose=1, cv=5))
    return clf.fit(X_train, Y_train), mlb


_clf, _mlb = _create_classifier()


def classify(sentences):
    y = _clf.predict(sentences)
    return _mlb.inverse_transform(y)
