from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .forms import CountryForm
from The6ix.settings import STAT_DATE



@login_required()
def clashstats(request):
    return render(request, 'clashstats/menu.html', {'title': 'The6ixClan: Statistics', 'stat_date': STAT_DATE})


@login_required()
def cards(request):
    form = CountryForm()
    # pathname = os.path.abspath(os.path.dirname(__file__))
    # df = pd.read_csv(pathname + '/upload_data/segment_summary_quart.csv', index_col=None)
    #
    # filter_name = []
    # filter_name.append("Personal best trophy range:    0-6124")
    # filter_name.append("Personal best trophy range: 6125-6359")
    # filter_name.append("Personal best trophy range: 6360-6682")
    # filter_name.append("Personal best trophy range: 6683-8703")
    #
    # sort_name = []
    # sort_name.append("Alphabetic Order")
    # sort_name.append("Most Popular")
    # sort_name.append("Least Popular")
    # sort_name.append("Highest Win Rate")
    # sort_name.append("Lowest Win Rate")
    #
    # sort_id = range(len(sort_name))
    # form.sortOrder.choices = list(zip(sort_id, sort_name))
    #
    # pd.set_option('display.max_colwidth', None)
    # quartiles = [1, 2, 3, 4]
    # form.filters.data
    # sort_order = 0
    #
    # if request.method == 'POST':
    #     if 'submit_retrieve' in request.form:
    #         return redirect(url_for('decks.card_view', card_id=form.cardID.data))
    #     if 'submit_filters' in request.form:
    #         if form.filters.data is None:
    #             flash("Please select at least one of the quartiles.", "warning")
    #             quartiles = [1, 2, 3, 4]
    #         else:
    #             quartiles = [x + 1 for x in form.filters.data if x < 4]
    #             if len(quartiles) == 0:
    #                 flash("Please select at least one of the quartiles.", "warning")
    #                 quartiles = [1, 2, 3, 4]
    #         sort_order = form.sortOrder.data
    #
    # i = 1
    # filter_data = []
    # while i < 1 + len(filter_name):
    #     if i < 5:
    #         if i in quartiles:
    #             filter_data.append(i - 1)
    #     i += 1
    #
    # filter_list = list(zip(range(0, len(filter_name)), filter_name))
    # form.filters.choices = filter_list
    # form.filters.data = filter_data
    #
    # max_cards = len(df.columns) - (7 + 1)  # stats + home_elixr
    #
    # card_name = []
    # card_games = []
    # card_win_ratio = []
    # card_use_rate = []
    # quart_filt = df.quartile.isin(quartiles)
    # games = df[quart_filt].count_games
    # wins = df[quart_filt].win_games
    # i = 0
    #
    # while i < max_cards:
    #     curr_card = df.columns[7 + i]
    #     card_name.append(curr_card)
    #     card_games.append(sum(games * df[quart_filt].iloc[:, df.columns.get_loc(curr_card)]))
    #     card_use_rate.append(card_games[i] / sum(games))
    #     card_win_ratio.append(sum(wins * df[quart_filt].iloc[:, df.columns.get_loc(curr_card)]) / card_games[i])
    #     i += 1
    #
    # sum_df = pd.DataFrame(card_name, columns=['card_name'])
    # sum_df['use_rate'] = card_use_rate
    # sum_df['win_ratio'] = card_win_ratio
    #
    # if sort_order == 0:
    #     sum_df.sort_values(['card_name'], ascending=[1], inplace=True)
    # elif sort_order == 1:
    #     sum_df.sort_values(['use_rate'], ascending=[0], inplace=True)
    # elif sort_order == 2:
    #     sum_df.sort_values(['use_rate'], ascending=[1], inplace=True)
    # elif sort_order == 3:
    #     sum_df.sort_values(['win_ratio', 'card_name'], ascending=[0, 0], inplace=True)
    # elif sort_order == 4:
    #     sum_df.sort_values(['win_ratio', 'card_name'], ascending=[1, 0], inplace=True)
    #
    # display_df = sum_df.loc[:, ['card_name']]
    # display_df['use_rate'] = pd.Series(["{0:.1f}%".format(val * 100) for val in sum_df['use_rate']], index=sum_df.index)
    # display_df['win_ratio'] = pd.Series(["{0:.1f}%".format(val * 100) for val in sum_df['win_ratio']],
    #                                     index=sum_df.index)
    #
    # form.cardStats = display_df.to_html(index=False, classes='table table-striped table-hover', header="true",
    #                                     justify="center")

    # return render_template('cards.html', title='Cards', form=form, legend='Select Options for Card Statistics')

    return render(request, 'clashstats/cards.html', {'title': 'The6ixClan: Card Statistics', 'form': form})
