import copy
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseNotFound, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import cardStatsForm, segmentForm, segmentsForm, cardsegtForm, findSegtForm, segmentFoundForm, clanReptForm, memberSlctForm, memberReptForm, winDeepForm
from .score_utils import get_segment, get_elixr, get_clan, auto_pull, auto_analyze, mid, rowIndex
from The6ix.settings import STAT_DATE, STAT_FILES, BASE_URL, SEGMENT_SUMMARY, SEGMENT_SUMMARY_QUART, LBOUNDS, UBOUNDS
from .models import Reports
from django_celery_results.models import TaskResult
from .tasks import analyze_deck
import pandas as pd
import numpy as np
import pickle
import datetime
import math
from scipy.stats import pearsonr


@login_required()
def clashstats(request):
    return render(request, 'clashstats/menu.html', {'title': 'The6ixClan: Statistics', 'stat_date': STAT_DATE})


@login_required()
def cards(request):

    title = 'The6ixClan: Card Statistics'
    show_df = False
    df = copy.deepcopy(SEGMENT_SUMMARY_QUART)

    lbounds = copy.deepcopy(LBOUNDS)
    ubounds = copy.deepcopy(UBOUNDS)

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
                games_divisor = sum(games)
                if games_divisor == 0:
                    games_divisor = 1
                card_use_rate.append(card_games[i] / games_divisor)
                card_games_divisor = card_games[i]
                if card_games_divisor == 0:
                    card_games_divisor = 1
                card_win_ratio.append(sum(wins * df[quart_filt].iloc[:, df.columns.get_loc(curr_card)]) / card_games_divisor)
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
    df = copy.deepcopy(SEGMENT_SUMMARY)

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
    df = copy.deepcopy(SEGMENT_SUMMARY_QUART)
    all_segs = np.sort(df.seg_name.unique())
    seg_list = list(zip(pd.Series(range(len(all_segs))), all_segs))

    lbounds = copy.deepcopy(LBOUNDS)
    ubounds = copy.deepcopy(UBOUNDS)

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
    df = copy.deepcopy(SEGMENT_SUMMARY_QUART)
    df = df.drop(columns=['homogeneity']).reset_index(drop=True)

    max_cards = len(df.columns) - (7 + 1)  # stats + home_elixr
    card_name = []
    i = 0
    while i < max_cards:
        card_name.append(df.columns[7 + i])
        i += 1
    card_id = range(len(card_name))
    card_list = list(zip(card_id, card_name))

    sort_name = []
    sort_name.append("Segment No. Order")
    sort_name.append("Highest Use Rate")

    sort_id = range(len(sort_name))
    sort_list = list(zip(sort_id, sort_name))

    lbounds = copy.deepcopy(LBOUNDS)
    ubounds = copy.deepcopy(UBOUNDS)

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

            col01 = df[df.quartile == 1].iloc[:, [0, df.columns.get_loc(card_seln)]]
            col02 = df[df.quartile == 2].iloc[:, [0, df.columns.get_loc(card_seln)]]
            col03 = df[df.quartile == 3].iloc[:, [0, df.columns.get_loc(card_seln)]]
            col04 = df[df.quartile == 4].iloc[:, [0, df.columns.get_loc(card_seln)]]

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

    df = copy.deepcopy(SEGMENT_SUMMARY)
    deck_df = df.drop(df.columns[range(0, 6)], axis=1)
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

            deck_df = get_elixr(deck_df)
            deck_df = get_segment(deck_df)
            segmentID = int(deck_df['home_seg'])
            request.session['find_seg_deck_df'] = deck_df.to_json()
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

    deck_df = pd.read_json(request.session['find_seg_deck_df'], dtype=False)
    elixr = deck_df.home_elixr.iloc[0]

    df = copy.deepcopy(SEGMENT_SUMMARY)

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


@login_required()
def clanrept(request):
    title = 'The6ixClan: Clan Report Menu'
    form = clanReptForm()

    if request.method == 'POST':
        form = clanReptForm(data=request.POST)
        if request.POST.get('Return') == 'Return to Menu':
            return redirect('clashstats-menu')
        if request.POST.get("Pull Recent Stats for 'The6ix' Clan") == "Pull Recent Stats for 'The6ix' Clan":
            request.session['clan'] = '#YP8GPGYQ'
            return redirect('clashstats-membslct')
        if request.POST.get("Pull Recent Stats for 'Honeypie' Clan") == "Pull Recent Stats for 'Honeypie' Clan":
            request.session['clan'] = '#Q2JR8C9V'
            return redirect('clashstats-membslct')
        if request.POST.get("Pull Recent Stats for '50 Stars' Clan") == "Pull Recent Stats for '50 Stars' Clan":
            request.session['clan'] = '#QV2VP28L'
            return redirect('clashstats-membslct')
        if request.POST.get("Pull Recent Stats for 'Avatar' Clan") == "Pull Recent Stats for 'Avatar' Clan":
            request.session['clan'] = '#PY8VPYC0'
            return redirect('clashstats-membslct')
        if request.POST.get("Pull Recent Stats for 'Pivot Family' Clan") == "Pull Recent Stats for 'Pivot Family' Clan":
            request.session['clan'] = '#2C0LVR9P'
            return redirect('clashstats-membslct')
        if request.POST.get("Pull Recent Stats for 'WARTube' Clan") == "Pull Recent Stats for 'WARTube' Clan":
            request.session['clan'] = '#L0LC9R8R'
            return redirect('clashstats-membslct')
        if request.POST.get("Pull Recent Stats for 'Skeleton Scoot' Clan") == "Pull Recent Stats for 'Skeleton Scoot' Clan":
            request.session['clan'] = '#YUGYYJ0V'
            return redirect('clashstats-membslct')
        if request.POST.get("Pull Recent Stats for 'CLANwithSHANE' Clan") == "Pull Recent Stats for 'CLANwithSHANE' Clan":
            request.session['clan'] = '#CGJ9GGU'
            return redirect('clashstats-membslct')
        if request.POST.get("Pull Recent Stats for 'PandaScheme' Clan") == "Pull Recent Stats for 'PandaScheme' Clan":
            request.session['clan'] = '#YU2RQG9'
            return redirect('clashstats-membslct')

    context = {
        'title': title,
        'form': form,
    }
    return render(request, 'clashstats/clanrept.html', context)


@login_required()
def membslct(request):
    title = 'The6ixClan: Clan Member Select'
    clan = request.session['clan']
    err_code, member_df = get_clan(clan)
    if err_code == 99:
        messages.warning(request, f'Clash Royale API is down.  Please notify Remember_215 in the clan.')
        member_list = []
    else:
        member_names = []
        member_tags = []
        member_id = []

        max_members = len(member_df)
        i = 0
        while i < max_members:
            member_id.append(i)
            member_tags.append(member_df.tag.iloc[i])
            member_names.append(member_df.name.iloc[i])
            i += 1

        df = pd.DataFrame(member_id, columns=['member_id'])
        df['member_names'] = member_names

        member_list = list(zip(df.member_id.to_list(), df.member_names.to_list()))

    if request.method == 'POST':
        form = memberSlctForm(data=request.POST, memberList=member_list)
        if request.POST.get('Return to Clan Select') == 'Return to Clan Select':
            return redirect('clashstats-clanrept')
        elif request.POST.get('Return') == 'Return to Menu':
            return redirect('clashstats-menu')
        elif request.POST.get('Clear Form') == 'Clear Form':
            form = memberSlctForm(data={}, memberList=member_list)
            context = {
                'title': title,
                'form': form
            }
            return render(request, 'clashstats/membslct.html.html', context)
        elif request.POST.get("Pull Statistics for All Clan Members") == "Pull Statistics for All Clan Members":
            members = [int(x) for x in range(0, len(member_list))]
            request.session['member_sels'] = members
            request.session['member_list'] = member_list
            request.session['member_df'] = member_df.to_json()
            request.session['clan'] = clan
            request.session['curr_page'] = 1
            return redirect('clashstats-membrept')
        elif request.POST.get("Pull Statistics for Selections Below") == "Pull Statistics for Selections Below" and form.is_valid():
            members = [int(x) for x in form.cleaned_data.get('members')]
            request.session['member_sels'] = members
            request.session['member_list'] = member_list
            request.session['member_df'] = member_df.to_json()
            request.session['clan'] = clan
            request.session['curr_page'] = 1
            return redirect('clashstats-membrept')

        context = {
            'title': title,
            'form': form,
        }
        return render(request, 'clashstats/membslct.html', context)
    form = memberSlctForm(memberList=member_list)
    context = {
        'title': title,
        'form' : form,
    }
    return render(request, 'clashstats/membslct.html', context)


@login_required()
def membrept(request):
    title = 'The6ixClan: Member Report'
    show_df = False
    show_p = False
    try:
        clan = request.session['clan']
        member_list = request.session['member_list']
        member_sels = request.session['member_sels']
        member_df = pd.read_json(request.session['member_df'], dtype=False)
        curr_page = request.session['curr_page']
        if len(member_sels) == 1:
            dyn_title = 'Member Report'
        else:
            dyn_title = 'Member Reports'
    except:
        clan = []
        member_list = []
        member_sels = []
        curr_page = 1
        messages.warning(request, f'Error has occurred.')
        dyn_title = 'The6ixClan: Member Report'
    if request.method == 'POST':
        form = memberReptForm(data=request.POST)
        if request.POST.get('Return to Clan Select') == 'Return to Clan Select':
            return redirect('clashstats-clanrept')
        elif request.POST.get('Return to Menu') == 'Return to Menu':
            return redirect('clashstats-menu')
        elif request.POST.get('Next Member') == 'Next Member':
            curr_page = min(len(member_sels), (curr_page + 1))
            request.session['curr_page'] = curr_page
        elif request.POST.get('Previous Member') == 'Previous Member':
            curr_page = max(1, (curr_page - 1))
            request.session['curr_page'] = curr_page

    result_df, lbounds, success = auto_pull(member_df.iloc[[member_sels[curr_page-1]]])

    if success == 0:
        messages.warning(request, 'No ladder games played for this clan member.')
        show_df = False
        show_p = False
        memberStats = ""
        form = memberReptForm()
        context = {
            'title': title,
            'show_df': show_df,
            'dyn_title': dyn_title,
            'curr_page': curr_page,
            'max_page': len(member_sels),
            'memberStats': memberStats,
            'form': form,
        }
        return render(request, 'clashstats/membrept.html', context)

    show_df = True
    df = result_df.copy()
    df = df.sort_values(by=['home_tag', 'game_dt', 'game_tm'], ascending=[True, False, False]).reset_index()
    df_total = df.groupby('home_tag') \
        .agg({'outcome': 'sum', 'expected_win_ratio': 'sum', 'away_seg': 'count'}).reset_index()
    df_total = df_total.rename(columns={'away_seg': 'cnt', 'outcome': 'win'})
    df_total = df_total.sort_values(by=['home_tag']).reset_index()

    df = df.rename(columns={'away_seg': 'opponent_seg', 'home_seg': 'player_seg'})
    display_df = df[['home_tag', 'away_tag']].reset_index()
    #  display_df['home_tag'] = df.apply(lambda x: f'<a href="https://royaleapi.com/player/{(mid(x["home_tag"], 1, 9).rstrip())}/battles">{x["home_name"]}</a>', axis=1)
    display_df['away_tag'] = df.apply(lambda x: f'<a href="https://royaleapi.com/player/{(mid(x["away_tag"], 1, 9)).rstrip()}/battles">{x["away_name"]}</a>', axis=1)
    display_df['player_seg'] = df.apply(lambda x: f'<a href="{BASE_URL}/clashstats/segment/{(str(x["player_seg"])).strip()}">{str(x["player_seg"]).strip()}</a>', axis=1)
    display_df['opponent_seg'] = df.apply(lambda x: f'<a href="{BASE_URL}/clashstats/segment/{(str(x["opponent_seg"])).strip()}">{str(x["opponent_seg"]).strip()}</a>', axis=1)
    display_df['win'] = df['outcome'].values
    display_df['exp_win_ratio'] = pd.Series(["{0:.1f}%".format(val * 100)
                                             for val in df['expected_win_ratio']], index=df.index).values
    display_df['exp_win_ratio'] = display_df.apply(lambda x: f'<a href="{BASE_URL}/clashstats/win_deep/{rowIndex(x)}">{x.exp_win_ratio}</a>', axis=1)

    request.session['deep_dive_games'] = df.to_json()

    display_df['time'] = df['game_tm'].values
    display_df['date'] = df['game_dt'].values

    display_df = display_df[['date', 'time', 'away_tag', 'player_seg', 'opponent_seg', 'win', 'exp_win_ratio']]

    memberStats = display_df.to_html(index=False, classes='table table-striped table-hover',
                                          header="true", justify="center", escape=False)

    game_cnt = "{:.0f}".format(float(df_total.cnt))
    act_win_ratio = "{:.1%}".format(float(df_total.win/df_total.cnt))
    exp_win_ratio = "{:.1%}".format(float(df_total.expected_win_ratio/df_total.cnt))
    if len(df) < 5:
        show_p = False
        x = 0
        y = 0
    else:
        show_p = True
        x, y = pearsonr(df['expected_win_ratio'], df['outcome'])
    pearson_r = "{:.1%}".format(float(x))
    pvalue = "{:.1%}".format(float(y))

    form = memberReptForm()
    context = {
        'title': title,
        'show_df': show_df,
        'show_p': show_p,
        'dyn_title': dyn_title,
        'curr_page': curr_page,
        'max_page': len(member_sels),
        'memberStats': memberStats,
        'player': member_df.iloc[[member_sels[curr_page-1]],1].values[0],
        'player_tag': mid(df['home_tag'].iloc[0],1,9).rstrip(),
        'game_cnt': game_cnt,
        'act_win_ratio': act_win_ratio,
        'exp_win_ratio': exp_win_ratio,
        'pearson_r': pearson_r,
        'p_value': pvalue,
        'form' : form,
    }
    return render(request, 'clashstats/membrept.html', context)


@login_required()
def win_deep(request, pk):
    title = 'The6ixClan: Game Statistic Deep Dive'
    dyn_title = 'Probability Deep Dive'
    show_df = False
    request.session['win_deep_show_df'] = show_df
    results = []
    try:
        games = pd.read_json(request.session['deep_dive_games'], dtype=False)
    except:
        html = '<a href = "http://the6ixclan.ca"> Return to The6ixclan.ca </a>'
        return HttpResponseNotFound(f'<h2>Game {pk} cannot be accessed at this time.<h2><br>' + html)
    if pk > len(games) or pk < 1:
        html = '<a href = "http://the6ixclan.ca"> Return to The6ixclan.ca </a>'
        return HttpResponseNotFound(f'<h2>Segment {pk} does not exist.<h2><br>' + html)
    else:
        results = auto_analyze(games.iloc[[pk - 1]])
    form = winDeepForm()
    if request.method == 'POST':
        form = winDeepForm(data=request.POST)
        if request.POST.get('Return to Member Report') == 'Return to Member Report':
            return redirect('clashstats-membrept')
        elif request.POST.get('Return to Menu') == 'Return to Menu':
            return redirect('clashstats-menu')
        elif (request.POST.get('Build Deck Analysis') == 'Build Deck Analysis'):
            # report_id = analyze_deck.delay(games.iloc[[pk - 1]])
            report_name = games.iloc[[pk-1]]['home_name'].to_string(index=False) + ' vs. ' + games.iloc[[pk-1]]['away_name'].to_string(index=False)
            report_id = analyze_deck.delay(games.iloc[[pk - 1]])

            created = datetime.datetime.now()
            report = Reports(task_id=report_id.task_id, rept_name=report_name[0:36], rept_type='deck opt', status='submitted',
                             created=created, user=request.user, )
            report.save()
            messages.success(request, f'Your deck analysis has been submitted and will take approx 20 mins to run. Report will be available for 24hrs.')
            return redirect('clashstats-viewrepts')

    r1 = results.get("intercept")
    r2 = r1 * results.get("lseason_trophies_impact")
    r3 = r1 * (1 + results.get("lseason_trophies_impact")) * results.get("bseason_trophies_impact")
    r4 = r1 * (1 + results.get("lseason_trophies_impact")) * (1 + results.get("bseason_trophies_impact")) * results.get("exp_trophies_impact")
    r5 = r1 * (1 + results.get("lseason_trophies_impact")) * (1 + results.get("bseason_trophies_impact")) * (1 + results.get("exp_trophies_impact")) * results.get("level_trophies_impact")
    r6 = r1 * (1 + results.get("lseason_trophies_impact")) * (1 + results.get("bseason_trophies_impact")) * (1 + results.get("exp_trophies_impact")) * (1 + results.get("level_trophies_impact")) * results.get("deck_impact")
    r7 = r1 * (1 + results.get("deck_impact"))

    context = {
        'title': title,
        'dyn_title': dyn_title,
        'player_name': games.loc[(pk-1), 'home_name'],
        'away_name': games.loc[(pk-1), 'away_name'],
        'player_tag': mid(games.loc[(pk-1), 'home_tag'], 1, 9).rstrip(),
        'away_tag': mid(games.loc[(pk-1), 'away_tag'], 1, 9).rstrip(),
        'row_int': f'Starting estimate (regression intercept):',
        'intercept': f'{results.get("intercept"):.1%}',
        'cintercept': f'{r1:.1%}',
        'row_lsg': f'{games.loc[(pk-1), "home_name"]} last season gap to 5700',
        'last_season_gap':  f'{results.get("lseason_trophies_impact"):.1%}',
        'clsg': f'{r2:.1%}',
        'row_bsd': f'Best season difference',
        'best_season_difference': f'{results.get("bseason_trophies_impact"):.1%}',
        'cbsd': f'{r3:.1%}',
        'row_ted': f'Tower experience level difference',
        'tower_experience_difference': f'{results.get("exp_trophies_impact"):.1%}',
        'cted': f'{r4:.1%}',
        'row_ced': f'Card experience level difference',
        'card_experience_difference': f'{results.get("level_trophies_impact"):.1%}',
        'cced': f'{r5:.1%}',
        'row_ded': f'Deck advantage / disadvantage',
        'deck_experience_difference': f'{results.get("deck_impact"):.1%}',
        'cded': f'{r6:.1%}',
        'row_fin': f'Estimated total advantage / disadvantage:',
        'cfin': f'{results.get("base_est"):.1%}',
        'row_sup': f'Normalized "deck only" advantage / disadvantage:',
        'csup': f'{r7:.1%}',
        'show_df': show_df,
        'form': form,
    }
    return render(request, 'clashstats/win_deep.html', context)


@login_required()
def viewrepts(request):
    title = 'The6ixClan: Deck Analysis Reports'
    username = None
    if request.user.is_authenticated:
        username = request.user.username
    report_list = Reports.objects.filter(user=request.user).order_by('-created')
    for report in report_list:
        create_time = report.created
        diff = datetime.datetime.now().astimezone() - create_time
        if diff.days == 1:
            status = 'stale'
        elif diff.days > 2:
            status = 'expired'
        elif diff.days < 1:
            status = 'fresh'
        if diff.seconds < (60 * 240):
            pstatus = 'alive'
        task = TaskResult.objects.filter(task_id=report.task_id).first()
        if status == 'expired':
            report.delete()
        elif status == 'stale':
            report.status = 'Expired'
            report.save()
        elif pstatus == 'alive' and task == None:
            report.status = 'Pending'
            report.save()
        elif pstatus == 'alive':
            report.status = 'Completed'
            report.save()
    report_list = Reports.objects.filter(user=request.user).order_by('-created')
    if request.method == 'POST':
        if request.POST.get('Return') == 'Return to Menu':
            return redirect('clashstats-menu')
        elif request.POST.get('Build') == 'Build a Report':
            return redirect('clashstats-clanrept')
    context = {
        'title': title,
        'report_list': report_list,
    }
    return render(request, 'clashstats/viewrepts.html', context)


def highwindeck(request):
    title = 'The6ixClan: Model Identified High Win Ratio Decks'
    context = {
        'title': title
    }


def viewrept(request, pk):
    title = 'The6ixClan: Game Statistic Deep Dive'
    report = get_object_or_404(Reports, id=pk)
    if request.user.is_authenticated:
        username = request.user.username
    show_df = False
    table_data = None
    if request.method == 'POST':
        if request.POST.get('Back') == 'Back':
            return redirect('clashstats-viewrepts')
        elif request.POST.get('Return') == 'Return to Menu':
            return redirect('clashstats-menu')

    task = TaskResult.objects.filter(task_id=report.task_id).first()
    show_df = False
    if task == None:
        messages.warning(request, f'Report processing has not yet started. Report waiting in queue.')
    elif task.status == 'SUCCESS':
        result = analyze_deck.AsyncResult(report.task_id).get()
        show_df = True

    elif task.status == 'FAILURE':
        result = None
    else:
        result = None

    if show_df is True:
        all_ests = result['all_ests']
        home_card_list = result['home_card_list']
        out_df = pd.DataFrame(columns=['probability_win', 'original_deck', 'modifications',
                                       'card_01', 'card_02', 'card_03', 'card_o4',
                                       'card_05', 'card_06', 'card_07', 'card_08'])
        out_df['probability_win'] = pd.Series(["{0:,.1f}%".format(100*val) for val in all_ests[:, (len(home_card_list))]])
        out_df['original_deck'] = ' '
        out_df['original_deck'].iloc[0] = '*'
        orig_deck = None
        for i, row in enumerate(all_ests):
            if i == 0:
                orig_deck = row[range(0, len(home_card_list))]
            out_df['modifications'].iloc[i] = int(0.5 * sum(orig_deck != row[range(0, len(home_card_list))]))
            home_away = np.asarray(np.nonzero(row[range(0, len(home_card_list))])).flatten()
            j = 0
            while j < 8:
                out_df.iloc[i, 3+j] = home_card_list[home_away[j]]
                j += 1

        out_df = out_df.sort_values(by=['original_deck', 'probability_win'], ascending=[False, False])

        table_data = out_df.to_html(index=False, classes='table table-striped table-hover',
                                    header="true",
                                    justify="center")

    context = {
        'title': title,
        'report': report,
        'show_df': show_df,
        'table_data': table_data,
    }
    return render(request, 'clashstats/viewrept.html', context)
