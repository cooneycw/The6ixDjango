from The6ix.settings import STAT_FILES, CLUSTERING, HCLUSTERING, CLASH_API
import pickle
import urllib.request
import json
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


def get_clan(clan_tag):
    err_code = 0
    my_key = CLASH_API

    base_url = "https://api.clashroyale.com/v1"
    n_clan_tag = clan_tag.replace('#', '%23')
    endpoint = f'/clans/{n_clan_tag}/members'

    request = urllib.request.Request(
        base_url + endpoint,
        None,
        {
            "Authorization": "Bearer %s" % my_key
        }
    )

    try:
        response = urllib.request.urlopen(request).read().decode("utf-8")
        data = json.loads(response)
        member_list = pd.json_normalize(data['items'])
    except:
        err_code = 99
        member_list = []

    return err_code, member_list


def auto_pull():
    return
