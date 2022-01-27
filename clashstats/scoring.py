from The6ix.settings import STAT_FILES, CLUSTERING, HCLUSTERING, NEW_SEGMENT_MAP, SEGMENT_COLS, \
    CLASH_API, LBOUNDS, UBOUNDS, ANALYSIS_SEL_COLS, MAX_SEG, MAX_A_SEG, ELIXR_LBOUNDS, ELIXR_UBOUNDS
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import requests
import datetime
import copy
import time
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
    _, clan_df_v2 = add_trophs(clan_df_v2)
    _, clan_df_v2 = add_segments_home(clan_df_v2)
    _, clan_df_v2 = add_segments_away(clan_df_v2)
    _, clan_df_v2 = add_elixir_home(clan_df_v2)
    _, clan_df_v2 = add_elixir_away(clan_df_v2)

    #        results = get_probs_seg_clan(temp_df_v2)
    #    results.sort_values(by=['date', 'time'], ascending=False, inplace=True)
    #    if i == 0:
    #        df_out = results
    #    else:
    #        df_out = df_out.append(results, ignore_index=True)
    #    i += 1

    df_out = []
    lbounds = LBOUNDS

    return df_out, lbounds, success


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
    away_tag = list()
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
                    away_tag.append(game['opponent'][0]['tag'])
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
    result['away_tag'] = away_tag
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
    return success, result


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
    df_out['home_seg'] = df_out['home_seg'].astype(pd.Int32Dtype())
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
    df_out['away_seg'] = df_out['away_seg'].astype(pd.Int32Dtype())
    return df_out


def add_trophs(analyze_df):

    trophs = analyze_df['home_pb_lseason'].tolist()
    max_trophs = len(LBOUNDS)
    i = 1
    new_cols = list()
    while i <= max_trophs:
        col = 'trophs' + str(i).zfill(3)
        lower = LBOUNDS[i - 1]
        upper = UBOUNDS[i - 1]
        if i == max_trophs:
            analyze_df[col] = ((trophs >= lower).astype(int))
        else:
            analyze_df[col] = (((trophs < upper) * (trophs >= lower)).astype(int))
        new_cols.append(col)
        i += 1

    return new_cols, analyze_df


def add_segments_home(analyze_df):
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


def add_segments_away(analyze_df):
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


def add_elixir_home(analyze_df):

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
            analyze_df = pd.concat([analyze_df, pd.DataFrame(((elixir >= lower).astype(int)), columns=[col])], axis=1)
        else:
            analyze_df = pd.concat([analyze_df, pd.DataFrame((((elixir < upper) * (elixir >= lower)).astype(int)), columns=[col])], axis=1)
        new_cols.append(col)
        i += 1

    return new_cols, analyze_df


def add_elixir_away(analyze_df):
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
            analyze_df = pd.concat([analyze_df, pd.DataFrame(((elixir >= lower).astype(int)), columns=[col])], axis=1)
        else:
            analyze_df = pd.concat([analyze_df, pd.DataFrame((((elixir < upper) * (elixir >= lower)).astype(int)), columns=[col])], axis=1)
        new_cols.append(col)
        i += 1

    return new_cols, analyze_df