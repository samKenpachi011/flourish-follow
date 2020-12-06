import random
import re

# from django.apps import apps as django_apps
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.urls.base import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormView

from edc_base.view_mixins import EdcBaseViewMixin
from edc_dashboard.view_mixins import (
    ListboardFilterViewMixin, SearchFormViewMixin)
from edc_dashboard.views import ListboardView
from edc_navbar import NavbarViewMixin

from flourish_caregiver.models import CaregiverLocator

from ..forms import ParticipantsNumberForm
from ..model_wrappers import WorkListModelWrapper
from ..models import WorkList
from .filters import ListboardViewFilters
from .worklist_queryset_view_mixin import WorkListQuerysetViewMixin


class ListboardView(NavbarViewMixin, EdcBaseViewMixin,
                    ListboardFilterViewMixin, SearchFormViewMixin,
                    WorkListQuerysetViewMixin,
                    ListboardView, FormView):

    form_class = ParticipantsNumberForm
    listboard_template = 'flourish_follow_listboard_template'
    listboard_url = 'flourish_follow_listboard_url'
    listboard_panel_style = 'info'
    listboard_fa_icon = "fa-user-plus"

    model = 'flourish_follow.worklist'
    listboard_view_filters = ListboardViewFilters()
    model_wrapper_cls = WorkListModelWrapper
    navbar_name = 'flourish_follow'
    navbar_selected_item = 'worklist'
    ordering = '-modified'
    paginate_by = 10
    search_form_url = 'flourish_follow_listboard_url'

    def get_success_url(self):
        return reverse('flourish_follow:flourish_follow_listboard_url')

    def create_user_worklist(self, selected_participants=None):
        """Sets a work list for a user.
        """
        for selected_participant in selected_participants:
            try:
                work_list = WorkList.objects.get(
                    study_maternal_identifier=selected_participant)
            except WorkList.DoesNotExist:
                WorkList.objects.create(
                    study_maternal_identifier=selected_participant,
                    assigned=self.request.user.username,
                    date_assigned=timezone.now().date())
            else:
                work_list.assigned = self.request.user.username
                work_list.date_assigned = timezone.now().date()
                work_list.save()

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        if form.is_valid():
            selected_participants = []
            participants = form.cleaned_data['participants']
            if len(self.available_participants) < participants:
                selected_participants = self.available_participants
            else:
                selected_participants = random.sample(
                    self.available_participants, participants)
            self.create_user_worklist(
                selected_participants=selected_participants)
        return super().form_valid(form)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset_filter_options(self, request, *args, **kwargs):
        options = super().get_queryset_filter_options(request, *args, **kwargs)
        if kwargs.get('subject_identifier'):
            options.update(
                {'subject_identifier': kwargs.get('subject_identifier')})
        return options

    def extra_search_options(self, search_term):
        q = Q()
        if re.match('^[A-Z]+$', search_term):
            q = Q(first_name__exact=search_term)
        return q

    @property
    def available_participants(self):
        locators = CaregiverLocator.objects.all()
        work_list = WorkList.objects.filter(
            Q(is_called=True) | Q(date_assigned=timezone.now().date()))
        locator_identifiers = [
            obj.study_maternal_identifier for obj in locators]
        called_assigned_identifiers = [
            obj.study_maternal_identifier for obj in work_list]
        return list(set(locator_identifiers) - set(called_assigned_identifiers))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            total_results=self.get_queryset().count(),
            called_subject=len(
                [obj for obj in self.get_queryset() if obj.is_called]),
            visited_subjects=len(
                [obj for obj in self.get_queryset() if obj.visited]),
            total_available=len(self.available_participants),
        )
        return context
