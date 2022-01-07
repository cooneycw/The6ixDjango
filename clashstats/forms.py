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


    #class CardForm(FlaskForm):
    #    cardStats = TextAreaField('Card Statistics')
    #    filters = MultiCheckboxField('Select Options', coerce=int)
    #    quartOrder = SelectField(label='Select Quartile for Sort Order', coerce=int)
    #    sortOrder = SelectField(label='Choose a Sort Order', coerce=int)
    #    submit_filters = SubmitField('Update Card Statistics with Selections')