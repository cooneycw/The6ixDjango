from The6ix.settings import STAT_FILES, CLUSTERING, HCLUSTERING, NEW_SEGMENT_MAP, SEGMENT_COLS, \
    CLASH_API, LBOUNDS, UBOUNDS, ANALYSIS_VAR_LIST, ANALYSIS_SEL_COLS, STATS_SEL_COLS, MAX_SEG, MAX_A_SEG, \
    ELIXR_LBOUNDS, ELIXR_UBOUNDS, LR_MODEL, XGB_MODEL, MIN_MAX_SCALER, TF_MODEL, STACKED_MODEL, REDIS_INSTANCE
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
from math import comb
import requests
import datetime
import copy
import itertools
import time
import pickle
import urllib.request
import json
import pandas as pd
import numpy as np
import sys
import xgboost as xgb
import tensorflow as tf


def rowIndex(row):
    ret_val = int(row.name) + 1
    return ret_val


def mid(s, offset, amount):
    return s[offset:offset+amount]


def get_segment(deck_in):
    df_out = deck_in
    deck_df = get_elixr(deck_in)

    segment_cols = SEGMENT_COLS.copy()

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
    segs = [int(x + 1) for x in final_mapping_ls]
    df_out.loc[:, 'home_seg'] = segs

    df_out['home_seg'] = df_out['home_seg'].map(NEW_SEGMENT_MAP).fillna(int(1))
    df_out['home_seg'] = df_out['home_seg'].astype(pd.Int32Dtype())
    return df_out


def get_elixr(deck_in):
    cards_df = get_cards()
    cards_df.sort_values(by=['card'], inplace=True)
    cards_df.set_index('card')
    elixr = (deck_in[cards_df.loc[:, 'card']].T.mul(cards_df.loc[:, 'elixr'].tolist(), axis=0)).T
    deck_in.loc[:, 'home_elixr'] = (elixr.sum(axis=1))/8
    return deck_in


def get_elixr_away(deck_in):
    cards_df = get_cards()
    cards_df.sort_values(by=['card'], inplace=True)
    cards_df.set_index('card')
    cards_df.loc[:, 'card'] = 'a_' + cards_df['card'].values
    elixr = (deck_in[cards_df.loc[:, 'card']].T.mul(cards_df.loc[:, 'elixr'].tolist(), axis=0)).T
    deck_in.loc[:, 'away_elixr'] = (elixr.sum(axis=1))/8
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
    success, df = get_async_games(member.iloc[:, 0:5])

    if success == 0:
        df_out = []
        lbounds = []
        return df_out, lbounds, success
    clan_df_v2 = game_cleanup_asynch_clan(df)

    clan_df_v2.sort_values(by=['game_dt', 'game_tm'], ascending=False, inplace=True)

    clan_df_v2 = get_segment_away(get_segment(clan_df_v2))

    analysis_sel_cols = ANALYSIS_SEL_COLS.copy()
    stats_sel_cols = STATS_SEL_COLS.copy()

    _, clan_df_v2 = add_trophs(clan_df_v2, analysis_sel_cols)
    _, clan_df_v2 = add_segments_home(clan_df_v2, analysis_sel_cols)
    _, clan_df_v2 = add_segments_away(clan_df_v2, analysis_sel_cols)
    _, clan_df_v2 = add_elixir_home(clan_df_v2, analysis_sel_cols)
    _, clan_df_v2 = add_elixir_away(clan_df_v2, analysis_sel_cols)
    _, clan_df_v2 = code_features(clan_df_v2, analysis_sel_cols)
    _, clan_df_v2 = code_away_features(clan_df_v2, analysis_sel_cols)
    _, clan_df_v2 = code_home_features(clan_df_v2, analysis_sel_cols)

    #        results = get_probs_seg_clan(temp_df_v2)
    #    results.sort_values(by=['date', 'time'], ascending=False, inplace=True)
    #    if i == 0:
    #        df_out = results
    #    else:
    #        df_out = df_out.append(results, ignore_index=True)
    #    i += 1
    pred_outcome = predict(clan_df_v2.loc[:, analysis_sel_cols], clan_df_v2.loc[:, stats_sel_cols], stats_sel_cols, lr_only=True)
    clan_df_v2 = pd.concat([clan_df_v2, pd.DataFrame(pred_outcome, columns=['expected_win_ratio'])], axis=1)

    return clan_df_v2, LBOUNDS, success


def get_async_games(member):
    cards = get_cards()
    cards.sort_values(by=['card'], inplace=True)

    elixr = cards['elixr']

    home_cards = pd.get_dummies(cards['card']).drop(range(cards.shape[0]))

    my_key = CLASH_API

    i = 0
    max_i = (len(member.index))
    base_url = "https://api.clashroyale.com/v1"
    headers = {"Authorization": "Bearer %s" % my_key}
    itm = list()
    itm.append(base_url)
    itm.append(headers)

    def call_clash(call_var):
        base_url = call_var[0]
        headers = call_var[1]
        player_tag = call_var[2]
        n_player_tag = player_tag.replace('#', '%23')
        endpoint = f'/players/{n_player_tag}/battlelog'
        dat = requests.get((base_url + endpoint), headers=headers).json()
        return dat

    players = list()
    while i < min(1000, max_i):
        ind_rng = range(i, min((i + 6), (max_i)), 1)
        itm_lst = (itm.copy())

        call_var = [itm_lst + [member.iloc[q, 0]] for q in ind_rng]
        # data = call_clash(itm_lst)
        pool = ThreadPool(len(call_var))
        results = pool.map(call_clash, call_var)
        pool.close()
        pool.join()
        for result in results:
            players.append(result)
        # print(f'ranked players retrieved: {i}')
        i += 6

    i = 0

    # print(f'Processing {max_i} players...')
    home_card_list = list(home_cards.columns)
    away_card_list = [('a_' + card) for card in home_card_list]

    card_list_compare = [card.replace('_', ' ') for card in home_card_list]
    # adjustment for Pekka / mini-Pekka
    card_list_compare[74] = 'P.E.K.K.A'  # 106 amend if new cards inserted
    card_list_compare[66] = 'Mini P.E.K.K.A'
    elixr_for_mult = elixr.values
    home_tag = list()
    home_name = list()
    away_tag = list()
    away_name = list()
    home_crowns = list()
    away_crowns = list()
    outcome = list()
    battletime = list()
    game_dt = list()
    game_tm = list()
    home_elixr = list()
    away_elixr = list()
    home_level_gap = list()
    away_level_gap = list()
    net_level_gap = list()
    home_cards_all = None
    away_cards_all = None

    for row, player in enumerate(players):
        for subrow, game in enumerate(player):
            if game['type'] == 'PvP':
                # print(game['gameMode']['name'])
                if (game['gameMode']['name'] == 'Ladder_CrownRush') or \
                        (game['gameMode']['name'] == 'Ladder_GoldRush') or \
                        (game['gameMode']['name'] == 'Ladder_GemRush') or \
                        (game['gameMode']['name'] == 'Ladder'):
                    i = i + 1
                    if (i % 2000) == 0:
                        print(f'Processing game #: {i + 1}')
                    home_tag.append(game['team'][0]['tag'])
                    home_name.append(game['team'][0]['name'])
                    away_tag.append(game['opponent'][0]['tag'])
                    away_name.append(game['opponent'][0]['name'])
                    home_crown = game['team'][0]['crowns']
                    away_crown = game['opponent'][0]['crowns']
                    home_crowns.append(home_crown)
                    away_crowns.append(away_crown)
                    if home_crown == away_crown:
                        outcome.append(-1)
                    elif home_crown > away_crown:
                        outcome.append(1)
                    else:
                        outcome.append(0)
                    battletime.append(game['battleTime'])
                    game_dt.append(mid(game['battleTime'], 0, 8))
                    game_tm.append(mid(game['battleTime'], 9, 6))
                    home_cards = np.zeros((1, len(home_card_list)), dtype=int)
                    away_cards = np.zeros((1, len(home_card_list)), dtype=int)
                    home_elixr_calc = 0
                    away_elixr_calc = 0
                    home_gap_calc = 0
                    away_gap_calc = 0
                    for element, card in enumerate(game['team'][0]['cards']):
                        index_element = card_list_compare.index(card['name'])
                        home_cards[0, index_element] = 1
                        home_elixr_calc = home_elixr_calc + elixr_for_mult[index_element]
                        home_gap_calc = home_gap_calc + \
                                        ((card['maxLevel'] - card['level']) * elixr_for_mult[index_element])

                    for element, card in enumerate(game['opponent'][0]['cards']):
                        index_element = card_list_compare.index(card['name'])
                        away_cards[0, index_element] = 1
                        away_elixr_calc = away_elixr_calc + elixr_for_mult[index_element]
                        away_gap_calc = away_gap_calc + \
                                        ((card['maxLevel'] - card['level']) * elixr_for_mult[index_element])

                    t_h_gap = home_gap_calc / 8
                    t_a_gap = away_gap_calc / 8
                    if i == 1:
                        home_cards_all = home_cards
                        away_cards_all = away_cards
                        home_elixr = np.array(home_elixr_calc / 8, dtype=float)
                        away_elixr = np.array(away_elixr_calc / 8, dtype=float)
                        home_level_gap = np.array(t_h_gap, dtype=float)
                        away_level_gap = np.array(t_a_gap, dtype=float)
                        net_level_gap = np.array((t_a_gap - t_h_gap), dtype=float)
                    else:
                        home_cards_all = np.vstack((home_cards_all, home_cards))
                        away_cards_all = np.vstack((away_cards_all, away_cards))
                        home_elixr = np.append(home_elixr, home_elixr_calc / 8)
                        away_elixr = np.append(away_elixr, away_elixr_calc / 8)
                        home_level_gap = np.append(home_level_gap, t_h_gap)
                        away_level_gap = np.append(away_level_gap, t_a_gap)
                        net_level_gap = np.append(net_level_gap, (t_a_gap - t_h_gap))

    result = pd.DataFrame(home_tag, columns=['home_tag'])
    result['home_name'] = home_name
    result['away_tag'] = away_tag
    result['away_name'] = away_name
    result['battletime'] = battletime
    result['game_dt'] = game_dt
    result['game_tm'] = game_tm
    result['home_elixr'] = home_elixr
    result['away_elixr'] = away_elixr
    result['home_level_gap'] = home_level_gap
    result['away_level_gap'] = away_level_gap
    result['net_level_gap'] = net_level_gap
    result['outcome'] = outcome
    result['home_crowns'] = home_crowns
    result['away_crowns'] = away_crowns

    home_card_df = pd.DataFrame(home_cards_all, columns=home_card_list)
    away_card_df = pd.DataFrame(away_cards_all, columns=away_card_list)

    result.reset_index(drop=True, inplace=True)
    home_card_df.reset_index(drop=True, inplace=True)
    away_card_df.reset_index(drop=True, inplace=True)

    result = pd.concat([result, home_card_df, away_card_df], axis=1)
    export = result.loc[result.outcome != -1]

    success = 1
    if len(result) == 0:
        success = 0
        result = []
    return success, export


def game_cleanup_asynch_clan(input_df):
    input_df.sort_values(by=['battletime', 'home_tag'], ascending=False, inplace=True)

    # opponents = input_df.opponent_tag.unique()
    # print(f"Length of opponents is: {len(opponents)}")
    # print(f"Number of records is: {len(input_df)}")

    i = 0
    max_i = len(input_df)
    l_home_tag = ""
    l_away_tag = ""
    l_battletime = ""
    input_df['tag_for_delete'] = 0
    while i < max_i:
        if (int(input_df.iloc[i]['game_dt']) < 20210714)  \
                or (input_df.iloc[i].outcome < 0):  # delete games from prior season
            input_df.iloc[i, input_df.columns.get_loc('tag_for_delete')] = 1

        if (0 == i % 20000):
            # print(f'Row: {i}')
            #print(f'Datetime: {datetime.datetime.now()}')
            pass

        if i == 0:
            l_home_tag = input_df.iloc[i].home_tag
            l_away_tag = input_df.iloc[i].away_tag
            l_battletime = input_df.iloc[i].battletime
            i += 1
        else:
            if (l_battletime == input_df.iloc[i].battletime) and (l_away_tag == input_df.iloc[i].home_tag) and \
                    (l_home_tag == input_df.iloc[i].away_tag):
                input_df.iloc[i, input_df.columns.get_loc('tag_for_delete')] = 1

            l_home_tag = input_df.iloc[i].home_tag
            l_away_tag = input_df.iloc[i].away_tag
            l_battletime = input_df.iloc[i].battletime
            i += 1

    input_df = input_df[input_df.tag_for_delete != 1]
    # print(f'New number of records is: {len(input_df)}')
    # process unique player_info

    tags_home = input_df['home_tag'].reset_index(drop=True)
    tags_all = (
        pd.concat([tags_home, input_df['away_tag'].reset_index(drop=True)], axis=0, ignore_index=True)).unique()

    # print(f"Number of players to query: {len(tags_all)}")

    my_key = CLASH_API

    base_url = "https://api.clashroyale.com/v1"
    headers = {"Authorization": "Bearer %s" % my_key}
    itm = list()
    itm.append(base_url)
    itm.append(headers)

    def call_clash_player(call_var):
        base_url = call_var[0]
        headers = call_var[1]
        player_tag = call_var[2]
        n_player_tag = player_tag.replace('#', '%23')
        endpoint = f'/players/{n_player_tag}'

        connection_tries = 0
        for i in range(3):
            try:
                dat = requests.get((base_url + endpoint), headers=headers).json()
            except:
                connection_tries += 1
                # print(f'Call for {player_tag} failed after {i} attempt(s).  Pausing for 2 seconds.')
                time.sleep(2)
            else:
                break

        tag = list()
        exp_level = list()
        pb_forever = list()
        pb_lseason = list()
        pb_bseason = list()

        connection_tries = 0

        try:
            if 'tag' in dat:
                tag.append(dat['tag'])
                exp_level.append(dat['expLevel'])
                if 'bestTrophies' in dat:
                    pb_forever.append(dat['bestTrophies'])
                else:
                    pb_forever.append(-1)
                if 'leagueStatistics' in dat:
                    if 'previousSeason' in dat['leagueStatistics']:
                        pb_lseason.append(dat['leagueStatistics']['previousSeason']['trophies'])
                    else:
                        pb_lseason.append(-1)
                    if 'bestSeason' in dat['leagueStatistics']:
                        pb_bseason.append(dat['leagueStatistics']['bestSeason']['trophies'])
                    else:
                        pb_bseason.append(-1)
                else:
                    pb_lseason.append(-1)
                    pb_bseason.append(-1)
            else:
                tag.append(player_tag)
                # print(f'Player tag {player_tag} is unavailable.  Successful pull.')
                exp_level.append(-1)
                pb_forever.append(-1)
                pb_lseason.append(-1)
                pb_bseason.append(-1)

        except:
                # print(f'{player_tag} is unavailable.  Unsuccessful pull.')
                tag.append(player_tag)
                exp_level.append(-1)
                pb_forever.append(-1)
                pb_lseason.append(-1)
                pb_bseason.append(-1)
                time.sleep(2)

        pack = list()
        pack.append(tag)
        pack.append(exp_level)
        pack.append(pb_forever)
        pack.append(pb_lseason)
        pack.append(pb_bseason)

        return pack

    tag = list()
    exp_level = list()
    pb_forever = list()
    pb_lseason = list()
    pb_bseason = list()

    experience_data = list()
    i = 0
    max_i = len(tags_all)
    while i < max_i:
        ind_rng = range(i, min((i + 10), (max_i)), 1)
        itm_lst = (itm.copy())
        call_var = [itm_lst + [tags_all[q]] for q in ind_rng]
        #packed = call_clash_player(call_var[0])
        pool = ThreadPool(len(call_var))
        packed = pool.map(call_clash_player, call_var)
        pool.close()
        pool.join()
        for pack in packed:
            try:
                tag.append(pack[0][0])
            except:
                # print(f'Unpacking error for {tags_all[i]}.')
                pass
            exp_level.append(pack[1][0])
            pb_forever.append(pack[2][0])
            pb_lseason.append(pack[3][0])
            pb_bseason.append(pack[4][0])
        if (i % (30000*0.01)) == 0:
            # print(f'players retrieved: {i}')
            # print(f'{datetime.datetime.now()}')
            pass
        i += 10

    input_df['home_exp_level'] = -1
    input_df['away_exp_level'] = -1
    input_df['net_exp_level'] = -999
    input_df['home_pb_forever'] = -1
    input_df['away_pb_forever'] = -1
    input_df['net_pb_forever'] = -999
    input_df['home_pb_lseason'] = -1
    input_df['away_pb_lseason'] = -1
    input_df['net_pb_lseason'] = -999
    input_df['home_pb_bseason'] = -1
    input_df['away_pb_bseason'] = -1
    input_df['net_pb_bseason'] = -999

    i = 0
    max_i = len(input_df)
    while i < max_i:
        if (i % 20000) == 0:
            # print(f'{i} records processed.')
            # print(f'{datetime.datetime.now()}')
            pass
        try:
            home_ind = tag.index(input_df.iloc[i]['home_tag'])
        except:
            # print(f"Home player {input_df.iloc[i]['home_tag']} not found in latest website data.")
            input_df.iloc[i, input_df.columns.get_loc('tag_for_delete')] = 1
            i += 1
            continue
        try:
            away_ind = tag.index(input_df.iloc[i]['away_tag'])
        except:
            # print(f"Away player {input_df.iloc[i]['away_tag']} not found in latest website data.")
            input_df.iloc[i, input_df.columns.get_loc('tag_for_delete')] = 1
            i += 1
            continue
        input_df.iloc[i, input_df.columns.get_loc('home_exp_level')] = exp_level[home_ind]
        input_df.iloc[i, input_df.columns.get_loc('away_exp_level')] = exp_level[away_ind]
        input_df.iloc[i, input_df.columns.get_loc('net_exp_level')] = exp_level[home_ind] - exp_level[away_ind]
        input_df.iloc[i, input_df.columns.get_loc('home_pb_forever')] = pb_forever[home_ind]
        input_df.iloc[i, input_df.columns.get_loc('away_pb_forever')] = pb_forever[away_ind]
        input_df.iloc[i, input_df.columns.get_loc('net_pb_forever')] = pb_forever[home_ind] - pb_forever[away_ind]
        input_df.iloc[i, input_df.columns.get_loc('home_pb_lseason')] = pb_lseason[home_ind]
        input_df.iloc[i, input_df.columns.get_loc('away_pb_lseason')] = pb_lseason[away_ind]
        input_df.iloc[i, input_df.columns.get_loc('net_pb_lseason')] = pb_lseason[home_ind] - pb_lseason[away_ind]
        input_df.iloc[i, input_df.columns.get_loc('home_pb_bseason')] = pb_bseason[home_ind]
        input_df.iloc[i, input_df.columns.get_loc('away_pb_bseason')] = pb_bseason[away_ind]
        input_df.iloc[i, input_df.columns.get_loc('net_pb_bseason')] = pb_bseason[home_ind] - pb_bseason[away_ind]
        if ((exp_level[home_ind] == -1) or
            (pb_forever[home_ind] == -1) or
            (pb_forever[away_ind] == -1) or
            (pb_lseason[home_ind] == -1) or
            (pb_lseason[away_ind] == -1) or
            (pb_bseason[home_ind] == -1) or
            (pb_bseason[away_ind] == -1)):
            input_df.iloc[i, input_df.columns.get_loc('tag_for_delete')] = 1
        i += 1

    # print(f'Length of collected records is: {len(input_df)}')
    export_df = input_df[input_df.tag_for_delete != 1]
    # print(f'Length of processed records is: {len(export_df)}')

    return export_df


def get_segment(deck_in):
    df_out = deck_in.copy()

    deck = deck_in[SEGMENT_COLS.to_list()]

    CLUSTERING.labels_ = CLUSTERING.predict(deck)
    post_clust_data_mapping = {case: cluster for case, cluster in enumerate(CLUSTERING.labels_)}

    H_mapping = {case: cluster for case,
                                   cluster in enumerate(HCLUSTERING.labels_)}
    final_mapping = {case: H_mapping[post_clust_data_mapping[case]]
                     for case in post_clust_data_mapping}

    final_mapping_ls = list(final_mapping.values())
    segs = [int(x + 1) for x in final_mapping_ls]
    df_out.loc[:, 'home_seg'] = segs


    df_out['home_seg'] = df_out['home_seg'].map(NEW_SEGMENT_MAP).fillna(int(1))
    df_out['home_seg'] = df_out['home_seg'].astype(pd.Int16Dtype())
    return df_out


def get_segment_away(deck_in):
    df_out = deck_in.copy()

    segment_cols = SEGMENT_COLS.copy().to_list()

    col_names = segment_cols.copy()
    i = 0
    max_seg = len(segment_cols)-1

    while i < max_seg:
        segment_cols[i]='a_'+segment_cols[i]
        i += 1
    segment_cols[max_seg] = 'away_elixr'

    deck_score = pd.DataFrame(deck_in[segment_cols].values, columns=col_names)

    CLUSTERING.labels_ = CLUSTERING.predict(deck_score)
    post_clust_data_mapping = {case: cluster for case, cluster in enumerate(CLUSTERING.labels_)}

    H_mapping = {case: cluster for case,
                                   cluster in enumerate(HCLUSTERING.labels_)}
    final_mapping = {case: H_mapping[post_clust_data_mapping[case]]
                     for case in post_clust_data_mapping}

    final_mapping_ls = list(final_mapping.values())
    segs = [int(x + 1) for x in final_mapping_ls]
    df_out.loc[:, 'away_seg'] = segs

    df_out['away_seg'] = df_out['away_seg'].map(NEW_SEGMENT_MAP).fillna(int(1))
    df_out['away_seg'] = df_out['away_seg'].astype(pd.Int16Dtype())
    return df_out


def add_trophs(analyze_df, analysis_sel_cols):

    trophs = analyze_df['home_pb_lseason'].tolist()
    max_trophs = len(LBOUNDS)
    i = 1
    new_cols = list()
    while i <= max_trophs:
        col = 'trophs' + str(i).zfill(3)
        lower = LBOUNDS[i - 1]
        upper = UBOUNDS[i - 1]
        if i == max_trophs:
            analyze_df[col] = ((trophs >= lower).astype('uint8'))
        else:
            analyze_df[col] = (((trophs < upper) * (trophs >= lower)).astype('uint8'))
        new_cols.append(col)
        i += 1

    return new_cols, analyze_df


def add_segments_home(analyze_df, analysis_sel_cols):
    segs = analyze_df.home_seg

    max_seg = copy.deepcopy(MAX_SEG)

    new_cols = list()

    i = 1
    while i <= max_seg:
        col = 'seg' + str(i).zfill(3)
        analyze_df = pd.concat([analyze_df, pd.DataFrame((1 * (segs == i)).values, columns=[col])], axis=1)
        new_cols.append(col)
        i += 1

    # i = 1
    # while i <= max_seg:
    #     col = 'a_seg' + str(i).zfill(3)
    #     analyze_df[col] = 1 * (a_segs == i)
    #     new_cols.append(col)
    #     i += 1

    return new_cols, analyze_df


def add_segments_away(analyze_df, analysis_sel_cols):
    a_segs = analyze_df.away_seg

    max_seg = copy.deepcopy(MAX_A_SEG)

    new_cols = list()

    # i = 1
    # while i <= max_seg:
    #     col = 'seg' + str(i).zfill(3)
    #     analyze_df[col] = 1 * (segs == i)
    #     new_cols.append(col)
    #     i += 1

    i = 1
    while i <= max_seg:
        col = 'a_seg' + str(i).zfill(3)
        analyze_df = pd.concat([analyze_df, pd.DataFrame((1 * (a_segs == i)).values, columns=[col])], axis=1)
        new_cols.append(col)
        i += 1

    return new_cols, analyze_df


def add_elixir_home(analyze_df, analysis_sel_cols):

    lbounds = ELIXR_LBOUNDS.copy()
    ubounds = ELIXR_UBOUNDS.copy()

    elixir = analyze_df['home_elixr'].tolist()

    max_elixir = len(lbounds)
    i = 1
    new_cols = list()
    while i <= max_elixir:
        col = 'home_elixir_' + str(i).zfill(3)
        lower = lbounds[i - 1]
        upper = ubounds[i - 1]
        if i == max_elixir:
            analyze_df = pd.concat([analyze_df, pd.DataFrame(((elixir >= lower).astype('uint8')), columns=[col])], axis=1)
        else:
            analyze_df = pd.concat([analyze_df, pd.DataFrame((((elixir < upper) * (elixir >= lower)).astype('uint8')), columns=[col])], axis=1)
        new_cols.append(col)
        i += 1

    return new_cols, analyze_df


def add_elixir_away(analyze_df, analysis_sel_cols):
    lbounds = ELIXR_LBOUNDS.copy()
    ubounds = ELIXR_UBOUNDS.copy()

    elixir = analyze_df['away_elixr'].tolist()

    max_elixir = len(lbounds)
    i = 1
    new_cols = list()
    while i <= max_elixir:
        col = 'away_elixir_' + str(i).zfill(3)
        lower = lbounds[i - 1]
        upper = ubounds[i - 1]
        if i == max_elixir:
            analyze_df = pd.concat([analyze_df, pd.DataFrame(((elixir >= lower).astype('uint8')), columns=[col])], axis=1)
        else:
            analyze_df = pd.concat([analyze_df, pd.DataFrame((((elixir < upper) * (elixir >= lower)).astype('uint8')), columns=[col])], axis=1)
        new_cols.append(col)
        i += 1

    return new_cols, analyze_df


def code_features(input_df, analysis_sel_cols):
    analysis_var_list = ANALYSIS_VAR_LIST.copy()

    analysis_home = analysis_var_list[0:1 * 106]  # 106 amendment
    analysis_away = analysis_var_list[106:2 * 106]  # 106 amendment

    feature_list = [var for var in analysis_sel_cols if "_x_" in var]

    home_indicators = input_df[analysis_home].values
    away_indicators = input_df[analysis_away].values

    new_indicators = np.zeros((len(home_indicators), len(feature_list)), dtype=int)

    for i, home_value in enumerate(analysis_home):
        for j, away_value in enumerate(analysis_away):
            test_value = home_value + '_x_' + away_value
            if test_value in feature_list:
                match_ind = feature_list.index(test_value)
                new_indicators[:, match_ind] = home_indicators[:, i] * away_indicators[:, j]

    temp_df = pd.DataFrame(new_indicators, columns=feature_list, dtype='uint8')
    input_df = pd.concat([input_df.reset_index(drop=True), temp_df.reset_index(drop=True)], axis=1)
    return analysis_sel_cols, input_df


def code_home_features(input_df, analysis_sel_cols):
    analysis_var_list = ANALYSIS_VAR_LIST.copy()

    analysis_home = analysis_var_list[0:1 * 106]  # 106 amendment

    feature_list = [var for var in analysis_sel_cols if "_q_" in var]

    home_indicators = input_df[analysis_home].values

    new_indicators = np.zeros((len(home_indicators), len(feature_list)), dtype=int)

    for i, home_value in enumerate(analysis_home):
        for j, home2_value in enumerate(analysis_home):
            test_value = home_value + '_q_' + home2_value
            if test_value in feature_list:
                match_ind = feature_list.index(test_value)
                new_indicators[:, match_ind] = home_indicators[:, i] * home_indicators[:, j]

    temp_df = pd.DataFrame(new_indicators, columns=feature_list, dtype='uint8')
    input_df = pd.concat([input_df.reset_index(drop=True), temp_df.reset_index(drop=True)], axis=1)

    return analysis_sel_cols, input_df


def code_away_features(input_df, analysis_sel_cols):
    analysis_var_list = ANALYSIS_VAR_LIST.copy()

    analysis_away = analysis_var_list[106:2 * 106]  # 106 amendment

    feature_list = [var for var in analysis_sel_cols if "_z_" in var]

    away_indicators = input_df[analysis_away].values

    new_indicators = np.zeros((len(away_indicators), len(feature_list)), dtype=int)

    for i, away_value in enumerate(analysis_away):
        for j, away2_value in enumerate(analysis_away):
            test_value = away_value + '_z_' + away2_value
            if test_value in feature_list:
                match_ind = feature_list.index(test_value)
                new_indicators[:, match_ind] = away_indicators[:, i] * away_indicators[:, j]

    temp_df = pd.DataFrame(new_indicators, columns=feature_list, dtype='uint8')
    input_df = pd.concat([input_df.reset_index(drop=True), temp_df.reset_index(drop=True)], axis=1)
    return analysis_sel_cols, input_df


def auto_analyze(input_df):
    if LR_MODEL.classes_[0] == 0:
        pred_index = 1
    else:
        pred_index = 0

    analysis_sel_cols = ANALYSIS_SEL_COLS.copy()
    stats_sel_cols = STATS_SEL_COLS.copy()

    base_df = input_df.loc[:, analysis_sel_cols]
    base_stats_df = input_df.loc[:, stats_sel_cols]
    base_est = predict(base_df, base_stats_df, stats_sel_cols, lr_only=True)

    intercept_df = base_df.copy()
    intercept_stats_df = base_stats_df.copy()
    for col in intercept_df.columns:
        intercept_df[col].values[:] = 0
    for col in intercept_stats_df.columns:
        intercept_stats_df[col].values[:] = 0

    intercept = predict(intercept_df, intercept_stats_df, stats_sel_cols, lr_only=True)

    troph_cols = [item for item in analysis_sel_cols if "trophs" in item]
    troph_stats_cols = [item for item in stats_sel_cols if "trophs" in item]
    if len(troph_cols) > 0:
        troph_df = base_df.copy()
        troph_stats_df = base_stats_df.copy()
        troph_df.drop(troph_cols, axis=1, inplace=True)
        troph_stats_df.drop(troph_stats_cols, axis=1, inplace=True)
        troph_df['home_pb_lseason'] = 5700
        troph_stats_df['home_pb_lseason'] = 5700
        _, troph_df = add_trophs(troph_df, analysis_sel_cols)
        _, troph_stats_df = add_trophs(troph_stats_df, stats_sel_cols)
        probs = predict(troph_df.loc[:, analysis_sel_cols], troph_stats_df.loc[:, stats_sel_cols], stats_sel_cols, lr_only=True)
        lseason_trophies_impact = (probs / base_est) - 1
    else:
        lseason_trophies_impact = 0

    btroph_df = base_df.copy()
    btroph_stats_df = base_stats_df.copy()
    btroph_df.loc[:, 'net_pb_bseason'] = 0
    btroph_stats_df.loc[:, 'net_pb_bseason'] = 0
    probs = predict(btroph_df.loc[:, analysis_sel_cols], btroph_stats_df.loc[:, stats_sel_cols], stats_sel_cols, lr_only=True)
    bseason_trophies_impact = (base_est / probs) - 1

    etroph_df = base_df.copy()
    etroph_stats_df = base_stats_df.copy()
    etroph_df.loc[:, 'net_exp_level'] = 0
    etroph_stats_df.loc[:, 'net_exp_level'] = 0
    probs = predict(etroph_df.loc[:, analysis_sel_cols], etroph_stats_df.loc[:, stats_sel_cols], stats_sel_cols, lr_only=True)
    exp_trophies_impact = (base_est / probs) - 1

    ltroph_df = base_df.copy()
    ltroph_stats_df = base_stats_df.copy()
    ltroph_df.loc[:, 'net_level_gap'] = 0
    ltroph_stats_df.loc[:, 'net_level_gap'] = 0
    probs = predict(ltroph_df.loc[:, analysis_sel_cols], ltroph_stats_df.loc[:, stats_sel_cols], stats_sel_cols, lr_only=True)
    level_trophies_impact = (base_est / probs) - 1

    deck_impact = (base_est / intercept) / (1 + lseason_trophies_impact) / (1 + bseason_trophies_impact) / (1 + exp_trophies_impact) / (1+level_trophies_impact) - 1

    #
    # _, clan_df_v2 = add_trophs(clan_df_v2, analysis_sel_cols)
    # _, clan_df_v2 = add_segments_home(clan_df_v2, analysis_sel_cols)
    # _, clan_df_v2 = add_segments_away(clan_df_v2, analysis_sel_cols)
    # _, clan_df_v2 = add_elixir_home(clan_df_v2, analysis_sel_cols)
    # _, clan_df_v2 = add_elixir_away(clan_df_v2, analysis_sel_cols)
    # _, clan_df_v2 = code_features(clan_df_v2, analysis_sel_cols)
    # _, clan_df_v2 = code_away_features(clan_df_v2, analysis_sel_cols)
    # _, clan_df_v2 = code_home_features(clan_df_v2, analysis_sel_cols)

    # lr_test = LR_MODEL.predict_proba(clan_df_v2.loc[:, analysis_sel_cols])

    ret_dict = {
        'base_est': base_est[0],
        'intercept': intercept[0],
        'lseason_trophies_impact': lseason_trophies_impact[0],
        'bseason_trophies_impact': bseason_trophies_impact[0],
        'exp_trophies_impact': exp_trophies_impact[0],
        'level_trophies_impact': level_trophies_impact[0],
        'deck_impact': deck_impact[0],
    }
    return ret_dict


def predict(base_df, base_stats_df, stats_sel_cols, lr_only):
    if lr_only == False:
        base_xg_inp = xgb.DMatrix(data=base_stats_df.values, feature_names=stats_sel_cols)
        base_lr_test = LR_MODEL.predict_proba(base_df)
        base_xg_test = XGB_MODEL.predict(base_xg_inp)
        base_stats_df_minmax = MIN_MAX_SCALER.transform(base_stats_df.astype(np.float32))
        base_nn_test = TF_MODEL.predict(base_stats_df_minmax)

        base_val = np.concatenate([base_nn_test, base_lr_test[:, 1:2]], axis=1)
        base_val = np.concatenate([base_val, base_xg_test.reshape(-1, 1)], axis=1)
        probability_est = STACKED_MODEL.predict_proba(base_val)[:, 1]
    else:
        probability_est = LR_MODEL.predict_proba(base_df)[:, 1]
    return probability_est


def auto_reco(input_df, redis_channel, lr_only):
    ret_dict = None
    redis_key = redis_channel + 'ret_dict'
    REDIS_INSTANCE.set(redis_channel + 'reco_data_ready', 'no'.encode('utf-8'))
    REDIS_INSTANCE.set(redis_key, pickle.dumps(ret_dict))

    cards = get_cards()
    cards.sort_values(by=['card'], inplace=True)
    elixr = cards['elixr']
    home_cards = pd.get_dummies(cards['card']).drop(range(cards.shape[0]))
    home_card_list = list(home_cards.columns)
    away_card_list = [('a_' + card) for card in home_card_list]
    card_list_compare = [card.replace('_', ' ') for card in home_card_list]
    # adjustment for Pekka / mini-Pekka
    card_list_compare[74] = 'P.E.K.K.A'  # 106 amend if new cards inserted
    card_list_compare[66] = 'Mini P.E.K.K.A'

    analysis_sel_cols = ANALYSIS_SEL_COLS.copy()
    stats_sel_cols = STATS_SEL_COLS.copy()

    all_cards = home_card_list.copy()
    all_cards.extend(away_card_list)
    combin_base_df = input_df.loc[:, all_cards]
    input_stats_df = input_df.copy()
    base_df = input_df.loc[:, analysis_sel_cols]
    base_stats_df = input_stats_df.loc[:, stats_sel_cols]

    norm_est = predict(base_df, base_stats_df, stats_sel_cols, lr_only=False)

    player_cards = combin_base_df.T.squeeze().to_numpy().nonzero()
    home = player_cards[0][range(0, 8)]
    away = player_cards[0][range(8, 16)]
    card_cnt = int((home_cards.shape)[1])

    rem_list_01, add_list_01, explan_ind_01, new_decks_01 = modify_decks(home, away, card_cnt, 1)
    rem_list_02, add_list_02, explan_ind_02, new_decks_02 = modify_decks(home, away, card_cnt, 2)

    explan_ind = explan_ind_01.copy()
    explan_ind.extend(explan_ind_02)
    #get_var_sizes(list(locals().items()))
    new_df = get_elixr(pd.DataFrame(np.concatenate([new_decks_01, new_decks_02], axis=0), columns=all_cards, dtype='int8'))
    del new_decks_02
    del new_decks_01
    #get_var_sizes(list(locals().items()))

    iter_size = int(0.1*len(new_df))

    i = 0
    max_i = len(new_df)
    new_ests = np.zeros(max_i)
    while i < max_i:
        inds = min((i+iter_size), max_i)
        if inds == 0:
            break
        temp_df = new_df[i:inds].reset_index()
        temp_df = get_elixr_away(temp_df)
        temp_df = get_segment(temp_df)
        temp_df = get_segment_away(temp_df)
        temp_df['home_pb_lseason'] = int(input_df.loc[:, 'home_pb_lseason'])
        temp_df['net_pb_bseason'] = int(input_df.loc[:, 'net_pb_lseason'])
        temp_df['net_exp_level'] = int(input_df.loc[:, 'net_exp_level'])
        temp_df['net_level_gap'] = int(input_df.loc[:, 'net_level_gap'])
        _, temp_df = add_trophs(temp_df, analysis_sel_cols)
        _, temp_df = add_segments_home(temp_df, analysis_sel_cols)
        _, temp_df = add_segments_away(temp_df, analysis_sel_cols)
        _, temp_df = add_elixir_home(temp_df, analysis_sel_cols)
        _, temp_df = add_elixir_away(temp_df, analysis_sel_cols)
        _, temp_df = code_features(temp_df, analysis_sel_cols)
        _, temp_df = code_away_features(temp_df, analysis_sel_cols)
        _, temp_df = code_home_features(temp_df, analysis_sel_cols)
        temp_stats_df = temp_df.loc[:, stats_sel_cols]
        temp_df = temp_df.loc[:, analysis_sel_cols]

        ests = predict(temp_df, temp_stats_df, stats_sel_cols, lr_only)
        new_ests[range(i, inds)] = ests

        del temp_df
        del temp_stats_df
        ## create combinations by removing single cards
        i = i + iter_size

    ret_dict = {
        'norm_est': norm_est,
        'new_ests': new_ests,
        'len_first_list': len(explan_ind_01),
        'len_full_list': len(explan_ind),
        'home_card_list': home_card_list,
        'explan_ind': explan_ind,
    }

    REDIS_INSTANCE.expire(redis_key, 120)
    REDIS_INSTANCE.set(redis_key, pickle.dumps(ret_dict))
    REDIS_INSTANCE.expire(redis_channel + 'reco_data_ready', 120)
    REDIS_INSTANCE.set(redis_channel + 'reco_data_ready', 'yes'.encode('utf-8'))
    return


def modify_decks(home, away, card_cnt, n):
    rem_list = list(itertools.combinations(home, n))
    remove_iters = len(rem_list)

    add_cards = [x for x in range(0, card_cnt) if x not in home]
    add_list = list(itertools.combinations(add_cards, n))
    add_iters = len(add_list)

    new_decks = np.zeros([(remove_iters * add_iters), (2 * card_cnt)])
    explan_list = []
    i = 0
    while i < remove_iters:
        j = 0
        rem = []
        short_home = np.append([x for x in home if x not in rem_list[i]], away)
        rem.append(rem_list[i])
        while j < add_iters:
            add = []
            longer_home = np.append(short_home, add_list[j])
            new_decks[((i * add_iters) + j), longer_home] = 1
            add.append(add_list[j])
            explan_list.append([rem, add])
            j += 1
        i += 1

    return rem_list, add_list, explan_list, new_decks


def get_var_sizes(local_vars):
    for var, obj in local_vars:
        print(f'variable {var} size: {sys.getsizeof(obj)}')