import pandas as pd
import numpy as np
import scipy as sp
import re
import sklearn
from sklearn.cross_validation import *
from sklearn.ensemble import RandomForestRegressor
import textblob
from math import *
import time, datetime

tripadvisor_dir= "../../../data/tripadvisor/json"
if __name__ == "__main__":
    start_time= time.time()
    print(datetime.datetime.now())

    df= pd.DataFrame.from_csv("../data/Tweets.csv", encoding="ISO-8859-1")
    def sentiment_to_label(sentiment):
        if sentiment=="neutral":  return 0
        if sentiment=="negative":  return -1
        return 1

    df['airline_sentiment_confidence']= df['airline_sentiment_confidence'].astype('str')
    df['sentiment']= (df['airline_sentiment']).apply(lambda x: sentiment_to_label(x))
    df= df[['text','sentiment']]

    re_attags= re.compile(" @[^ ]* ")
    re_spaces= re.compile("\w+]")
    df['text']= df['text'].apply(lambda x: re_spaces.sub(" ",re_attags.sub(" ", " "+x+" "))[1:-1])
    df= df.drop_duplicates(subset=['text'])
    df.index= df['id']= range(df.shape[0])

    non_alphanums=re.compile('[^A-Za-z]+')
    def normalize_text(text): return non_alphanums.sub(' ', text).lower().strip()
    df['text_normalized']= df['text'].map(lambda x: normalize_text(x))
    df['textblob_score']= df['text_normalized'].map(lambda x: textblob.TextBlob(x).polarity)

    import wordbag_regressor
    print("Train wordbag regressor")
    #wb_regressor= wordbag_regressor.WordbagRegressor("../models/wordbag_model.pkl.gz", tripadvisor_dir)
    wb_regressor= wordbag_regressor.WordbagRegressor("../models/wordbag_model.pkl.gz")
    df['wordbag_score']= wb_regressor.predict(df['text'].values)

    import wordhash_regressor
    print("Train wordhash regressor")
    wh_regressor= wordhash_regressor.WordhashRegressor("../models/wordhash_model.pkl.gz", tripadvisor_dir)
    #wh_regressor= wordhash_regressor.WordhashRegressor("../models/wordhash_model.pkl.gz")
    df['wordhash_score']= wh_regressor.predict(df['text'].values)

    import wordseq_regressor
    print("Train wordseq regressor")
    ws_regressor = wordseq_regressor.WordseqRegressor("../models/wordseq_model.pkl.gz", tripadvisor_dir)
    #ws_regressor = wordseq_regressor.WordseqRegressor("../models/wordseq_model.pkl.gz")
    df['wordseq_score']= ws_regressor.predict_batch(df['text'].values)

    import wordvec_regressor
    print("Train wordvec regressor")
    wv_regressor= wordvec_regressor.WordvecRegressor("../models/wordvec_model.pkl.gz", tripadvisor_dir)
    #wv_regressor= wordvec_regressor.WordvecRegressor("../models/wordvec_model.pkl.gz")
    df['wordvec_score'] = wv_regressor.predict(df['text'].values)

    df['tweet_len']= df['text'].map(lambda x: log(1+len(x)))
    df['tweet_wordcount']= df['text'].map(lambda x: log(1+len(x.split())))



    pd.to_pickle(df, "test.pkl")



    print(df)
    full_preds= np.zeros(df.shape[0])
    columns_pick= ['tweet_len', 'tweet_wordcount', 'wordbag_score', 'wordhash_score', 'wordseq_score', 'wordvec_score', 'textblob_score'] #Mean Squared Error: 0.28730889581
    #columns_pick= ['tweet_len', 'tweet_wordcount', 'wordhash_score', 'wordseq_score', 'wordvec_score', 'textblob_score'] #
    #columns_pick= ['tweet_len', 'tweet_wordcount', 'wordbag_score', 'wordseq_score', 'wordvec_score', 'textblob_score'] #
    #columns_pick= ['tweet_len', 'tweet_wordcount', 'wordbag_score', 'wordhash_score', 'wordvec_score', 'textblob_score'] #
    #columns_pick= ['tweet_len', 'tweet_wordcount', 'wordbag_score', 'wordhash_score', 'wordseq_score', 'textblob_score'] #

    kf= KFold(df.shape[0], n_folds=10, shuffle=True, random_state=0)
    for train_index, dev_index in kf:
        df_train= df.ix[train_index]
        df_dev= df.ix[dev_index]
        clf= RandomForestRegressor(n_estimators=200, criterion='mse', max_depth=None, min_samples_split=5,
                                   min_samples_leaf=2, min_weight_fraction_leaf=0.0, max_features='auto',
                                   max_leaf_nodes=None, bootstrap=True, oob_score=False, n_jobs=8, random_state=0,
                                   verbose=0, warm_start=False)

        clf.fit(df_train[columns_pick], df_train['sentiment'])
        preds= clf.predict(df_dev[columns_pick])
        for x in range(len(preds)):  full_preds[df_dev['id'].iloc[x]]= preds[x]

    df['preds']= full_preds
    df['preds']= sp.clip(full_preds, -1.0, 1.0)

    print(datetime.datetime.now())
    print(("%s minutes ---" % round(((time.time() - start_time)/60),2)))

    c_mse= sklearn.metrics.mean_squared_error(df['sentiment'], df['preds'], sample_weight=None,
                                              multioutput='uniform_average')
    print("Mean Squared Error:", c_mse)
