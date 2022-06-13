import pandas as pd
import numpy as np

from The6ix.settings import ANALYSIS_SEL_COLS, STATS_SEL_COLS, SAMPLE_DECKS
from clashstats.models import Reports
from clashstats.score_utils import get_cards, get_segment, get_segment_away, get_elixr, get_elixr_away, add_trophs, \
                                    add_segments_home, add_segments_away, add_elixir_home, add_elixir_away, \
                                    code_features, code_home_features, code_away_features, predict, modify_decks, score_decks


def deck_analyzer(game_df):

    cards = get_cards()
    cards.sort_values(by=['card'], inplace=True)
    elixr = cards['elixr']
    home_cards = pd.get_dummies(cards['card']).drop(range(cards.shape[0]))
    home_card_list = list(home_cards.columns)
    away_card_list = [('a_' + card) for card in home_card_list]
    card_list_compare = [card.replace('_', ' ') for card in home_card_list]
    # adjustment for Pekka / mini-Pekka
    card_list_compare[75] = 'P.E.K.K.A'  # 108 amend if new cards inserted
    card_list_compare[67] = 'Mini P.E.K.K.A'

    sample_df = SAMPLE_DECKS.copy()

    away_sample_df = sample_df.loc[:, away_card_list].sample(frac=0.0025)
    del sample_df

    all_cards = home_card_list.copy()
    all_cards.extend(away_card_list)
    combin_base_df = game_df.loc[:, all_cards]

    player_cards = combin_base_df.T.squeeze().to_numpy().nonzero()
    home = player_cards[0][range(0, 8)]
    away = player_cards[0][range(8, 16)]
    card_cnt = int((home_cards.shape)[1])

    rem_list, add_list, explan_ind, new_decks = modify_decks(home, away, card_cnt, 1)

    base_deck = np.zeros((1, new_decks.shape[1]))
    base_deck[0, player_cards] = 1
    base_est = score_decks(base_deck, away_sample_df, all_cards, card_cnt, home_card_list)
    outcome_est = score_decks(new_decks, away_sample_df, all_cards, card_cnt, home_card_list)

    top_impr = (-outcome_est[:, card_cnt]).argsort()[:10]

    all_ests = np.append(base_est, outcome_est[top_impr, :], axis=0)
    for k, impr in enumerate(top_impr):
        home_away = np.asarray(np.nonzero(new_decks[impr, range(0, card_cnt)])).flatten()
        print(f'iterating through: {outcome_est[impr, card_cnt]}')
        print(f'secondary card: {k} - {[home_card_list[x] for x in home_away[0:8].tolist()]}')

        next_rem, next_add, next_explan, next_decks = modify_decks(home_away[0:8], away, card_cnt, 1)
        next_est = score_decks(next_decks, away_sample_df, all_cards, card_cnt, home_card_list)
        top_next = (-next_est[:, card_cnt]).argsort()[:10]

        all_ests = np.append(all_ests, next_est[top_next, :], axis=0)

    results = {
        'all_ests': all_ests,
        'home_card_list': home_card_list
    }
    return results






