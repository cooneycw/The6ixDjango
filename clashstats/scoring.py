from The6ix.settings import STAT_FILES, CLUSTERING, HCLUSTERING
import pickle
from joblib import dump, load
import pandas as pd
from sklearn.preprocessing import normalize


def get_segment(deck_in):
    df_out = deck_in
    deck_df = get_elixr(deck_in)

    segcols_name = STAT_FILES / 'pickles/segment_cols'
    segment_cols = pickle.load(open(segcols_name, "rb"))

    deck = deck_df[segment_cols]

    data_scaled = deck
    data_scaled = pd.DataFrame(data_scaled, columns=deck.columns)

    CLUSTERING.labels_ = CLUSTERING.predict(data_scaled)
    post_clust_data_mapping = {case: cluster for case, cluster in enumerate(CLUSTERING.labels_)}

    H_mapping = {case: cluster for case,
                                   cluster in enumerate(HCLUSTERING.labels_)}
    final_mapping = {case: H_mapping[post_clust_data_mapping[case]]
                     for case in post_clust_data_mapping}

    final_mapping_ls = list(final_mapping.values())
    segs = [x + 1 for x in final_mapping_ls]
    df_out.loc[:, 'home_seg'] = segs
    return df_out


def get_elixr(deck_in):

    cards_df = get_cards()
    cards_df.sort_values(by=['card'], inplace=True)
    cards_df.set_index('card')

    elixr = (deck_in[cards_df.loc[:,'card']].T.mul(cards_df.loc[:,'elixr'].tolist(), axis=0)).T

    deck_in.loc[:,'home_elix'] = (elixr.sum(axis=1))/8

    return deck_in


def get_cards():

    cards_name = STAT_FILES / 'pickles/cards'
    cards = pickle.load(open(cards_name, "rb"))

    return cards