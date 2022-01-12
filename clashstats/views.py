from django.shortcuts import render, redirect
from django.http import HttpResponseNotFound
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import cardStatsForm, segmentForm, segmentsForm, cardsegtForm, findSegtForm, segmentFoundForm
from .scoring import get_segment, get_cards
from The6ix.settings import STAT_DATE, STAT_FILES
import pandas as pd
import numpy as np
import pickle
import math


@login_required()
def clashstats(request):
    return render(request, 'clashstats/menu.html', {'title': 'The6ixClan: Statistics', 'stat_date': STAT_DATE})


@login_required()
def cards(request):

    title = 'The6ixClan: Card Statistics'
    show_df = False
    f_name = STAT_FILES / 'csv/segment_summary_quart.csv'
    # pathname = os.path.abspath(os.path.dirname(__file__))
    df = pd.read_csv(f_name, index_col=None)

    pl_name = STAT_FILES / 'pickles/lbounds'
    pu_name = STAT_FILES / 'pickles/ubounds'
    lbounds = pickle.load(open(pl_name, "rb"))
    ubounds = pickle.load(open(pu_name, "rb"))

    filter_name = []
    i = 0
    max_i = len(ubounds)
    while i < max_i:
        filter_name.append(f'Personal best trophy range: {str(int(lbounds[i])).rjust(4," ")}-{str(int(ubounds[i])).rjust(4," ")}')
        i += 1
    filter_id = range(len(filter_name))
    filter_list = list(zip(filter_id, filter_name))

    sort_name = []
    sort_name.append("Alphabetic Order")
    sort_name.append("Most Popular")
    sort_name.append("Least Popular")
    sort_name.append("Highest Win Rate")
    sort_name.append("Lowest Win Rate")

    sort_id = range(len(sort_name))
    sort_list = list(zip(sort_id, sort_name))

    if request.method == 'POST':
        form = cardStatsForm(data=request.POST, filterList=filter_list, sortList=sort_list)
        if request.POST.get('Return') == 'Return to Menu':
            return redirect('clashstats-menu')
        elif form.is_valid():
            show_df = True
            quartiles = [1 + int(x) for x in form.cleaned_data.get('filts')]

            sort_order = int(form.cleaned_data.get('sorts'))

            card_name = []
            card_games = []
            card_win_ratio = []
            card_use_rate = []
            quart_filt = df.quartile.isin(quartiles)
            games = df[quart_filt].count_games
            wins = df[quart_filt].win_games

            max_cards = len(df.columns) - (8 + 1)  # stats + home_elixr
            i = 0
            while i < max_cards:
                curr_card = df.columns[8 + i]
                card_name.append(curr_card)
                card_games.append(sum(games * df[quart_filt].iloc[:, df.columns.get_loc(curr_card)]))
                card_use_rate.append(card_games[i] / sum(games))
                card_win_ratio.append(sum(wins * df[quart_filt].iloc[:, df.columns.get_loc(curr_card)]) / card_games[i])
                i += 1

            sum_df = pd.DataFrame(card_name, columns=['card_name'])
            sum_df['use_rate'] = card_use_rate
            sum_df['win_ratio'] = card_win_ratio

            if sort_order == 0:
                sum_df.sort_values(['card_name'], ascending=[1], inplace=True)
            elif sort_order == 1:
                sum_df.sort_values(['use_rate'], ascending=[0], inplace=True)
            elif sort_order == 2:
                sum_df.sort_values(['use_rate'], ascending=[1], inplace=True)
            elif sort_order == 3:
                sum_df.sort_values(['win_ratio', 'card_name'], ascending=[0, 0], inplace=True)
            elif sort_order == 4:
                sum_df.sort_values(['win_ratio', 'card_name'], ascending=[1, 0], inplace=True)

            display_df = sum_df.loc[:, ['card_name']]
            display_df['use_rate'] = pd.Series(["{0:.1f}%".format(val * 100) for val in sum_df['use_rate']], index=sum_df.index)
            display_df['win_ratio'] = pd.Series(["{0:.1f}%".format(val * 100) for val in sum_df['win_ratio']],
                                        index=sum_df.index)

            table_data = display_df.to_html(index=False, classes='table table-striped table-hover', header="true",
                                        justify="center")

            context = {
                'title': title,
                'form': form,
                'show_df': show_df,
                'table_data': table_data
            }
            return render(request, 'clashstats/cards.html', context)

        else:
            context = {
                'title': title,
                'form': form,
                'show_df': show_df
            }
            return render(request, 'clashstats/cards.html', context)

    form = cardStatsForm(filterList=filter_list, sortList=sort_list)
    context = {
                'title': title,
                'form': form,
                'show_df': show_df
    }
    return render(request, 'clashstats/cards.html', context)


@login_required()
def segment(request, pk):

    title = 'The6ixClan: Segment Close-Up'
    show_df = False
    f_name = STAT_FILES / 'csv/segment_summary.csv'
    # pathname = os.path.abspath(os.path.dirname(__file__))
    df = pd.read_csv(f_name, index_col=None)

    segment_list = df['home_seg'].unique()
    segment_list = np.sort(segment_list)

    if pk not in segment_list:
        html = '<a href = "http://the6ixclan.ca"> Return to The6ixclan.ca </a>'
        return HttpResponseNotFound(f'<h2>Segment {pk} does not exist.<h2><br>' + html)
    else:
        show_df = True

    if request.method == 'POST':
        form = segmentForm(data=request.POST)
        if request.POST.get('Return') == 'Return to All Segments':
            return redirect('clashstats-segments')

    form = segmentForm()
    segment_ind = df.index[df['home_seg'] == pk][0]
    segment_name = df['seg_name'].iloc[segment_ind]
    segment_display = segment_name[0:8] + segment_name[17:100]
    homogeneity = segment_name[9:15]
    max_cards = len(df.columns) - (7 + 1)  # stats + home_elixr
    card_names = []
    card_stats = []
    i = 0
    while i < max_cards:
         card_names.append(df.columns[7 + i])
         card_stats.append(df.iloc[segment_ind, (7 + i)])
         i += 1

    card_df = pd.DataFrame(card_names, columns=['card'])
    card_df['use'] = card_stats
    card_df = card_df.sort_values('use', ascending=False)

    display_df = card_df.loc[:, ['card']]  # seg_name
    display_df['use_rate'] = pd.Series(["{0:.1f}%".format(val * 100) for val in card_df['use']], index=card_df.index)

    table_data = display_df.to_html(index=False, classes='table table-striped table-hover', header="true",
                                justify="center")

    context = {
        'title': title,
        'segment_name': segment_display,
        'homogeneity': homogeneity,
        'form': form,
        'show_df': show_df,
        'table_data': table_data,
    }
    return render(request, 'clashstats/segment.html', context)


@login_required()
def segments(request):

    title = 'The6ixClan: Card Statistics'
    show_df = False
    f_name = STAT_FILES / 'csv/segment_summary_quart.csv'
    # pathname = os.path.abspath(os.path.dirname(__file__))
    df = pd.read_csv(f_name, index_col=None)
    all_segs = np.sort(df.seg_name.unique())
    seg_list = list(zip(pd.Series(range(len(all_segs))), all_segs))

    pl_name = STAT_FILES / 'pickles/lbounds'
    pu_name = STAT_FILES / 'pickles/ubounds'
    lbounds = pickle.load(open(pl_name, "rb"))
    ubounds = pickle.load(open(pu_name, "rb"))

    filter_name = []
    i = 0
    max_i = len(ubounds)
    while i < max_i:
        filter_name.append(f'Personal best trophy range: {str(int(lbounds[i])).rjust(4," ")}-{str(int(ubounds[i])).rjust(4," ")}')
        i += 1

    filter_id = range(len(filter_name))
    filter_list = list(zip(filter_id, filter_name))

    confidence_name = []
    confidence_name.append("No confidence interval applied")
    confidence_name.append("Only show segments with differences at 90% confidence")
    confidence_name.append("Only show segments with differences at 95% confidence")
    confidence_name.append("Only show segments with differences at 98% confidence")
    confidence_name.append("Only show segments with differences at 99% confidence")

    confidence_id = range(len(confidence_name))
    confidence_list = list(zip(confidence_id, confidence_name))

    sort_name = []
    sort_name.append("Segment No. Order")
    sort_name.append("Most Popular")
    sort_name.append("Least Popular")
    sort_name.append("Highest Win Rate")
    sort_name.append("Lowest Win Rate")

    sort_id = range(len(sort_name))
    sort_list = list(zip(sort_id, sort_name))

    if request.method == 'POST':
        form = segmentsForm(data=request.POST, segList=seg_list, filterList=filter_list, confList=confidence_list, sortList=sort_list)
        if request.POST.get('Return') == 'Return to Menu':
            return redirect('clashstats-menu')
        elif form.is_valid():
            if request.POST.get('Segment') == 'View Segment Details':
                pk = 1 + int(form.cleaned_data.get('sgmts'))
                return redirect('clashstats-segment', pk)
            show_df = True

            quartiles = [1 + int(x) for x in form.cleaned_data.get('filts')]
            conf_int = int(form.cleaned_data.get('confs'))
            sort_order = int(form.cleaned_data.get('sorts'))

            mean_total = df.win_games.sum() / df.count_games.sum()

            scan_df = df[df.quartile.isin(quartiles)]
            i = 0
            zero_data = np.zeros(shape=(len(all_segs), 6))
            sum_df = pd.DataFrame(zero_data, columns=['games', 'wins', 'win_ratio',
                                                      'upper', 'lower', 'signif_test'])
            if conf_int == 0:
                z_val = 0
            elif conf_int == 1:
                z_val = 1.645
            elif conf_int == 2:
                z_val = 1.960
            elif conf_int == 3:
                z_val = 2.36
            elif conf_int == 4:
                z_val = 2.576

            sum_df.insert(0, 'seg_name', all_segs)
            while i < len(all_segs):
                sum_df.iloc[i, sum_df.columns.get_loc('games')] = scan_df.count_games.loc[
                    scan_df['seg_name'] == all_segs[i]].sum()
                sum_df.iloc[i, sum_df.columns.get_loc('wins')] = scan_df.win_games.loc[
                    scan_df['seg_name'] == all_segs[i]].sum()
                sig_calc = math.sqrt(
                    mean_total * sum_df.iloc[i, sum_df.columns.get_loc('games')] * (1 - mean_total)) * z_val  # 98% CI
                sum_df.iloc[i, sum_df.columns.get_loc('upper')] = ((mean_total * sum_df.games.iloc[i]) + sig_calc)
                sum_df.iloc[i, sum_df.columns.get_loc('lower')] = ((mean_total * sum_df.games.iloc[i]) - sig_calc)
                if (sum_df.iloc[i, sum_df.columns.get_loc('upper')] < sum_df.iloc[i, sum_df.columns.get_loc('wins')] or
                        sum_df.iloc[i, sum_df.columns.get_loc('lower')] > sum_df.iloc[
                            i, sum_df.columns.get_loc('wins')]):
                    sum_df.iloc[i, sum_df.columns.get_loc('signif_test')] = 1
                i += 1
            sum_df['win_ratio'] = sum_df['wins'] / sum_df['games']

            # sum_df = sum_df.iloc[]

            i = 1
            filter_data = []
            while i < 1 + len(filter_name):
                if i < 5:
                    if i in quartiles:
                        filter_data.append(i - 1)
                else:
                    if (i - 4) == conf_int:
                        filter_data.append(i - 1)
                i += 1

            if conf_int > 0:
                sum_df = sum_df.loc[sum_df.signif_test == 1]

            if sort_order == 0:
                sum_df.sort_values(['seg_name'], ascending=[1], inplace=True)
            elif sort_order == 1:
                sum_df.sort_values(['games'], ascending=[0], inplace=True)
            elif sort_order == 2:
                sum_df.sort_values(['games'], ascending=[1], inplace=True)
            elif sort_order == 3:
                sum_df.sort_values(['win_ratio', 'seg_name'], ascending=[0, 0], inplace=True)
            elif sort_order == 4:
                sum_df.sort_values(['win_ratio', 'seg_name'], ascending=[1, 0], inplace=True)

            display_df = sum_df.loc[:, ['seg_name']]  # seg_name
            display_df['games'] = sum_df.games.map('{:,.0f}'.format)
            display_df['victories'] = sum_df.wins.map('{:,.0f}'.format)
            display_df['win_ratio'] = pd.Series(["{0:.1f}%".format(val * 100) for val in sum_df['win_ratio']],
                                                index=sum_df.index)

            table_data = display_df.to_html(index=False, classes='table table-striped table-hover',
                                                   header="true",
                                                   justify="center")

            context = {
                'title': title,
                'form': form,
                'show_df': show_df,
                'table_data': table_data,
            }

            return render(request, 'clashstats/segments.html', context)

        context = {
             'title': title,
             'form': form,
             'show_df': show_df
            }

        return render(request, 'clashstats/segments.html', context)

    form = segmentsForm(segList=seg_list, filterList=filter_list, confList=confidence_list, sortList=sort_list)
    context = {
                'title': title,
                'form': form,
                'show_df': show_df
            }
    return render(request, 'clashstats/segments.html', context)


@login_required()
def cardsegt(request):

    title = 'The6ixClan: Card Statistics'
    show_df = False
    f_name = STAT_FILES / 'csv/segment_summary_quart.csv'
    # pathname = os.path.abspath(os.path.dirname(__file__))
    df = pd.read_csv(f_name, index_col=None)

    max_cards = len(df.columns) - (8 + 1)  # stats + home_elixr
    card_name = []
    i = 0
    while i < max_cards:
        card_name.append(df.columns[8 + i])
        i += 1
    card_id = range(len(card_name))
    card_list = list(zip(card_id, card_name))

    sort_name = []
    sort_name.append("Segment No. Order")
    sort_name.append("Highest Use Rate")

    sort_id = range(len(sort_name))
    sort_list = list(zip(sort_id, sort_name))

    pl_name = STAT_FILES / 'pickles/lbounds'
    pu_name = STAT_FILES / 'pickles/ubounds'
    lbounds = pickle.load(open(pl_name, "rb"))
    ubounds = pickle.load(open(pu_name, "rb"))

    rank_name = []
    i = 0
    max_i = len(ubounds)
    while i < max_i:
        rank_name.append(f'Sort by use rate for trophy range: {str(int(lbounds[i])).rjust(4," ")}-{str(int(ubounds[i])).rjust(4," ")}')
        i += 1

    rank_id = range(len(rank_name))
    rank_list = list(zip(rank_id, rank_name))


    if request.method == 'POST':
        form = cardsegtForm(data=request.POST, cardList=card_list, sortList=sort_list, rankList=rank_list)
        if request.POST.get('Return') == 'Return to Menu':
            return redirect('clashstats-menu')
        elif form.is_valid():
            show_df = True

            card_sel = int(form.cleaned_data.get('cards'))
            sort_order = int(form.cleaned_data.get('sorts'))
            rank_order = int(form.cleaned_data.get('ranks'))

            card_seln = card_name[card_sel]
            seg_list = df.seg_name.unique()

            usage = pd.DataFrame(np.sort(seg_list), columns=['seg_name']).reset_index()

            col01 = df[df.quartile == 1].iloc[:, [1, df.columns.get_loc(card_seln)]]
            col02 = df[df.quartile == 2].iloc[:, [1, df.columns.get_loc(card_seln)]]
            col03 = df[df.quartile == 3].iloc[:, [1, df.columns.get_loc(card_seln)]]
            col04 = df[df.quartile == 4].iloc[:, [1, df.columns.get_loc(card_seln)]]

            usage['quart_01'] = col01.set_index('seg_name').reindex(usage['seg_name']).fillna(0).reset_index().iloc[:, 1]
            usage['quart_02'] = col02.set_index('seg_name').reindex(usage['seg_name']).fillna(0).reset_index().iloc[:, 1]
            usage['quart_03'] = col03.set_index('seg_name').reindex(usage['seg_name']).fillna(0).reset_index().iloc[:, 1]
            usage['quart_04'] = col04.set_index('seg_name').reindex(usage['seg_name']).fillna(0).reset_index().iloc[:, 1]

            if sort_order == 0:
                usage.sort_values(['seg_name'], ascending=[1], inplace=True)
            elif rank_order == 0:
                usage.sort_values(['quart_01'], ascending=[0], inplace=True)
            elif rank_order == 1:
                usage.sort_values(['quart_02'], ascending=[0], inplace=True)
            elif rank_order == 2:
                usage.sort_values(['quart_03'], ascending=[0], inplace=True)
            elif rank_order == 3:
                usage.sort_values(['quart_04'], ascending=[0], inplace=True)

            display_df = pd.DataFrame(usage.seg_name, columns=['seg_name'])
            display_df['Quartile 1'] = pd.Series(["{0:.1f}%".format(val * 100)
                                                  for val in usage['quart_01']], index=usage.index)
            display_df['Quartile 2'] = pd.Series(["{0:.1f}%".format(val * 100)
                                                  for val in usage['quart_02']], index=usage.index)
            display_df['Quartile 3'] = pd.Series(["{0:.1f}%".format(val * 100)
                                                  for val in usage['quart_03']], index=usage.index)
            display_df['Quartile 4'] = pd.Series(["{0:.1f}%".format(val * 100)
                                                  for val in usage['quart_04']], index=usage.index)

            table_data = display_df.to_html(index=False, classes='table table-striped table-hover',
                                                header="true", justify="center")
            context = {
                'title': title,
                'form': form,
                'show_df': show_df,
                'table_data': table_data,
            }

            return render(request, 'clashstats/cardsegt.html', context)

        context = {
             'title': title,
             'form': form,
             'show_df': show_df
            }

        return render(request, 'clashstats/cardsegt.html', context)

    form = cardsegtForm(cardList=card_list, sortList=sort_list, rankList=rank_list)
    context = {
                'title': title,
                'form': form,
                'show_df': show_df
            }
    return render(request, 'clashstats/cardsegt.html', context)

@login_required()
def findsegt(request):
    title = 'The6ixClan: Find a Segment'
    show_df = False

    f_name = STAT_FILES / 'csv/segment_summary.csv'
    # pathname = os.path.abspath(os.path.dirname(__file__))
    df = pd.read_csv(f_name, index_col=None)
    deck_df = df.drop(df.columns[range(0, 7)], axis=1)
    deck_df.drop(deck_df.index, inplace=True)
    deck_df = deck_df.append(pd.Series(0, index=deck_df.columns), ignore_index=True)

    max_cards = len(df.columns) - (7 + 1)  # stats + home_elixr
    card_name = []
    i = 0
    while i < max_cards:
        card_name.append(df.columns[7 + i])
        i += 1
    card_id = range(len(card_name))
    card_list = list(zip(card_id, card_name))

    if request.method == 'POST':
        form = findSegtForm(data=request.POST, cardList=card_list)
        if request.POST.get('Return') == 'Return to Menu':
            return redirect('clashstats-menu')
        elif request.POST.get('Clear') == 'Clear Entries' and form.is_valid():
            form = findSegtForm(data={}, cardList=card_list)
            context = {
                'title': title,
                'form': form,
                'show_df': show_df,
            }
            return render(request, 'clashstats/findsegt.html', context)
        elif form.is_valid():
            show_df = True
            cards = [int(x) for x in form.cleaned_data.get('cards')]
            if len(cards) != 8:
                show_df = False
                if len(cards) < 8:
                    if len(cards) == 1:
                        messages.warning(request, f'Must select 8 cards to derive segment.  Only {len(cards)} card is currently selected.')
                    else:
                        messages.warning(request, f'Must select 8 cards to derive segment.  Only {len(cards)} cards are currently selected.')
                else:
                    messages.warning(request,
                                     f'Must select only 8 cards to derive segment; {len(cards)} cards are currently selected.')
                context = {
                    'title': title,
                    'form': form,
                    'show_df': show_df,
                }
                return render(request, 'clashstats/findsegt.html', context)

            for card in cards:
                deck_df.loc[0, card_list[card][1]] = 1

            deck_df = get_segment(deck_df)
            segmentID = int(deck_df['home_seg'])
            request.session['deck_df'] = deck_df.to_json()
            return redirect('clashstats-segtrslt', segmentID)

        else:
            context = {
                'title': title,
                'form': form,
                'show_df': show_df
            }
            return render(request, 'clashstats/findsegt.html', context)

    form = findSegtForm(cardList=card_list)
    context = {
                'title': title,
                'form': form,
                'show_df': show_df
    }
    return render(request, 'clashstats/findsegt.html', context)


@login_required()
def segtrslt(request, pk):

    title = 'The6ixClan: Segment Identification'
    show_df = True
    form = segmentFoundForm()

    deck_df = pd.read_json(request.session['deck_df'], dtype=False)
    elixr = deck_df.home_elix.iloc[0]

    f_name = STAT_FILES / 'csv/segment_summary.csv'
    # pathname = os.path.abspath(os.path.dirname(__file__))

    df = pd.read_csv(f_name, index_col=None)

    segment_list = df['home_seg'].unique()
    segment_list = np.sort(segment_list)

    if pk not in segment_list:
        html = '<a href = "http://the6ixclan.ca"> Return to The6ixclan.ca </a>'
        return HttpResponseNotFound(f'<h2>Segment {pk} does not exist.<h2><br>' + html)
    else:
        show_df = True

    if request.method == 'POST':
        form = segmentFoundForm(data=request.POST)
        if request.POST.get('Return') == "Return to Find Your Deck's Segment":
            return redirect('clashstats-findsegt')


    segment_id = pk - 1

    segment_name = df['seg_name'].iloc[segment_id]
    segment_display = segment_name[0:8] + segment_name[17:100]
    homogeneity = segment_name[9:15]

    max_cards = len(df.columns)-(7+1) # stats + home_elixr
    alt_card_names = []
    user_card_names = []
    alt_card_stats = []
    user_card_stats = []
    i = 0
    while i < max_cards:
        if int(deck_df.iloc[0, i]) == 1:
            user_card_names.append(df.columns[7+i])
            user_card_stats.append(df.iloc[segment_id, (7+i)])
        else:
            alt_card_names.append(df.columns[7+i])
            alt_card_stats.append(df.iloc[segment_id, (7+i)])
        i += 1

    user_df = pd.DataFrame(user_card_names, columns=['card'])
    user_df['use'] = user_card_stats
    user_df = user_df.sort_values('use', ascending=False)

    user_display_df = user_df.loc[:, ['card']] # seg_name
    user_display_df['use_rate'] = pd.Series(["{0:.1f}%".format(val * 100) for val in user_df['use']], index=user_df.index)

    alt_df = pd.DataFrame(alt_card_names, columns=['card'])
    alt_df['use'] = alt_card_stats
    alt_df = alt_df.sort_values('use', ascending=False)

    alt_display_df = alt_df.loc[:, ['card']] # seg_name
    alt_display_df['use_rate'] = pd.Series(["{0:.1f}%".format(val * 100) for val in alt_df['use']], index=alt_df.index)

    table_data = user_display_df.to_html(index=False, classes='table table-striped table-hover',
                                        header="true", justify="center")
    alt_data = alt_display_df.to_html(index=False, classes='table table-striped table-hover',
                                         header="true", justify="center")
    context = {
                'title': title,
                'form': form,
                'segment_name': segment_display,
                'homogeneity': homogeneity,
                'show_df': show_df,
                'table_data': table_data,
                'alt_data': alt_data,
            }
    return render(request, 'clashstats/segtrslt.html', context)