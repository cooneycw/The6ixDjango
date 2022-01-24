from django import forms


class cardStatsForm(forms.Form):
    def __init__(self, filterList, sortList, *args, **kwargs):
        super(cardStatsForm, self).__init__(*args, **kwargs)
        self.fields['filts'].choices = filterList
        self.fields['filts'].label = "Select player rankings for inclusion in statistics:"
        self.fields['sorts'].choices = sortList
        self.fields['sorts'].label = "Choose a sort order:"

    filts = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=(), initial=0, required=True)
    sorts = forms.ChoiceField(choices=(), initial=0, required=True)


class segmentForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(segmentForm, self).__init__(*args, **kwargs)


class segmentsForm(forms.Form):
    def __init__(self, segList, filterList, confList, sortList, *args, **kwargs):
        super(segmentsForm, self).__init__(*args, **kwargs)
        self.fields['sgmts'].choices = segList
        self.fields['sgmts'].label = "Select segment for a deep-dive regarding segment composition:"
        self.fields['filts'].choices = filterList
        self.fields['filts'].label = "Select player rankings for inclusion in statistics:"
        self.fields['confs'].choices = confList
        self.fields['confs'].label = "Choose a confidence interval:"
        self.fields['sorts'].choices = sortList
        self.fields['sorts'].label = "Choose a sort order:"

    sgmts = forms.ChoiceField(choices=(), initial=0, required=True)
    filts = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=(), initial=0, required=True)
    confs = forms.ChoiceField(choices=(), initial=0, required=True)
    sorts = forms.ChoiceField(choices=(), initial=0, required=True)


class cardsegtForm(forms.Form):
    def __init__(self, cardList, sortList, rankList, *args, **kwargs):
        super(cardsegtForm, self).__init__(*args, **kwargs)
        self.fields['cards'].choices = cardList
        self.fields['cards'].label = "Choose a card:"
        self.fields['sorts'].choices = sortList
        self.fields['sorts'].label = "Order results by:"
        self.fields['ranks'].choices = rankList
        self.fields['ranks'].label = "Rank within quartile:"

    cards = forms.ChoiceField(choices=(), initial=0, required=True)
    sorts = forms.ChoiceField(choices=(), initial=0, required=True)
    ranks = forms.ChoiceField(choices=(), initial=0, required=True)


class findSegtForm(forms.Form):
    def __init__(self, cardList, *args, **kwargs):
        super(findSegtForm, self).__init__(*args, **kwargs)
        self.fields['cards'].choices = cardList
        self.fields['cards'].label = "Select 8 cards to identify your deck's segment:"

    cards = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=(), initial=None, required=True)


class segmentFoundForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(segmentFoundForm, self).__init__(*args, **kwargs)


class clanReptForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(clanReptForm, self).__init__(*args, **kwargs)


class memberSlctForm(forms.Form):
    def __init__(self, memberList, *args, **kwargs):
        super(memberSlctForm, self).__init__(*args, **kwargs)
        self.fields['members'].choices = memberList
        self.fields['members'].label = "Select players to compile statistical reports:"
    members = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=(), initial=None, required=True)


class memberReptForm(forms.Form):
    def __init__(self,  *args, **kwargs):
        super(memberReptForm, self).__init__(*args, **kwargs)
