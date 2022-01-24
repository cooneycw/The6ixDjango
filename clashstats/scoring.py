from The6ix.settings import STAT_FILES, CLUSTERING, HCLUSTERING, CLASH_API
import pickle
import urllib.request
import json
import pandas as pd
import numpy as np
from sklearn.preprocessing import normalize


def mid(s, offset, amount):
    return s[offset:offset+amount]


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


def auto_pull(member):
    success, df = get_games(member.iloc[:, 0:5])
    if success == 0:
        df_out = []
        lbounds = []
        return df_out, lbounds, success
    clan_df = game_cleanup_clan(df)
    clan_df_v2 = append_trophs(clan_df, home)
    team = clan_df_v2.tag.unique()
    i = 0
    for person in team:
        temp_df = clan_df_v2.loc[clan_df['tag'] == person]
        temp_df_v2 = get_segment_away(get_segment(temp_df))

        results = get_probs_seg_clan(temp_df_v2)
        results.sort_values(by=['date', 'time'], ascending=False, inplace=True)
        if i == 0:
            df_out = results
        else:
            df_out = df_out.append(results, ignore_index=True)
        i += 1

    pathname = os.path.abspath(os.path.dirname(__file__))
    with open(pathname + "/pickles/lbounds", 'rb') as handle:
        lbounds = pickle.load(handle)

    return df_out, lbounds, success


def get_games(member):
    cards_name = STAT_FILES / 'pickles/cards'
    cards = pickle.load(open(cards_name, "rb"))

    cards.sort_values(by=['card'], inplace=True)

    elixr = cards.loc[:,'elixr']

    #maxl = (13*(cards['rarity'] == "A_Common")) + (11*(cards['rarity'] == "B_Rare")) + \
    #        (8 * (cards['rarity'] == "C_Epic")) + (5*(cards['rarity'] == "D_Legendary"))

    home_cards = pd.get_dummies(cards['card']).drop(range(cards.shape[0]))
    away_cards = pd.get_dummies(cards['card']).drop(range(cards.shape[0]))

    i = 0
    max_i = (len(member.index))
    ladder_cnt = 0
    while i < min(1000, max_i):
        player_tag = member.iloc[i, 0]

        my_key = CLASH_API

        base_url = "https://api.clashroyale.com/v1"
        n_player_tag = player_tag.replace('#', '%23')
        endpoint = f'/players/{n_player_tag}/battlelog'

        request = urllib.request.Request(
             base_url+endpoint,
             None,
             {
                 "Authorization":  "Bearer %s" % my_key
             }
             )

        response = urllib.request.urlopen(request).read().decode("utf-8")
        data = json.loads(response)

        j = 0
        max_j = len(data)

        while j < max_j:
            game = data[j]

            if (game['type'] == 'PvP') and (((game['gameMode'])['name'] == 'Ladder_CrownRush') or \
                                            ((game['gameMode'])['name'] == 'Ladder_GoldRush') or \
                                            ((game['gameMode'])['name'] == 'Ladder_GemRush'
                                                                           '') or \
                                            (game['gameMode'])['name'] == 'Ladder'):

                home_app = home_cards.copy(deep=True)
                home_gap = home_cards.copy(deep=True)
                home_gap.columns = home_gap.columns + "_lvlgap"
                away_app = away_cards.copy(deep=True)
                away_gap = away_cards.copy(deep=True)
                away_gap.columns = away_gap.columns + "_lvlgap"

                battletime = game['battleTime']

                dt = mid(battletime, 0, 8)
                tm = mid(battletime, 9, 6)
                home = game['team'][0]
                away = game['opponent'][0]

                opponent_tag = game['opponent'][0]['tag']
                #away_exp_level = get_experience(opponent_tag)
                away_exp_level = -1

                t_cards = game['team'][0]['cards']
                a_cards = game['opponent'][0]['cards']

                k = 0

                home_app = home_app.append(pd.Series(0, index=home_app.columns), ignore_index=True)
                home_gap = home_gap.append(pd.Series(0, index=home_gap.columns), ignore_index=True)
                away_app = away_app.append(pd.Series(0, index=away_app.columns), ignore_index=True)
                away_gap = away_gap.append(pd.Series(0, index=away_gap.columns), ignore_index=True)
                while k < 8: # cycle through cards
                    home_app[t_cards[k]['name'].replace(" ", "_").replace(".", "_")] = 1
                    away_app[a_cards[k]['name'].replace(" ", "_").replace(".", "_")] = 1

                    home_gap[(t_cards[k]['name']+'_lvlgap').replace(" ", "_").replace(".", "_")] = t_cards[k]['maxLevel'] - t_cards[k]['level']
                    away_gap[(a_cards[k]['name']+'_lvlgap').replace(" ", "_").replace(".", "_")] = a_cards[k]['maxLevel'] - a_cards[k]['level']

                    k = k + 1

                home_elix = np.sum(home_app.iloc[0].values*elixr.values)/8
                away_elix = np.sum(away_app.iloc[0].values*elixr.values)/8

                home_total_gap = np.sum(home_gap.iloc[0])
                away_total_gap = np.sum(away_gap.iloc[0])

                home_bldg = np.sum(home_app.iloc[0].values*bldgs.values)
                away_bldg = np.sum(away_app.iloc[0].values*bldgs.values)

                home_spll = np.sum(home_app.iloc[0].values*splls.values)
                away_spll = np.sum(away_app.iloc[0].values*splls.values)

                if 'startingTrophies' in home:
                    home_trph = home['startingTrophies']
                else:
                    home_trph = 0

                if 'startingTrophies' in away:
                    away_trph = away['startingTrophies']
                else:
                    away_trph = 0

                h_crowns = home['crowns']
                a_crowns = away['crowns']

                outcome = -1
                if h_crowns > a_crowns:
                    outcome = 1
                elif a_crowns > h_crowns:
                    outcome = 0
                # assemble the dataframe

                away_app.columns = [('a_' + str(col)) for col in away_app.columns]
                away_gap.columns = [('a_' + str(col)) for col in away_gap.columns]

                if ladder_cnt == 0:
                    result = (pd.concat([rankings.iloc[[i]].reset_index(), home_app, home_gap, away_app, away_gap], axis=1))
                    result['opponent_tag']=opponent_tag
                    result['battletime']=battletime
                    result['dt']=dt
                    result['tm']=tm
                    result['home_elix']=home_elix
                    result['away_elix']=away_elix
                    result['home_total_gap']=home_total_gap
                    result['away_total_gap']=away_total_gap
                    result['home_bldg']=home_bldg
                    result['away_bldg']=away_bldg
                    result['home_spll']=home_spll
                    result['away_spll']=away_spll
                    result['home_trph']=home_trph
                    result['away_trph']=away_trph
                    result['h_crowns']=h_crowns
                    result['a_crowns']=a_crowns
                    result['away_exp_level']=away_exp_level
                    result['tag_for_delete']=0
                    result['outcome']=outcome
                    ladder_cnt += 1
                else:
                    interim = (pd.concat([rankings.iloc[[i]].reset_index(), home_app, home_gap, away_app, away_gap], axis=1))
                    interim['opponent_tag']=opponent_tag
                    interim['battletime']=battletime
                    interim['dt']=dt
                    interim['tm']=tm
                    interim['home_elix']=home_elix
                    interim['away_elix']=away_elix
                    interim['home_total_gap']=home_total_gap
                    interim['away_total_gap']=away_total_gap
                    interim['home_bldg']=home_bldg
                    interim['away_bldg']=away_bldg
                    interim['home_spll']=home_spll
                    interim['away_spll']=away_spll
                    interim['home_trph']=home_trph
                    interim['away_trph']=away_trph
                    interim['h_crowns']=h_crowns
                    interim['a_crowns']=a_crowns
                    interim['away_exp_level']=away_exp_level
                    interim['tag_for_delete']=0
                    interim['outcome']=outcome
                    result = result.append(interim)
                    ladder_cnt += 1
                print(f'player: {i}  total ladder games: {ladder_cnt}')
            elif (game['type'] == 'PvP'):
                cwc=0
            elif game['type'] == 'casual2v2':
                cwc=0
            elif game['type'] == 'clanMate':
                cwc=0
            elif game['type'] == 'challenge':
                cwc=0
            elif game['type'] == 'casual1v1':
                cwc=0
            elif game['type'] == 'friendly':
                cwc=0
            elif game['type'] == 'clanWarCollectionDay':
                cwc=0
            elif game['type'] == 'clanWarWarDay':
                cwc=0
            else:
                cwc=0
            j += 1
        i += 1

        # data_v2 = pd.json_normalize(data['items'])
        # if loop_counter == 1:
        #     data_v2['location'] = location
        #     data_v2['country'] = country
        #     rankings = data_v2
        # else:
        #     data_v2['location'] = location
        #     data_v2['country'] = country
        #     rankings = rankings.append(data_v2)
    success = 1
    if ladder_cnt == 0:
        success = 0
        result = []
    return success, result
