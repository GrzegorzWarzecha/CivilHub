# -*- coding: utf-8 -*-
import json, datetime
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, get_object_or_404, redirect, render_to_response
from django.http import HttpResponse
from django.core.urlresolvers import reverse_lazy, reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.translation import ugettext as _
from django.views.generic import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.contenttypes.models import ContentType
from ideas.models import Idea
from ideas.models import Category as IdeaCategory
from ideas.forms import CategoryForm as IdeaCategoryForm
from blog.models import News
from topics.models import Discussion, Entry
from topics.models import Category as ForumCategory
from polls.models import Poll, Answer
from polls.forms import PollForm
from forms import *
from models import Location
# Use our mixin to allow only some users make actions
from places_core.mixins import LoginRequiredMixin
# Activity stream
from actstream.actions import follow, unfollow
from actstream.models import Action


class LocationNewsList(DetailView):
    """
    Location news page
    """
    model = Location
    template_name = 'locations/location_news.html'


class LocationNewsCreate(LoginRequiredMixin, CreateView):
    """
    Auto-fill some options in this view to create news in currently selected
    location etc.
    """
    model = News
    form_class = NewsLocationForm
    template_name = 'locations/location_news_form.html'

    def get(self, request, *args, **kwargs):
        slug = kwargs['slug']
        ctx = {
                'title': _('Create new entry'),
                'location': Location.objects.get(slug=slug),
                'form': NewsLocationForm(initial={
                    'location': Location.objects.get(slug=slug)
                })
            }
        return render(request, self.template_name, ctx)

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.creator = self.request.user
        obj.save()
        # Without this next line the tags won't be saved.
        form.save_m2m()
        return super(LocationNewsCreate, self).form_valid(form)


class LocationIdeasList(DetailView):
    """
    Location ideas list
    """
    model = Location
    template_name = 'locations/location_ideas.html'

    def get_context_data(self, **kwargs):
        context = super(LocationIdeasList, self).get_context_data(**kwargs)
        context['form'] = IdeaCategoryForm()
        return context


class LocationIdeaCreate(LoginRequiredMixin, CreateView):
    """
    Create new idea in scope of currently selected location.
    """
    model = Idea
    form_class = IdeaLocationForm
    template_name = 'locations/location_idea_form.html'

    def get(self, request, *args, **kwargs):
        slug = kwargs['slug']
        ctx = {
                'location': Location.objects.get(slug=slug),
                'form': IdeaLocationForm(initial={
                    'location': Location.objects.get(slug=slug)
                })
            }
        return render(request, self.template_name, ctx)

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.creator = self.request.user
        obj.save()
        # Without this next line the tags won't be saved.
        form.save_m2m()
        return super(LocationIdeaCreate, self).form_valid(form)

    def form_invalid(self, form):
        ctx = {
                'title': _('Create new idea'),
                'location': form.cleaned_data.get('location'),
                'form': form,
                'errors': form.errors,
            }
        return render_to_response(self.template_name, ctx)


class LocationDiscussionsList(DetailView):
    """
    Get list of all discussion topics related to this location.
    """
    model = Location
    template_name = 'locations/location_forum.html'

    def get_context_data(self, **kwargs):
        location = super(LocationDiscussionsList, self).get_object()
        context = super(LocationDiscussionsList, self).get_context_data(**kwargs)
        discussions = Discussion.objects.filter(location=location)
        paginator = Paginator(discussions, 50)
        page = self.request.GET.get('page')
        try:
            context['discussions'] = paginator.page(page)
        except PageNotAnInteger:
            context['discussions'] = paginator.page(1)
        except EmptyPage:
            context['discussions'] = paginator.page(paginator.num_pages)
        context['title'] = location.name + ':' + _('Discussions')
        context['categories'] = ForumCategory.objects.all()
        return context


def location_discussion_list(request, slug, limit=None, status=None):
    """
    Get subset of discussion list for current location, based on search
    conditions provided by user.
    """
    context = {}
    location = get_object_or_404(Location, slug=slug)
    discussions = Discussion.objects.filter(location=location)
    categories = ForumCategory.objects.all()
    time_delta = False

    if limit == 'day':
        time_delta = datetime.date.today() - datetime.timedelta(days=1)
    if limit == 'week':
        time_delta = datetime.date.today() - datetime.timedelta(days=7)
    if limit == 'month':
        time_delta = datetime.date.today() - relativedelta(months=1)
    if limit == 'year':
        time_delta = datetime.date.today() - relativedelta(years=1)

    if time_delta:
        discussions = discussions.filter(date_created__gte=time_delta)

    paginator = Paginator(discussions, 50)
    page = request.GET.get('page')
    try:
        context['discussions'] = paginator.page(page)
    except PageNotAnInteger:
        context['discussions'] = paginator.page(1)
    except EmptyPage:
        context['discussions'] = paginator.page(paginator.num_pages)
    context['title'] = location.name + ':' + _('Discussions')
    context['location'] = location
    context['categories'] = categories
    return render(request, 'locations/location_forum.html', context)


class LocationDiscussionCreate(LoginRequiredMixin, CreateView):
    """
    Custom form to auto-fill fields related with location.
    """
    model = Discussion
    form_class = DiscussionLocationForm
    template_name = 'locations/location_forum_create.html'
    parent_object = None

    def get(self, request, *args, **kwargs):
        slug = kwargs['slug']
        self.parent_object = Location.objects.get(slug=slug) 
        ctx = {
                'title': _('Create new discussion'),
                'location': self.parent_object,
                'form': DiscussionLocationForm(initial={
                    'location': Location.objects.get(slug=slug)
                })
            }
        return render(request, self.template_name, ctx)

    def get_context_data(self, **kwargs):
        context = super(LocationDiscussionCreate, self).get_context_data(**kwargs)
        context['title'] = _('Create new topic')
        return context

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super(LocationDiscussionCreate, self).form_valid(form)


class LocationFollowersList(DetailView):
    """
    Location followers list
    """
    model = Location
    template_name = 'locations/location_followers.html'


class LocationPollsList(DetailView):
    """
    Show list of polls made in this location.
    """
    model = Location
    template_name = 'locations/location_polls.html'

    def get_context_data(self, **kwargs):
        location = super(LocationPollsList, self).get_object()
        context = super(LocationPollsList, self).get_context_data(**kwargs)
        context['title'] = location.name + ':' + _('Polls')
        context['polls'] = Poll.objects.filter(location=location)
        return context


class LocationPollCreate(LoginRequiredMixin, CreateView):
    """
    Create poll in currently selected location.
    """
    model = Poll
    form_class = PollForm
    template_name = 'polls/create-poll.html'

    def get(self, request, *args, **kwargs):
        slug = kwargs['slug']
        location = Location.objects.get(slug=slug)
        ctx = {
                'title': _('Create new poll'),
                'location': location,
                'form': PollForm(initial={
                    'location': location
                })
            }
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        poll = Poll(
            title = request.POST.get('title'),
            question = request.POST.get('question'),
            location = get_object_or_404(Location,
                       pk=request.POST.get('location')),
            creator = request.user,
            multiple = True if request.POST.get('multiple') else False
        )
        poll.save()
        poll.tags.add(request.POST.get('tags'))
        poll.save()
        for key, val in request.POST.iteritems():
            if 'answer_txt_' in key:
                a = Answer(poll=poll, answer=val)
                a.save()
        return redirect(poll.get_absolute_url())

    def get_success_url(self):
        """
        Returns the supplied URL.
        """
        return reverse('locations:polls', kwargs={'slug':self.object.location.slug})

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super(LocationPollCreate, self).form_valid(form)


class LocationListView(ListView):
    """
    Location list
    """
    model = Location
    context_object_name = 'locations'
    template_name = 'location_list.html'
    def get_context_data(self, **kwargs):
        context = super(LocationListView, self).get_context_data(**kwargs)
        context['title'] = 'Locations'
        return context


class LocationDetailView(DetailView):
    """
    Detailed location view
    """
    model = Location
    def get_context_data(self, **kwargs):
        location = super(LocationDetailView, self).get_object()
        context = super(LocationDetailView, self).get_context_data(**kwargs)
        content_type = ContentType.objects.get_for_model(location)
        actions = Action.objects.filter(target_content_type=content_type)
        actions = actions.filter(target_object_id=location.pk)
        context['title'] = location.name
        context['actions'] = actions
        return context


class CreateLocationView(LoginRequiredMixin, CreateView):
    """
    Add new location
    """
    model = Location
    fields = ['name', 'description', 'latitude', 'longitude', 'image']
    form_class = LocationForm

    def get_context_data(self, **kwargs):
        context = super(CreateLocationView, self).get_context_data(**kwargs)
        context['title'] = _('create new location')
        return context

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super(CreateLocationView, self).form_valid(form)


class UpdateLocationView(LoginRequiredMixin, UpdateView):
    """
    Update existing location
    """
    model = Location
    form_class = LocationForm

    def get_context_data(self, **kwargs):
        location = super(UpdateLocationView, self).get_object()
        context = super(UpdateLocationView, self).get_context_data(**kwargs)
        context['title'] = location.name
        context['subtitle'] = _('Edit this location')
        context['action'] = 'edit'
        return context


class DeleteLocationView(LoginRequiredMixin, DeleteView):
    """
    Delete location
    """
    model = Location
    success_url = reverse_lazy('locations:index')


def add_follower(request, pk):
    """
    Add user to locations followers
    """
    location = get_object_or_404(Location, pk=pk)
    user = request.user
    location.users.add(user)
    try:
        location.save()
        follow(user, location, actor_only = False)
        response = {
            'success': True,
            'message': _('You follow this location'),
        }
    except:
        response = {
            'success': False,
            'message': _('Something, somewhere went terribly wrong'),
        }
    return HttpResponse(json.dumps(response))


def remove_follower(request, pk):
    """
    Remove user from locations followers
    """
    location = get_object_or_404(Location, pk=pk)
    user = request.user
    location.users.remove(user)
    try:
        location.save()
        unfollow(user, location)
        response = {
            'success': True,
            'message': _('You stop following this location'),
        }
    except:
        response = {
            'success': False,
            'message': _('Something, somewhere went terribly wrong'),
        }
    return HttpResponse(json.dumps(response))
