"""One fixed global baseline, used without test-dependent tuning."""
from sklearn.pipeline import Pipeline,FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


def build():
    return Pipeline([('features',FeatureUnion([
        ('word',TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True)),
        ('char',TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),sublinear_tf=True))],
        transformer_weights={'word':1.,'char':.5})),
        ('classifier',LogisticRegression(C=1.,class_weight='balanced',max_iter=1000,random_state=20261120))])
